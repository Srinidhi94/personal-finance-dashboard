#!/bin/bash

echo "Starting Personal Finance Dashboard..."

# Wait for database to be ready
echo "Waiting for database to be ready..."
until pg_isready -h db -p 5432 -U ${POSTGRES_USER}; do
  echo "Database is not ready yet. Waiting..."
  sleep 2
done

echo "Database is ready!"

# Initialize database tables
echo "Initializing database tables..."
python3 -c "
from models import db, Account
from app import create_app
app = create_app()
with app.app_context():
    try:
        # Always drop and recreate all tables for a clean start
        print('Dropping all existing tables...')
        db.drop_all()
        
        print('Creating fresh database tables...')
        db.create_all()
        print('Database tables created successfully')
        
        # Create default accounts
        print('Creating default accounts...')
        
        # HDFC Bank accounts
        hdfc_savings = Account(
            name='HDFC Savings Account',
            bank='HDFC Bank',
            account_type='Savings Account',
            is_active=True
        )
        hdfc_credit = Account(
            name='HDFC Credit Card',
            bank='HDFC Bank', 
            account_type='Credit Card',
            is_active=True
        )
        
        # Federal Bank accounts
        federal_savings = Account(
            name='Federal Bank Savings Account',
            bank='Federal Bank',
            account_type='Savings Account', 
            is_active=True
        )
        
        db.session.add(hdfc_savings)
        db.session.add(hdfc_credit)
        db.session.add(federal_savings)
        db.session.commit()
        
        print('Default accounts created successfully')
        print('Database initialization complete - clean start ensured!')
            
    except Exception as e:
        print(f'Database initialization error: {e}')
        print('Continuing anyway...')
"

# Start the application
echo "Starting Flask application..."
exec gunicorn --bind 0.0.0.0:5000 --workers 2 --timeout 300 --keep-alive 2 --max-requests 1000 --max-requests-jitter 100 app:app 