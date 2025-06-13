#!/usr/bin/env python3

"""
Integration tests for Personal Finance Dashboard
Tests complete workflows and end-to-end functionality
"""

import json
import pytest
from datetime import datetime, date
from app import create_app
from models import db, Transaction, Account, Category
from services import TransactionService, AccountService, CategoryService


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


class TestCompleteWorkflows:
    """Test complete user workflows from start to finish."""
    
    def test_complete_manual_transaction_workflow(self, client):
        """Test the complete workflow of manually adding a transaction."""
        # Step 1: Create account via service
        with client.application.app_context():
            account = AccountService.get_or_create_account(
                name='Test Savings',
                bank='HDFC Bank',
                account_type='Savings Account'
            )
            account_id = account.id
        
        # Step 2: Create transaction via API
        transaction_data = {
            'date': '2024-01-15',
            'description': 'Grocery Shopping',
            'amount': 150.00,
            'is_debit': True,
            'category': 'Food',
            'account_id': account_id,
            'tags': {
                'categories': ['Food'],
                'account_type': ['Savings Account']
            }
        }
        
        response = client.post('/api/transactions',
                              data=json.dumps(transaction_data),
                              content_type='application/json')
        
        assert response.status_code == 201
        created_transaction = json.loads(response.data)
        transaction_id = created_transaction['id']
        
        # Step 3: Verify transaction appears in list
        response = client.get('/api/transactions')
        assert response.status_code == 200
        
        transactions = json.loads(response.data)
        assert len(transactions) == 1
        assert transactions[0]['description'] == 'Grocery Shopping'
        
        # Step 4: Update transaction
        update_data = {
            'description': 'Grocery Shopping - Updated',
            'amount': 175.00
        }
        
        response = client.put(f'/api/transactions/{transaction_id}',
                             data=json.dumps(update_data),
                             content_type='application/json')
        
        assert response.status_code == 200
        updated_transaction = json.loads(response.data)
        assert updated_transaction['description'] == 'Grocery Shopping - Updated'
        assert updated_transaction['amount'] == 175.00
        
        # Step 5: Verify update in transactions page
        response = client.get('/transactions')
        assert response.status_code == 200
        assert b'Grocery Shopping - Updated' in response.data
        
        # Step 6: Delete transaction
        response = client.delete(f'/api/transactions/{transaction_id}')
        assert response.status_code == 200
        
        # Step 7: Verify deletion
        response = client.get('/api/transactions')
        transactions = json.loads(response.data)
        assert len(transactions) == 0
    
    def test_filtering_workflow(self, client):
        """Test the complete filtering workflow."""
        # Setup: Create accounts and transactions
        with client.application.app_context():
            # Create accounts
            hdfc_savings = AccountService.get_or_create_account(
                name='HDFC Bank Savings',
                bank='HDFC Bank',
                account_type='Savings Account'
            )
            
            federal_credit = AccountService.get_or_create_account(
                name='Federal Bank Credit Card',
                bank='Federal Bank',
                account_type='Credit Card'
            )
            
            # Create diverse transactions
            transactions_data = [
                {
                    'date': '2024-01-15',
                    'description': 'Grocery Shopping',
                    'amount': 150.00,
                    'is_debit': True,
                    'category': 'Food',
                    'account_id': hdfc_savings.id,
                    'tags': {'categories': ['Food'], 'account_type': ['Savings Account']}
                },
                {
                    'date': '2024-01-20',
                    'description': 'Restaurant Bill',
                    'amount': 800.00,
                    'is_debit': True,
                    'category': 'Food',
                    'account_id': federal_credit.id,
                    'tags': {'categories': ['Food'], 'account_type': ['Credit Card']}
                },
                {
                    'date': '2024-01-25',
                    'description': 'Salary Credit',
                    'amount': 50000.00,
                    'is_debit': False,
                    'category': 'Paycheck',
                    'account_id': hdfc_savings.id,
                    'tags': {'categories': ['Paycheck'], 'account_type': ['Savings Account']}
                },
                {
                    'date': '2024-02-05',
                    'description': 'Gas Station',
                    'amount': 2000.00,
                    'is_debit': True,
                    'category': 'Transportation',
                    'account_id': hdfc_savings.id,
                    'tags': {'categories': ['Transportation'], 'account_type': ['Savings Account']}
                }
            ]
            
            for tx_data in transactions_data:
                response = client.post('/api/transactions',
                                      data=json.dumps(tx_data),
                                      content_type='application/json')
                assert response.status_code == 201
        
        # Test 1: Filter by category
        response = client.get('/transactions?category=Food')
        assert response.status_code == 200
        assert b'Grocery Shopping' in response.data
        assert b'Restaurant Bill' in response.data
        assert b'Salary Credit' not in response.data
        
        # Test 2: Filter by bank
        response = client.get('/transactions?bank=HDFC Bank')
        assert response.status_code == 200
        assert b'Grocery Shopping' in response.data
        assert b'Salary Credit' in response.data
        assert b'Restaurant Bill' not in response.data
        
        # Test 3: Filter by account type
        response = client.get('/transactions?account=Credit Card')
        assert response.status_code == 200
        assert b'Restaurant Bill' in response.data
        assert b'Grocery Shopping' not in response.data
        
        # Test 4: Filter by date range
        response = client.get('/transactions?date_from=2024-01-01&date_to=2024-01-31')
        assert response.status_code == 200
        assert b'Grocery Shopping' in response.data
        assert b'Restaurant Bill' in response.data
        assert b'Salary Credit' in response.data
        assert b'Gas Station' not in response.data
        
        # Test 5: Multiple filters
        response = client.get('/transactions?category=Food&bank=HDFC Bank&date_from=2024-01-01&date_to=2024-01-31')
        assert response.status_code == 200
        assert b'Grocery Shopping' in response.data
        assert b'Restaurant Bill' not in response.data
        assert b'Salary Credit' not in response.data
    
    def test_dashboard_data_workflow(self, client):
        """Test the complete dashboard data workflow."""
        # Setup: Create transactions with different categories and amounts
        with client.application.app_context():
            account = AccountService.get_or_create_account(
                name='Test Account',
                bank='HDFC Bank',
                account_type='Savings Account'
            )
            
            # Create transactions for different months and categories
            transactions_data = [
                # January transactions
                {'date': '2024-01-15', 'description': 'Groceries', 'amount': 500.00, 'is_debit': True, 'category': 'Food', 'account_id': account.id},
                {'date': '2024-01-20', 'description': 'Salary', 'amount': 50000.00, 'is_debit': False, 'category': 'Paycheck', 'account_id': account.id},
                {'date': '2024-01-25', 'description': 'Rent', 'amount': 15000.00, 'is_debit': True, 'category': 'Rent', 'account_id': account.id},
                
                # February transactions
                {'date': '2024-02-10', 'description': 'Groceries', 'amount': 600.00, 'is_debit': True, 'category': 'Food', 'account_id': account.id},
                {'date': '2024-02-20', 'description': 'Salary', 'amount': 50000.00, 'is_debit': False, 'category': 'Paycheck', 'account_id': account.id},
                {'date': '2024-02-28', 'description': 'Utilities', 'amount': 3000.00, 'is_debit': True, 'category': 'Home', 'account_id': account.id},
            ]
            
            for tx_data in transactions_data:
                response = client.post('/api/transactions',
                                      data=json.dumps(tx_data),
                                      content_type='application/json')
                assert response.status_code == 201
        
        # Test dashboard summary
        response = client.get('/api/dashboard/summary')
        assert response.status_code == 200
        
        summary = json.loads(response.data)
        assert isinstance(summary, dict)
        # Should contain summary statistics
        
        # Test category distribution
        response = client.get('/api/charts/category_distribution')
        assert response.status_code == 200
        
        category_data = json.loads(response.data)
        assert isinstance(category_data, dict)
        
        # Test monthly trends
        response = client.get('/api/charts/monthly_trends')
        assert response.status_code == 200
        
        monthly_data = json.loads(response.data)
        assert isinstance(monthly_data, list)
        
        # Test account distribution
        response = client.get('/api/charts/account_distribution')
        assert response.status_code == 200
        
        account_data = json.loads(response.data)
        assert isinstance(account_data, list)


