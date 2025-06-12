#!/usr/bin/env python3

"""
Comprehensive test suite for Personal Finance Dashboard
Tests all major functionality including API endpoints, filtering, and data integrity
"""

import json
import os
import pytest
from datetime import datetime, date
from app import create_app
from models import db, Transaction, Account, Category
from config import config


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
def sample_accounts(app):
    """Create sample accounts for testing."""
    with app.app_context():
        accounts = [
            Account(name='HDFC Bank Savings', bank='HDFC Bank', account_type='Savings Account'),
            Account(name='HDFC Bank Credit Card', bank='HDFC Bank', account_type='Credit Card'),
            Account(name='Federal Bank Savings', bank='Federal Bank', account_type='Savings Account'),
        ]
        
        for account in accounts:
            db.session.add(account)
        db.session.commit()
        return accounts


@pytest.fixture
def sample_transactions(app, sample_accounts):
    """Create sample transactions for testing."""
    with app.app_context():
        transactions = [
            Transaction(
                date=date(2024, 1, 15),
                description='Grocery Shopping',
                amount=150.00,
                category='Food',
                tags='{"categories": ["Food"], "account_type": ["Savings Account"]}',
                account_id=sample_accounts[0].id,
                is_debit=True
            ),
            Transaction(
                date=date(2024, 1, 20),
                description='Salary Credit',
                amount=50000.00,
                category='Paycheck',
                tags='{"categories": ["Paycheck"], "account_type": ["Savings Account"]}',
                account_id=sample_accounts[0].id,
                is_debit=False
            ),
            Transaction(
                date=date(2024, 1, 25),
                description='Restaurant Bill',
                amount=800.00,
                category='Food',
                tags='{"categories": ["Food"], "account_type": ["Credit Card"]}',
                account_id=sample_accounts[1].id,
                is_debit=True
            ),
        ]
        
        for transaction in transactions:
            db.session.add(transaction)
        db.session.commit()
        return transactions


class TestAppCreation:
    """Test application creation and configuration."""
    
    def test_app_creation(self, app):
        """Test that the app is created successfully."""
        assert app is not None
        assert app.config['TESTING'] is True
    
    def test_health_endpoint(self, client):
        """Test the health check endpoint."""
        response = client.get('/health')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['status'] == 'healthy'
        assert 'timestamp' in data


class TestWebPages:
    """Test web page rendering."""
    
    def test_index_page(self, client):
        """Test that the index page loads successfully."""
        response = client.get('/')
        assert response.status_code == 200
        assert b'Personal Finance Dashboard' in response.data
    
    def test_transactions_page(self, client):
        """Test that the transactions page loads successfully."""
        response = client.get('/transactions')
        assert response.status_code == 200
        assert b'Transactions' in response.data
    
    def test_review_upload_page_no_session(self, client):
        """Test review upload page redirects when no session data."""
        response = client.get('/review-upload')
        assert response.status_code == 302  # Redirect


class TestTransactionAPI:
    """Test transaction API endpoints."""
    
    def test_get_transactions_empty(self, client):
        """Test getting transactions when none exist."""
        response = client.get('/api/transactions')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert isinstance(data, list)
        assert len(data) == 0
    
    def test_get_transactions_with_data(self, client, sample_transactions):
        """Test getting transactions when data exists."""
        response = client.get('/api/transactions')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert isinstance(data, list)
        assert len(data) == 3
        assert data[0]['description'] in ['Grocery Shopping', 'Salary Credit', 'Restaurant Bill']
    
    def test_create_transaction_success(self, client, sample_accounts):
        """Test creating a transaction via API."""
        transaction_data = {
            'date': '2024-01-30',
            'description': 'Test Transaction',
            'amount': 100.00,
            'is_debit': True,
            'category': 'Food',
            'account_id': sample_accounts[0].id
        }
        
        response = client.post('/api/transactions',
                              data=json.dumps(transaction_data),
                              content_type='application/json')
        
        assert response.status_code == 201
        
        data = json.loads(response.data)
        assert data['description'] == 'Test Transaction'
        assert data['amount'] == 100.00
        assert data['category'] == 'Food'
    
    def test_create_transaction_missing_fields(self, client):
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
    
    def test_update_transaction(self, client, sample_transactions):
        """Test updating a transaction."""
        transaction_id = sample_transactions[0].id
        update_data = {
            'description': 'Updated Description',
            'amount': 200.00
        }
        
        response = client.put(f'/api/transactions/{transaction_id}',
                             data=json.dumps(update_data),
                             content_type='application/json')
        
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['description'] == 'Updated Description'
        assert data['amount'] == 200.00
    
    def test_delete_transaction(self, client, sample_transactions):
        """Test deleting a transaction."""
        transaction_id = sample_transactions[0].id
        
        response = client.delete(f'/api/transactions/{transaction_id}')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'message' in data


