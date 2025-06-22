#!/usr/bin/env python3
"""
Database Schema Migration Script

This script safely updates the database schema to add:
1. New tables: chat_sessions, audit_logs, llm_processing_logs
2. Encryption fields to transactions table
3. Performance indexes

Usage:
    python scripts/database_migration.py [--dry-run] [--backup]
"""

import sqlite3
import os
import sys
import argparse
import shutil
from datetime import datetime


def get_db_path():
    """Get the database file path"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    return os.path.join(project_root, 'instance', 'personal_finance.db')


def create_backup(db_path):
    """Create a backup of the current database"""
    if os.path.exists(db_path):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = f"{db_path}.backup_{timestamp}"
        shutil.copy2(db_path, backup_path)
        print(f"✅ Database backed up to: {backup_path}")
        return backup_path
    else:
        print("⚠️  Database file not found - will be created")
        return None


def check_table_exists(cursor, table_name):
    """Check if a table exists"""
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
    return cursor.fetchone() is not None


def check_column_exists(cursor, table_name, column_name):
    """Check if a column exists in a table"""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [column[1] for column in cursor.fetchall()]
    return column_name in columns


def apply_migration(cursor, dry_run=False):
    """Apply the database migration"""
    updates_applied = []
    
    print("🔄 Starting database migration...")
    
    # 1. Add encryption fields to transactions table
    print("\n📝 Adding encryption fields to transactions table...")
    
    encryption_fields = [
        ('encrypted_description', 'TEXT'),
        ('encrypted_amount', 'TEXT'),
        ('encryption_key_id', 'VARCHAR(50)'),
        ('is_encrypted', 'BOOLEAN DEFAULT 0')
    ]
    
    for field_name, field_type in encryption_fields:
        if not check_column_exists(cursor, 'transactions', field_name):
            sql = f"ALTER TABLE transactions ADD COLUMN {field_name} {field_type}"
            print(f"   + Adding column: {field_name}")
            if not dry_run:
                cursor.execute(sql)
            updates_applied.append(f"Added transactions.{field_name}")
        else:
            print(f"   ✅ Column {field_name} already exists")
    
    # 2. Create chat_sessions table
    print("\n📝 Creating chat_sessions table...")
    if not check_table_exists(cursor, 'chat_sessions'):
        sql = """
            CREATE TABLE chat_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                message TEXT NOT NULL,
                response TEXT NOT NULL,
                timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                session_id VARCHAR(100),
                processing_time_ms INTEGER,
                tokens_used INTEGER,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """
        print("   + Creating chat_sessions table")
        if not dry_run:
            cursor.execute(sql)
        updates_applied.append("Created chat_sessions table")
    else:
        print("   ✅ chat_sessions table already exists")
    
    # 3. Create audit_logs table
    print("\n📝 Creating audit_logs table...")
    if not check_table_exists(cursor, 'audit_logs'):
        sql = """
            CREATE TABLE audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action VARCHAR(100) NOT NULL,
                user_id_hash VARCHAR(64),
                timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                details TEXT,
                ip_address_hash VARCHAR(64),
                user_agent_hash VARCHAR(64),
                resource_type VARCHAR(50),
                resource_id VARCHAR(50),
                success BOOLEAN DEFAULT 1,
                error_message TEXT
            )
        """
        print("   + Creating audit_logs table")
        if not dry_run:
            cursor.execute(sql)
        updates_applied.append("Created audit_logs table")
    else:
        print("   ✅ audit_logs table already exists")
    
    # 4. Create llm_processing_logs table
    print("\n📝 Creating llm_processing_logs table...")
    if not check_table_exists(cursor, 'llm_processing_logs'):
        sql = """
            CREATE TABLE llm_processing_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                processing_type VARCHAR(50) NOT NULL,
                success BOOLEAN NOT NULL,
                duration_ms INTEGER NOT NULL,
                timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                model_name VARCHAR(100),
                prompt_tokens INTEGER,
                completion_tokens INTEGER,
                total_tokens INTEGER,
                error_message TEXT,
                retry_count INTEGER DEFAULT 0,
                endpoint_url VARCHAR(200),
                request_size_bytes INTEGER,
                response_size_bytes INTEGER
            )
        """
        print("   + Creating llm_processing_logs table")
        if not dry_run:
            cursor.execute(sql)
        updates_applied.append("Created llm_processing_logs table")
    else:
        print("   ✅ llm_processing_logs table already exists")
    
    # 5. Create performance indexes
    print("\n📝 Creating performance indexes...")
    
    indexes = [
        ('idx_chat_sessions_timestamp', 'chat_sessions', 'timestamp'),
        ('idx_chat_sessions_session_id', 'chat_sessions', 'session_id'),
        ('idx_audit_logs_action', 'audit_logs', 'action'),
        ('idx_audit_logs_timestamp', 'audit_logs', 'timestamp'),
        ('idx_llm_logs_processing_type', 'llm_processing_logs', 'processing_type'),
        ('idx_llm_logs_timestamp', 'llm_processing_logs', 'timestamp'),
    ]
    
    for index_name, table_name, column_name in indexes:
        if check_table_exists(cursor, table_name):
            sql = f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name}({column_name})"
            print(f"   + Creating index: {index_name}")
            if not dry_run:
                cursor.execute(sql)
            updates_applied.append(f"Created index {index_name}")
    
    return updates_applied


def verify_migration(cursor):
    """Verify that the migration was applied correctly"""
    print("\n🔍 Verifying migration...")
    
    # Check transactions table has new columns
    required_columns = ['encrypted_description', 'encrypted_amount', 'encryption_key_id', 'is_encrypted']
    cursor.execute("PRAGMA table_info(transactions)")
    columns = [column[1] for column in cursor.fetchall()]
    
    for col in required_columns:
        if col in columns:
            print(f"   ✅ transactions.{col} exists")
        else:
            print(f"   ❌ transactions.{col} missing")
            return False
    
    # Check new tables exist
    required_tables = ['chat_sessions', 'audit_logs', 'llm_processing_logs']
    for table in required_tables:
        if check_table_exists(cursor, table):
            print(f"   ✅ {table} table exists")
        else:
            print(f"   ❌ {table} table missing")
            return False
    
    print("✅ Migration verification completed successfully")
    return True


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Migrate database schema for encryption and logging')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes')
    parser.add_argument('--backup', action='store_true', help='Create a backup before applying changes')
    parser.add_argument('--force', action='store_true', help='Apply changes without confirmation')
    
    args = parser.parse_args()
    
    db_path = get_db_path()
    
    print("🗄️  Personal Finance Database Migration")
    print("=" * 50)
    print(f"Database: {db_path}")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE MIGRATION'}")
    
    if not os.path.exists(db_path):
        print(f"❌ Database file not found: {db_path}")
        print("   Please ensure the application has been run at least once.")
        sys.exit(1)
    
    # Create backup if requested
    backup_path = None
    if args.backup and not args.dry_run:
        backup_path = create_backup(db_path)
    
    # Confirm before proceeding
    if not args.dry_run and not args.force:
        response = input("\n⚠️  This will modify your database. Continue? (y/N): ")
        if response.lower() != 'y':
            print("❌ Operation cancelled")
            sys.exit(0)
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Apply migration
        updates_applied = apply_migration(cursor, dry_run=args.dry_run)
        
        if not args.dry_run:
            conn.commit()
            print(f"\n✅ Applied {len(updates_applied)} updates")
            
            # Verify the migration
            if verify_migration(cursor):
                print("🎉 Database migration completed successfully!")
            else:
                print("❌ Migration verification failed")
                sys.exit(1)
        else:
            print(f"\n📋 Would apply {len(updates_applied)} updates:")
            for update in updates_applied:
                print(f"   - {update}")
            print("\nRun without --dry-run to apply these changes.")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        
        # Restore from backup if available
        if backup_path and os.path.exists(backup_path) and not args.dry_run:
            print(f"💾 Restoring from backup: {backup_path}")
            shutil.copy2(backup_path, db_path)
            print("✅ Database restored from backup")
        
        sys.exit(1)
    
    finally:
        conn.close()


if __name__ == "__main__":
    main() 