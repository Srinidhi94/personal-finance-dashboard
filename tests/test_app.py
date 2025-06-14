#!/usr/bin/env python3

"""
Comprehensive test suite for the Personal Finance Dashboard application.

This module contains tests for all major functionality including:
- Web pages and routes
- API endpoints
- Database models
- Transaction filtering
- Error handling
- Upload workflows

The tests use pytest fixtures to set up test data and ensure proper
database isolation between tests.
"""

import json
import os
from datetime import date, datetime

import pytest

from app import create_app
from config import config
from models import Account, Category, Transaction, db


@pytest.fixture
def app():
    """Create and configure a test Flask application."""
    app = create_app()
    app.config.update(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "WTF_CSRF_ENABLED": False,
        }
    )

    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    """Create a test client for the Flask application."""
    return app.test_client()


@pytest.fixture
def sample_accounts(app):
    """Create sample accounts for testing."""
    with app.app_context():
        accounts = [
            Account(name="HDFC Savings", bank="HDFC Bank", account_type="Savings"),
            Account(name="HDFC Credit Card", bank="HDFC Bank", account_type="Credit Card"),
            Account(name="Federal Bank Savings", bank="Federal Bank", account_type="Savings"),
        ]

        for account in accounts:
            db.session.add(account)
        db.session.commit()

        # Refresh to ensure IDs are loaded
        for account in accounts:
            db.session.refresh(account)

        yield accounts


@pytest.fixture
def sample_transactions(app, sample_accounts):
    """Create sample transactions for testing."""
    with app.app_context():
        # Get account IDs within the context
        account_ids = [acc.id for acc in sample_accounts]

        transactions = [
            Transaction(
                date=date(2024, 1, 15),
                description="Grocery Shopping",
                amount=150.00,
                is_debit=True,
                category="Food",
                account_id=account_ids[0],
                tags='{"categories": ["Food"], "account_types": ["Savings"]}',
            ),
            Transaction(
                date=date(2024, 1, 20),
                description="Salary Credit",
                amount=50000.00,
                is_debit=False,
                category="Income",
                account_id=account_ids[1],
                tags='{"categories": ["Income"], "account_types": ["Credit Card"]}',
            ),
            Transaction(
                date=date(2024, 1, 25),
                description="Restaurant Bill",
                amount=75.00,
                is_debit=True,
                category="Food",
                account_id=account_ids[2],
                tags='{"categories": ["Food"], "account_types": ["Savings"]}',
            ),
        ]

        for transaction in transactions:
            db.session.add(transaction)
        db.session.commit()

        # Refresh to ensure all attributes are loaded
        for transaction in transactions:
            db.session.refresh(transaction)

        yield transactions


