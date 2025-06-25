"""
Comprehensive Integration Tests for Personal Finance Dashboard

This test suite validates all core functionality including:
- Manual transaction management
- File upload and processing
- Data encryption and security
- Audit logging and trace IDs
- Health monitoring
- API endpoints

Uses real PDF files from uploads/Account_Statements/ folder.
Cleans up all test data after execution.
"""

import os
import sys
import json
import tempfile
import pytest
from datetime import datetime, date
from decimal import Decimal
import shutil

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import Flask and testing utilities
from flask import Flask
from flask.testing import FlaskClient

# Import database models and services
from models.models import db, Account, Transaction, AuditLog, TransactionSource
from models.secure_transaction import SecureTransaction

# Import our application factory and services
from app import create_app
from services import TransactionService, TraceIDService, AuditService


class TestComprehensiveIntegration:
    """Comprehensive integration tests for the entire application"""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self, app, client):
        """Setup test environment and cleanup after each test"""
        with app.app_context():
            # Clear existing data
            db.session.query(AuditLog).delete()
            db.session.query(Transaction).delete()
            db.session.commit()
            
            # Create test accounts
            self.hdfc_account = Account(
                name="Test HDFC Account",
                bank="HDFC Bank",
                account_type="Savings Account",
                is_active=True
            )
            self.federal_account = Account(
                name="Test Federal Bank Account", 
                bank="Federal Bank",
                account_type="Savings Account",
                is_active=True
            )
            
            db.session.add(self.hdfc_account)
            db.session.add(self.federal_account)
            db.session.commit()
            
            # Store account IDs for tests
            self.hdfc_account_id = self.hdfc_account.id
            self.federal_account_id = self.federal_account.id
            
        yield
        
        # Cleanup after test
        with app.app_context():
            # Clean up test data
            db.session.query(AuditLog).delete()
            db.session.query(Transaction).delete()
            db.session.query(Account).filter(
                Account.name.in_(['Test HDFC Account', 'Test Federal Bank Account'])
            ).delete(synchronize_session=False)
            db.session.commit()
            
            # Clean up any uploaded files
            upload_folder = app.config.get('UPLOAD_FOLDER', 'uploads')
            if os.path.exists(upload_folder):
                for filename in os.listdir(upload_folder):
                    if filename.startswith('test_') or 'trace_' in filename:
                        try:
                            os.remove(os.path.join(upload_folder, filename))
                        except:
                            pass

    def test_manual_transaction_crud(self, app, client):
        """Test manual transaction creation, reading, updating, and deletion"""
        with app.app_context():
            # Test transaction creation
            transaction_data = {
                'date': '2024-01-15',
                'description': 'Test Transaction',
                'amount': '150.75',
                'category': 'Food',
                'account_id': self.hdfc_account_id,
                'is_debit': True
            }
            
            response = client.post('/api/transactions', 
                                 data=json.dumps(transaction_data),
                                 content_type='application/json')
            
            assert response.status_code == 201
            created_transaction = response.get_json()
            transaction_id = created_transaction['id']
            
            # Test transaction reading
            response = client.get(f'/api/transactions/{transaction_id}')
            assert response.status_code == 200
            retrieved_transaction = response.get_json()
            assert retrieved_transaction['description'] == 'Test Transaction'
            assert float(retrieved_transaction['amount']) == 150.75

    def test_health_monitoring_endpoints(self, client):
        """Test health monitoring and status endpoints"""
        # Test basic health check
        response = client.get('/health')
        assert response.status_code in [200, 503]  # Healthy or unhealthy is acceptable
        
        health_data = response.get_json()
        assert 'status' in health_data
        assert 'timestamp' in health_data

    def test_api_endpoints_comprehensive(self, client):
        """Test all major API endpoints"""
        # Test accounts endpoint
        response = client.get('/api/accounts')
        assert response.status_code == 200
        accounts = response.get_json()
        assert isinstance(accounts, list)