class TestServiceIntegration:
    """Test service layer integration."""
    
    def test_transaction_service_integration(self, app):
        """Test TransactionService integration with database."""
        with app.app_context():
            # Create account first
            account = AccountService.get_or_create_account(
                name='Test Account',
                bank='HDFC Bank',
                account_type='Savings Account'
            )
            
            # Test transaction creation
            transaction_data = {
                'date': '2024-01-15',
                'description': 'Test Transaction',
                'amount': 100.00,
                'is_debit': True,
                'category': 'Food',
                'account_id': account.id
            }
            
            transaction = TransactionService.create_transaction(transaction_data)
            assert transaction is not None
            assert transaction.description == 'Test Transaction'
            assert transaction.amount == 100.00
            
            # Test transaction update
            update_data = {
                'description': 'Updated Transaction',
                'amount': 150.00
            }
            
            updated_transaction = TransactionService.update_transaction(transaction.id, update_data)
            assert updated_transaction.description == 'Updated Transaction'
            assert updated_transaction.amount == 150.00
            
            # Test transaction deletion
            success = TransactionService.delete_transaction(transaction.id)
            assert success is True
            
            # Verify deletion
            deleted_transaction = Transaction.query.get(transaction.id)
            assert deleted_transaction is None
    
    def test_account_service_integration(self, app):
        """Test AccountService integration."""
        with app.app_context():
            # Test account creation
            account = AccountService.get_or_create_account(
                name='Test Savings',
                bank='HDFC Bank',
                account_type='Savings Account'
            )
            
            assert account is not None
            assert account.name == 'Test Savings'
            assert account.bank == 'HDFC Bank'
            assert account.account_type == 'Savings Account'
            
            # Test get_or_create returns existing account
            same_account = AccountService.get_or_create_account(
                name='Test Savings',
                bank='HDFC Bank',
                account_type='Savings Account'
            )
            
            assert same_account.id == account.id
    
    def test_category_service_integration(self, app):
        """Test CategoryService integration."""
        with app.app_context():
            # Test auto-categorization
            category = CategoryService.categorize_transaction(
                description='McDonald\'s Restaurant',
                amount=25.50,
                is_debit=True
            )
            
            assert category in ['Food', 'Miscellaneous']  # Should categorize as Food or fallback to Miscellaneous
            
            # Test subcategory
            subcategory = CategoryService.categorize_subcategory(
                description='McDonald\'s Restaurant',
                category='Food'
            )
            
            assert isinstance(subcategory, str)


