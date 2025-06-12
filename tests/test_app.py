#!/usr/bin/env python3

"""
Test script that extracts transactions from a sample statement,
categorizes them, and displays the results in a nice format.
"""

import json
import os
from parsers import extract_transactions_from_file
from services import CategoryService
import pytest
from datetime import datetime
from app import create_app
from models import db, Transaction, Account, Category
from config import config

def main():
    # Define colors for output
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'
    
    # Clear the screen
    print("\033c", end="")
    
    # Print header
    print(f"{BOLD}{BLUE}===== HDFC Statement Parser Tester ====={END}\n")
    
    # Sample statement path
    # Define the statement path
    sample_path = 'uploads/Statement_Example.pdf'
    print(f"{BOLD}Testing with:{END} {sample_path}\n")
    
    # Extract transactions
    print(f"{BOLD}{BLUE}Step 1: Extracting transactions...{END}")
    transactions = extract_transactions_from_file(sample_path, "HDFC", "savings", "HDFC Savings Account")
    
    print(f"\n{GREEN}Successfully extracted {len(transactions)} transactions.{END}\n")
    
    # Categorize transactions
    print(f"{BOLD}{BLUE}Step 2: Categorizing transactions...{END}\n")
    
    for i, tx in enumerate(transactions):
        # Add categorization
        tx['category'] = CategoryService.categorize_transaction(
            description=tx.get('description', ''), 
            amount=tx.get('amount'), 
            is_debit=tx.get('is_debit')
        )
        
        tx['subcategory'] = CategoryService.categorize_subcategory(tx.get('description', ''), tx['category'])
        
        # Format date and amount for display
        date = tx.get('date', 'Unknown date')
        
        amount = tx.get('amount', 0)
        amount_str = f"{amount:.2f}" if amount else "0.00"
        amount_color = GREEN if amount > 0 or tx['category'] == 'Income' else RED
        amount_sign = "" if amount > 0 or tx['category'] == 'Income' else "-"
        
        # Display transaction
        print(f"{BOLD}Transaction #{i+1}:{END}")
        print(f"  Date: {date}")
        print(f"  Description: {tx.get('description', 'No description')[:80]}")
        print(f"  Amount: {amount_color}{amount_sign}₹{abs(float(amount_str)):.2f}{END}")
        print(f"  Category: {YELLOW}{tx['category']}{END}")
        if tx['subcategory']:
            print(f"  Subcategory: {tx['subcategory']}")
        print(f"  Is Debit: {RED if tx.get('is_debit') else GREEN}{tx.get('is_debit')}{END}")
        print("")
    
    # Save results to file
    output_file = 'test_output.json'
    with open(output_file, 'w') as f:
        json.dump(transactions, f, indent=2)
    
    print(f"{BOLD}{GREEN}Results saved to {output_file}{END}")
    print(f"\n{BOLD}{BLUE}===== Test Complete ====={END}")

@pytest.fixture
def app():
    """Create and configure a new app instance for each test."""
    app = create_app('testing')
    
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()


@pytest.fixture
def sample_account(app):
    """Create a sample account for testing."""
    with app.app_context():
        account = Account(
            name='Test Account',
            bank='Test Bank',
            account_type='savings'
        )
        db.session.add(account)
        db.session.commit()
        return account


def test_app_creation(app):
    """Test that the app is created successfully."""
    assert app is not None
    assert app.config['TESTING'] is True


def test_health_endpoint(client):
    """Test the health check endpoint."""
    response = client.get('/health')
    assert response.status_code == 200
    
    data = json.loads(response.data)
    assert data['status'] == 'healthy'
    assert 'timestamp' in data


def test_index_page(client):
    """Test that the index page loads successfully."""
    response = client.get('/')
    assert response.status_code == 200
    assert b'Personal Finance Dashboard' in response.data


def test_transactions_page(client):
    """Test that the transactions page loads successfully."""
    response = client.get('/transactions')
    assert response.status_code == 200


def test_api_get_transactions_empty(client):
    """Test getting transactions when none exist."""
    response = client.get('/api/transactions')
    assert response.status_code == 200
    
    data = json.loads(response.data)
    assert isinstance(data, list)
    assert len(data) == 0