class TestAppCreation:
    """Test basic application setup and configuration."""

    def test_app_creation(self, app):
        """Test that the Flask app is created successfully."""
        assert app is not None
        assert app.config["TESTING"] is True

    def test_health_endpoint(self, client):
        """Test the health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["status"] == "healthy"
        assert "timestamp" in data


class TestWebPages:
    """Test web page rendering and basic functionality."""

    def test_index_page(self, client):
        """Test that the index page loads correctly."""
        response = client.get("/")
        assert response.status_code == 200
        assert b"Personal Finance Dashboard" in response.data

    def test_index_page_with_transactions(self, client, sample_transactions):
        """Test index page with transaction data."""
        response = client.get("/")
        assert response.status_code == 200
        assert b"Personal Finance Dashboard" in response.data
        # Should show recent transactions
        assert b"Recent Transactions" in response.data

    def test_transactions_page(self, client):
        """Test that the transactions page loads correctly."""
        response = client.get("/transactions")
        assert response.status_code == 200
        assert b"Transactions" in response.data

    def test_review_upload_page_no_session(self, client):
        """Test review upload page without session data."""
        response = client.get("/review-upload")
        assert response.status_code == 302  # Redirect to transactions page


class TestTransactionAPI:
    """Test transaction API endpoints and functionality."""

    def test_get_transactions_empty(self, client):
        """Test getting transactions when database is empty."""
        response = client.get("/api/transactions")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert isinstance(data, list)
        assert len(data) == 0

    def test_get_transactions_with_data(self, client, sample_transactions):
        """Test getting transactions with sample data."""
        response = client.get("/api/transactions")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert isinstance(data, list)
        assert len(data) == 3
        assert data[0]["description"] in ["Grocery Shopping", "Salary Credit", "Restaurant Bill"]

    def test_create_transaction_success(self, client, sample_accounts):
        """Test creating a transaction via API."""
        with client.application.app_context():
            account_id = sample_accounts[0].id

        transaction_data = {
            "date": "2024-01-30",
            "description": "Test Transaction",
            "amount": 100.00,
            "is_debit": True,
            "category": "Food",
            "account_id": account_id,
        }

        response = client.post("/api/transactions", data=json.dumps(transaction_data), content_type="application/json")

        assert response.status_code == 201

        data = json.loads(response.data)
        assert data["description"] == "Test Transaction"
        assert data["amount"] == 100.00
        assert data["category"] == "Food"

    def test_create_transaction_missing_fields(self, client):
        """Test creating a transaction with missing required fields."""
        incomplete_data = {
            "description": "Test Transaction"
            # Missing amount and date
        }

        response = client.post("/api/transactions", data=json.dumps(incomplete_data), content_type="application/json")

        assert response.status_code == 400

        data = json.loads(response.data)
        assert "error" in data

    def test_update_transaction(self, client, sample_transactions):
        """Test updating a transaction."""
        with client.application.app_context():
            transaction_id = sample_transactions[0].id

        update_data = {"description": "Updated Description", "amount": 200.00}

        response = client.put(
            f"/api/transactions/{transaction_id}", data=json.dumps(update_data), content_type="application/json"
        )

        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["description"] == "Updated Description"
        assert data["amount"] == 200.00

    def test_delete_transaction(self, client, sample_transactions):
        """Test deleting a transaction."""
        with client.application.app_context():
            transaction_id = sample_transactions[0].id

        response = client.delete(f"/api/transactions/{transaction_id}")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert "message" in data

    def test_bulk_edit_transactions(self, client, sample_transactions):
        """Test bulk editing transactions."""
        with client.application.app_context():
            # Get fresh transaction IDs from the database
            transactions = Transaction.query.limit(2).all()
            transaction_ids = [t.id for t in transactions]

            bulk_edit_data = {"transaction_ids": transaction_ids, "category": "Updated Category"}

            response = client.post(
                "/api/transactions/bulk-edit", data=json.dumps(bulk_edit_data), content_type="application/json"
            )

            assert response.status_code == 200

            data = json.loads(response.data)
            assert "updated_count" in data
            assert data["updated_count"] == 2

            # Verify transactions were updated
            updated_transactions = Transaction.query.filter(Transaction.id.in_(transaction_ids)).all()
            for transaction in updated_transactions:
                assert transaction.category == "Updated Category"

    def test_bulk_edit_no_transactions(self, client):
        """Test bulk edit with no transactions selected."""
        bulk_edit_data = {"transaction_ids": [], "category": "Updated Category"}

        response = client.post("/api/transactions/bulk-edit", data=json.dumps(bulk_edit_data), content_type="application/json")

        assert response.status_code == 400

        data = json.loads(response.data)
        assert "error" in data

    def test_bulk_edit_no_category(self, client, sample_transactions):
        """Test bulk edit without category."""
        with client.application.app_context():
            transaction_id = sample_transactions[0].id

        bulk_edit_data = {"transaction_ids": [transaction_id], "category": ""}

        response = client.post("/api/transactions/bulk-edit", data=json.dumps(bulk_edit_data), content_type="application/json")

        assert response.status_code == 400

        data = json.loads(response.data)
        assert "error" in data


class TestFiltering:
    """Test transaction filtering functionality."""

    def test_filter_by_category(self, client, sample_transactions):
        """Test filtering transactions by category."""
        response = client.get("/transactions?category=Food")
        assert response.status_code == 200
        assert b"Food" in response.data

    def test_filter_by_bank(self, client, sample_transactions):
        """Test filtering transactions by bank."""
        response = client.get("/transactions?bank=HDFC Bank")
        assert response.status_code == 200
        assert b"HDFC Bank" in response.data

    def test_filter_by_account_type(self, client, sample_transactions):
        """Test filtering transactions by account type."""
        response = client.get("/transactions?account=Credit Card")
        assert response.status_code == 200

    def test_filter_by_date_range(self, client, sample_transactions):
        """Test filtering transactions by date range."""
        response = client.get("/transactions?date_from=2024-01-01&date_to=2024-01-31")
        assert response.status_code == 200

    def test_multiple_filters(self, client, sample_transactions):
        """Test applying multiple filters simultaneously."""
        response = client.get("/transactions?category=Food&bank=HDFC Bank&date_from=2024-01-01")
        assert response.status_code == 200


class TestAccountAPI:
    """Test account API endpoints."""

    def test_get_accounts(self, client, sample_accounts):
        """Test getting accounts via API."""
        response = client.get("/api/accounts")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert isinstance(data, list)
        assert len(data) >= 3

        # Check that all required fields are present
        for account in data:
            assert "name" in account
            assert "bank" in account
            assert "account_type" in account


class TestDashboardAPI:
    """Test dashboard API endpoints."""

    def test_dashboard_summary(self, client, sample_transactions):
        """Test dashboard summary endpoint."""
        response = client.get("/api/dashboard/summary")
        assert response.status_code == 200

        data = json.loads(response.data)
        # Should contain summary statistics
        assert isinstance(data, dict)

    def test_category_distribution(self, client, sample_transactions):
        """Test category distribution chart data."""
        response = client.get("/api/charts/category_distribution")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert isinstance(data, dict)

    def test_monthly_trends(self, client, sample_transactions):
        """Test monthly trends chart data."""
        response = client.get("/api/charts/monthly_trends")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert isinstance(data, dict)


class TestModels:
    """Test database models and their methods."""

    def test_transaction_model_tags(self, app, sample_accounts):
        """Test transaction model tag functionality."""
        with app.app_context():
            account_id = sample_accounts[0].id

            transaction = Transaction(
                date=date(2024, 1, 15),
                description="Test Transaction",
                amount=100.00,
                is_debit=True,
                category="Food",
                account_id=account_id,
                tags='{"categories": ["Food"], "account_types": ["Savings"]}',
            )

            db.session.add(transaction)
            db.session.commit()

            # Test tag parsing
            tags = transaction.get_tags()
            assert isinstance(tags, dict)
            assert "categories" in tags
            assert "Food" in tags["categories"]

    def test_transaction_to_dict(self, app, sample_transactions):
        """Test transaction to_dict method."""
        with app.app_context():
            transaction = sample_transactions[0]
            data = transaction.to_dict()

            assert isinstance(data, dict)
            assert "id" in data
            assert "description" in data
            assert "amount" in data
            assert "date" in data
            assert "tags" in data

    def test_account_model(self, app):
        """Test account model creation and methods."""
        with app.app_context():
            account = Account(name="Test Account", bank="Test Bank", account_type="Savings")

            db.session.add(account)
            db.session.commit()

            assert account.id is not None
            assert account.name == "Test Account"
            assert account.bank == "Test Bank"
            assert account.account_type == "Savings"


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_invalid_transaction_id(self, client):
        """Test handling of invalid transaction ID."""
        response = client.get("/api/transactions/99999")
        assert response.status_code == 404

    def test_invalid_json_data(self, client):
        """Test handling of invalid JSON data."""
        response = client.post("/api/transactions", data="invalid json", content_type="application/json")
        assert response.status_code == 400


class TestUploadFlow:
    """Test file upload workflow."""

    def test_upload_without_file(self, client):
        """Test upload endpoint without file."""
        response = client.post("/upload")
        assert response.status_code == 400

    def test_confirm_upload_without_session(self, client):
        """Test confirm upload without session data."""
        response = client.post("/confirm-upload")
        assert response.status_code == 302  # Redirect


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
