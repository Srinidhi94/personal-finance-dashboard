"""
Migration: Add encryption support and logging tables

This migration adds:
1. New tables: chat_sessions, audit_logs, llm_processing_logs
2. Encryption fields to transactions table
3. Indexes for performance

Revision ID: 001_encryption_logging
Revises: initial
Create Date: 2024-12-19 12:00:00.000000
"""

import sqlite3
import os
from datetime import datetime


def get_db_path():
    """Get the database file path"""
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), 'instance', 'personal_finance.db')


def backup_database():
    """Create a backup of the current database"""
    db_path = get_db_path()
    if os.path.exists(db_path):
        backup_path = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        import shutil
        shutil.copy2(db_path, backup_path)
        print(f"✅ Database backed up to: {backup_path}")
        return backup_path
    return None


def upgrade():
    """Apply the migration - add new tables and columns"""
    db_path = get_db_path()
    
    # Create backup first
    backup_path = backup_database()
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🔄 Starting database migration...")
        
        # 1. Add encryption fields to transactions table
        print("📝 Adding encryption fields to transactions table...")
        
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(transactions)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'encrypted_description' not in columns:
            cursor.execute("ALTER TABLE transactions ADD COLUMN encrypted_description TEXT")
            print("   ✅ Added encrypted_description column")
        
        if 'encrypted_amount' not in columns:
            cursor.execute("ALTER TABLE transactions ADD COLUMN encrypted_amount TEXT")
            print("   ✅ Added encrypted_amount column")
        
        if 'encryption_key_id' not in columns:
            cursor.execute("ALTER TABLE transactions ADD COLUMN encryption_key_id VARCHAR(50)")
            print("   ✅ Added encryption_key_id column")
        
        if 'is_encrypted' not in columns:
            cursor.execute("ALTER TABLE transactions ADD COLUMN is_encrypted BOOLEAN DEFAULT 0")
            print("   ✅ Added is_encrypted column")
        
        # 2. Create chat_sessions table
        print("📝 Creating chat_sessions table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_sessions (
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
        """)
        print("   ✅ Created chat_sessions table")
        
        # 3. Create audit_logs table
        print("📝 Creating audit_logs table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
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
        """)
        print("   ✅ Created audit_logs table")
        
        # 4. Create llm_processing_logs table
        print("📝 Creating llm_processing_logs table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS llm_processing_logs (
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
        """)
        print("   ✅ Created llm_processing_logs table")
        
        # 5. Create indexes for performance
        print("📝 Creating indexes...")
        
        # Chat sessions indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_chat_sessions_timestamp ON chat_sessions(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_chat_sessions_session_id ON chat_sessions(session_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_chat_sessions_user_id ON chat_sessions(user_id)")
        
        # Audit logs indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id_hash ON audit_logs(user_id_hash)")
        
        # LLM processing logs indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_llm_logs_processing_type ON llm_processing_logs(processing_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_llm_logs_success ON llm_processing_logs(success)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_llm_logs_timestamp ON llm_processing_logs(timestamp)")
        
        print("   ✅ Created performance indexes")
        
        # Commit all changes
        conn.commit()
        print("✅ Migration completed successfully!")
        
        # Verify the migration
        print("🔍 Verifying migration...")
        verify_migration(cursor)
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        if backup_path and os.path.exists(backup_path):
            print(f"💾 Restoring from backup: {backup_path}")
            import shutil
            shutil.copy2(backup_path, db_path)
            print("✅ Database restored from backup")
        raise e
    finally:
        conn.close()


def verify_migration(cursor):
    """Verify that the migration was applied correctly"""
    try:
        # Check transactions table has new columns
        cursor.execute("PRAGMA table_info(transactions)")
        columns = [column[1] for column in cursor.fetchall()]
        
        required_columns = ['encrypted_description', 'encrypted_amount', 'encryption_key_id', 'is_encrypted']
        for col in required_columns:
            if col in columns:
                print(f"   ✅ transactions.{col} exists")
            else:
                raise Exception(f"Column {col} not found in transactions table")
        
        # Check new tables exist
        tables_to_check = ['chat_sessions', 'audit_logs', 'llm_processing_logs']
        for table in tables_to_check:
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
            if cursor.fetchone():
                print(f"   ✅ {table} table exists")
            else:
                raise Exception(f"Table {table} not found")
        
        # Check indexes exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
        indexes = [row[0] for row in cursor.fetchall()]
        
        expected_indexes = [
            'idx_chat_sessions_timestamp',
            'idx_audit_logs_action',
            'idx_llm_logs_processing_type'
        ]
        
        for idx in expected_indexes:
            if idx in indexes:
                print(f"   ✅ Index {idx} exists")
            else:
                print(f"   ⚠️  Index {idx} not found (may be expected)")
        
        print("✅ Migration verification completed")
        
    except Exception as e:
        print(f"❌ Migration verification failed: {e}")
        raise e


def downgrade():
    """Rollback the migration - remove new tables and columns"""
    db_path = get_db_path()
    
    # Create backup first
    backup_path = backup_database()
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🔄 Starting database rollback...")
        
        # SQLite doesn't support DROP COLUMN, so we need to recreate the table
        print("📝 Rolling back transactions table...")
        
        # Get current transactions data (excluding new columns)
        cursor.execute("""
            SELECT id, date, description, amount, category, subcategory, tags, 
                   account_id, is_debit, transaction_type, balance, reference_number, 
                   notes, created_at, updated_at
            FROM transactions
        """)
        transactions_data = cursor.fetchall()
        
        # Drop and recreate transactions table without encryption columns
        cursor.execute("DROP TABLE IF EXISTS transactions_backup")
        cursor.execute("""
            CREATE TABLE transactions_backup (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE NOT NULL,
                description TEXT NOT NULL,
                amount NUMERIC(12, 2) NOT NULL,
                category VARCHAR(50) NOT NULL DEFAULT 'Miscellaneous',
                subcategory VARCHAR(50),
                tags TEXT,
                account_id INTEGER NOT NULL,
                is_debit BOOLEAN NOT NULL DEFAULT 1,
                transaction_type VARCHAR(20) NOT NULL DEFAULT 'manual',
                balance NUMERIC(12, 2),
                reference_number VARCHAR(100),
                notes TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (account_id) REFERENCES accounts (id)
            )
        """)
        
        # Insert data back
        cursor.executemany("""
            INSERT INTO transactions_backup 
            (id, date, description, amount, category, subcategory, tags, account_id, 
             is_debit, transaction_type, balance, reference_number, notes, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, transactions_data)
        
        # Replace original table
        cursor.execute("DROP TABLE transactions")
        cursor.execute("ALTER TABLE transactions_backup RENAME TO transactions")
        
        # Drop new tables
        cursor.execute("DROP TABLE IF EXISTS chat_sessions")
        cursor.execute("DROP TABLE IF EXISTS audit_logs")
        cursor.execute("DROP TABLE IF EXISTS llm_processing_logs")
        
        print("   ✅ Removed new tables and columns")
        
        conn.commit()
        print("✅ Rollback completed successfully!")
        
    except Exception as e:
        print(f"❌ Rollback failed: {e}")
        if backup_path and os.path.exists(backup_path):
            print(f"💾 Restoring from backup: {backup_path}")
            import shutil
            shutil.copy2(backup_path, db_path)
            print("✅ Database restored from backup")
        raise e
    finally:
        conn.close()


def get_migration_info():
    """Get information about this migration"""
    return {
        "revision": "001_encryption_logging",
        "description": "Add encryption support and logging tables",
        "date": "2024-12-19",
        "tables_added": ["chat_sessions", "audit_logs", "llm_processing_logs"],
        "columns_added": {
            "transactions": ["encrypted_description", "encrypted_amount", "encryption_key_id", "is_encrypted"]
        },
        "indexes_added": [
            "idx_chat_sessions_timestamp",
            "idx_chat_sessions_session_id", 
            "idx_chat_sessions_user_id",
            "idx_audit_logs_action",
            "idx_audit_logs_timestamp",
            "idx_audit_logs_user_id_hash",
            "idx_llm_logs_processing_type",
            "idx_llm_logs_success",
            "idx_llm_logs_timestamp"
        ]
    }


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python migration_script.py [upgrade|downgrade|info]")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "upgrade":
        upgrade()
    elif command == "downgrade":
        downgrade()
    elif command == "info":
        info = get_migration_info()
        print("Migration Information:")
        print(f"  Revision: {info['revision']}")
        print(f"  Description: {info['description']}")
        print(f"  Date: {info['date']}")
        print(f"  Tables Added: {', '.join(info['tables_added'])}")
        print(f"  Columns Added: {info['columns_added']}")
        print(f"  Indexes Added: {len(info['indexes_added'])} indexes")
    else:
        print("Invalid command. Use: upgrade, downgrade, or info")
        sys.exit(1) 