class TestErrorScenarios:
    """Test error handling in integration scenarios."""
    
    def test_invalid_transaction_creation(self, client):
        """Test error handling for invalid transaction creation."""
        # Test with missing required fields
        invalid_data = {
            'description': 'Test Transaction'
            # Missing amount and date
        }
        
        response = client.post('/api/transactions',
                              data=json.dumps(invalid_data),
                              content_type='application/json')
        
        assert response.status_code == 400
        
        error_data = json.loads(response.data)
        assert 'error' in error_data
    
    def test_nonexistent_transaction_operations(self, client):
        """Test operations on non-existent transactions."""
        # Test updating non-existent transaction
        update_data = {'description': 'Updated'}
        
        response = client.put('/api/transactions/99999',
                             data=json.dumps(update_data),
                             content_type='application/json')
        
        assert response.status_code == 404
        
        # Test deleting non-existent transaction
        response = client.delete('/api/transactions/99999')
        assert response.status_code == 404
    
    def test_invalid_filter_parameters(self, client):
        """Test filtering with invalid parameters."""
        # Test with invalid date format
        response = client.get('/transactions?date_from=invalid-date')
        # Should handle gracefully and return 200 with no filtering
        assert response.status_code == 200
        
        # Test with non-existent category
        response = client.get('/transactions?category=NonExistentCategory')
        assert response.status_code == 200


class TestDataConsistency:
    """Test data consistency across operations."""
    
    def test_transaction_account_consistency(self, client):
        """Test that transactions maintain consistency with accounts."""
        with client.application.app_context():
            # Create account
            account = AccountService.get_or_create_account(
                name='Consistency Test Account',
                bank='HDFC Bank',
                account_type='Savings Account'
            )
            
            # Create transaction
            transaction_data = {
                'date': '2024-01-15',
                'description': 'Consistency Test',
                'amount': 100.00,
                'is_debit': True,
                'category': 'Food',
                'account_id': account.id
            }
            
            response = client.post('/api/transactions',
                                  data=json.dumps(transaction_data),
                                  content_type='application/json')
            
            assert response.status_code == 201
            
            # Verify transaction has correct account information
            transaction_data = json.loads(response.data)
            assert transaction_data['bank'] == 'HDFC Bank'
            assert transaction_data['account_type'] == 'Savings Account'
            assert transaction_data['account_name'] == 'Consistency Test Account'
    
    def test_tag_structure_consistency(self, client):
        """Test that tag structure remains consistent."""
        with client.application.app_context():
            account = AccountService.get_or_create_account(
                name='Tag Test Account',
                bank='HDFC Bank',
                account_type='Savings Account'
            )
            
            # Create transaction with tags
            transaction_data = {
                'date': '2024-01-15',
                'description': 'Tag Test',
                'amount': 100.00,
                'is_debit': True,
                'category': 'Food',
                'account_id': account.id,
                'tags': {
                    'categories': ['Food', 'Groceries'],
                    'account_type': ['Savings Account']
                }
            }
            
            response = client.post('/api/transactions',
                                  data=json.dumps(transaction_data),
                                  content_type='application/json')
            
            assert response.status_code == 201
            
            # Verify tag structure
            created_transaction = json.loads(response.data)
            assert 'tags' in created_transaction
            assert isinstance(created_transaction['tags'], dict)
            assert 'categories' in created_transaction['tags']
            assert 'Food' in created_transaction['tags']['categories']


if __name__ == '__main__':
    pytest.main([__file__, '-v']) 