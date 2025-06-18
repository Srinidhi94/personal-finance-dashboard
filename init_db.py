#!/usr/bin/env python3
"""
Database initialization script for Personal Finance Dashboard
"""

import os
import sys
from sqlalchemy import create_engine, text
from models import db, Transaction, Account, Category, User, ChatSession, AuditLog, LLMProcessingLog

def init_database():
    """Initialize the database with all required tables"""
    try:
        # Get database URL from environment
        database_url = os.environ.get('DATABASE_URL', 'sqlite:///personal_finance.db')
        
        print(f"Connecting to database: {database_url}")
        
        # Create engine
        engine = create_engine(database_url)
        
        # Test connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            print("Database connection successful")
        
        # Create all tables
        db.metadata.create_all(engine)
        print("Database tables created successfully")
        
        print("Database initialization complete")
        return True
        
    except Exception as e:
        print(f"Database initialization failed: {e}")
        return False

if __name__ == "__main__":
    success = init_database()
    sys.exit(0 if success else 1) 