class TestFiltering:
    """Test transaction filtering functionality."""
    
    def test_filter_by_category(self, client, sample_transactions):
        """Test filtering transactions by category."""
        response = client.get('/transactions?category=Food')
        assert response.status_code == 200
        assert b'Food' in response.data
    
    def test_filter_by_bank(self, client, sample_transactions):
        """Test filtering transactions by bank."""
        response = client.get('/transactions?bank=HDFC Bank')
        assert response.status_code == 200
        assert b'HDFC Bank' in response.data
    
    def test_filter_by_account_type(self, client, sample_transactions):
        """Test filtering transactions by account type."""
        response = client.get('/transactions?account=Credit Card')
        assert response.status_code == 200
    
    def test_filter_by_date_range(self, client, sample_transactions):
        """Test filtering transactions by date range."""
        response = client.get('/transactions?date_from=2024-01-01&date_to=2024-01-31')
        assert response.status_code == 200
    
    def test_multiple_filters(self, client, sample_transactions):
        """Test applying multiple filters simultaneously."""
        response = client.get('/transactions?category=Food&bank=HDFC Bank&date_from=2024-01-01')
        assert response.status_code == 200


class TestAccountAPI:
    """Test account API endpoints."""
    
    def test_get_accounts(self, client, sample_accounts):
        """Test getting accounts via API."""
        response = client.get('/api/accounts')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert isinstance(data, list)
        assert len(data) >= 3
        
        # Check that all required fields are present
        for account in data:
            assert 'name' in account
            assert 'bank' in account
            assert 'account_type' in account


class TestDashboardAPI:
    """Test dashboard API endpoints."""
    
    def test_dashboard_summary(self, client, sample_transactions):
        """Test dashboard summary endpoint."""
        response = client.get('/api/dashboard/summary')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        # Should contain summary statistics
        assert isinstance(data, dict)
    
    def test_category_distribution(self, client, sample_transactions):
        """Test category distribution chart data."""
        response = client.get('/api/charts/category_distribution')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert isinstance(data, list)
    
    def test_monthly_trends(self, client, sample_transactions):
        """Test monthly trends chart data."""
        response = client.get('/api/charts/monthly_trends')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert isinstance(data, list)


class TestModels:
    """Test model functionality."""
    
    def test_transaction_model_tags(self, app, sample_accounts):
        """Test transaction model tag functionality."""
        with app.app_context():
            transaction = Transaction(
                date=date.today(),
                description='Test Transaction',
                amount=100.00,
                account_id=sample_accounts[0].id
            )
            
            # Test setting and getting tags
            tags = {"categories": ["Food"], "account_type": ["Savings Account"]}
            transaction.set_tags(tags)
            
            assert transaction.get_tags() == tags
            
            # Test adding individual tags
            transaction.add_tag("categories", "Groceries")
            updated_tags = transaction.get_tags()
            assert "Groceries" in updated_tags["categories"]
    
    def test_transaction_to_dict(self, app, sample_transactions):
        """Test transaction to_dict method."""
        with app.app_context():
            transaction = sample_transactions[0]
            data = transaction.to_dict()
            
            required_fields = ['id', 'date', 'description', 'amount', 'category', 'tags', 'bank']
            for field in required_fields:
                assert field in data
    
    def test_account_model(self, app):
        """Test account model functionality."""
        with app.app_context():
            account = Account(
                name='Test Account',
                bank='Test Bank',
                account_type='savings'
            )
            
            db.session.add(account)
            db.session.commit()
            
            data = account.to_dict()
            assert data['name'] == 'Test Account'
            assert data['bank'] == 'Test Bank'
            assert data['account_type'] == 'savings'


class TestErrorHandling:
    """Test error handling scenarios."""
    
    def test_invalid_transaction_id(self, client):
        """Test accessing non-existent transaction."""
        response = client.get('/api/transactions/99999')
        # This endpoint doesn't exist, but we test the pattern
        assert response.status_code == 404
    
    def test_invalid_json_data(self, client):
        """Test sending invalid JSON data."""
        response = client.post('/api/transactions',
                              data='invalid json',
                              content_type='application/json')
        
        assert response.status_code == 400


class TestUploadFlow:
    """Test file upload and processing flow."""
    
    def test_upload_without_file(self, client):
        """Test upload endpoint without file."""
        response = client.post('/upload')
        assert response.status_code in [400, 302]  # Bad request or redirect
    
    def test_confirm_upload_without_session(self, client):
        """Test confirm upload without session data."""
        response = client.post('/api/upload/confirm',
                              data=json.dumps({}),
                              content_type='application/json')
        
        assert response.status_code == 400


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