def test_api_create_transaction(client, sample_account):
    """Test creating a transaction via API."""
    transaction_data = {
        'date': '25/12/2024',
        'description': 'Test Transaction',
        'amount': 100.00,
        'is_debit': True,
        'category': 'Food',
        'account_id': sample_account.id
    }
    
    response = client.post('/api/transactions',
                          data=json.dumps(transaction_data),
                          content_type='application/json')
    
    assert response.status_code == 201
    
    data = json.loads(response.data)
    assert data['description'] == 'Test Transaction'
    assert data['amount'] == 100.00
    assert data['category'] == 'Food'


def test_api_create_transaction_missing_fields(client):
    """Test creating a transaction with missing required fields."""
    incomplete_data = {
        'description': 'Test Transaction'
        # Missing amount and date
    }
    
    response = client.post('/api/transactions',
                          data=json.dumps(incomplete_data),
                          content_type='application/json')
    
    assert response.status_code == 400
    
    data = json.loads(response.data)
    assert 'error' in data


def test_api_get_accounts(client, sample_account):
    """Test getting accounts via API."""
    response = client.get('/api/accounts')
    assert response.status_code == 200
    
    data = json.loads(response.data)
    assert isinstance(data, list)
    assert len(data) >= 1
    
    # Check if our sample account is in the response
    account_names = [acc['name'] for acc in data]
    assert 'Test Account' in account_names


def test_api_dashboard_summary(client, sample_account):
    """Test getting dashboard summary."""
    # First create a transaction
    with client.application.app_context():
        transaction = Transaction(
            date=datetime.now().date(),
            description='Test Income',
            amount=500.00,
            category='Income',
            account_id=sample_account.id,
            is_debit=False
        )
        db.session.add(transaction)
        db.session.commit()
    
    response = client.get('/api/dashboard/summary')
    assert response.status_code == 200
    
    data = json.loads(response.data)
    assert 'total_transactions' in data
    assert 'total_income' in data
    assert 'total_expenses' in data
    assert data['total_transactions'] >= 1


def test_api_category_distribution(client, sample_account):
    """Test getting category distribution chart data."""
    # Create some test transactions
    with client.application.app_context():
        transactions = [
            Transaction(
                date=datetime.now().date(),
                description='Food Purchase',
                amount=50.00,
                category='Food',
                account_id=sample_account.id,
                is_debit=True
            ),
            Transaction(
                date=datetime.now().date(),
                description='Gas',
                amount=30.00,
                category='Transportation',
                account_id=sample_account.id,
                is_debit=True
            )
        ]
        
        for transaction in transactions:
            db.session.add(transaction)
        db.session.commit()
    
    response = client.get('/api/charts/category-distribution')
    assert response.status_code == 200
    
    data = json.loads(response.data)
    assert isinstance(data, list)
    
    # Check that categories are present
    categories = [item['category'] for item in data]
    assert 'Food' in categories
    assert 'Transportation' in categories


def test_transaction_model_to_dict(app, sample_account):
    """Test the Transaction model to_dict method."""
    with app.app_context():
        transaction = Transaction(
            date=datetime(2024, 12, 25).date(),
            description='Test Transaction',
            amount=100.50,
            category='Food',
            account_id=sample_account.id,
            is_debit=True
        )
        db.session.add(transaction)
        db.session.commit()
        
        transaction_dict = transaction.to_dict()
        
        assert transaction_dict['description'] == 'Test Transaction'
        assert transaction_dict['amount'] == 100.50
        assert transaction_dict['category'] == 'Food'
        assert transaction_dict['is_debit'] is True
        assert transaction_dict['type'] == 'debit'
        assert transaction_dict['date'] == '25/12/2024'


def test_account_model_to_dict(app):
    """Test the Account model to_dict method."""
    with app.app_context():
        account = Account(
            name='Test Savings',
            bank='Test Bank',
            account_type='savings',
            account_number='123456789'
        )
        db.session.add(account)
        db.session.commit()
        
        account_dict = account.to_dict()
        
        assert account_dict['name'] == 'Test Savings'
        assert account_dict['bank'] == 'Test Bank'
        assert account_dict['account_type'] == 'savings'
        assert account_dict['account_number'] == '123456789'
        assert account_dict['is_active'] is True

if __name__ == "__main__":
    main()
