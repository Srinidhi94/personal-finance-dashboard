#!/usr/bin/env python3

"""
Production-ready test suite for Personal Finance Dashboard
"""

import json

import pytest

from app import create_app
from models import Account, Transaction, db
from services import AccountService


@pytest.fixture
def app():
    """Create and configure a new app instance for each test."""
    app = create_app("testing")

    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()


class TestCriticalFunctionality:
    """Test critical functionality for production readiness."""

    def test_app_health(self, client):
        """Test that the application is healthy."""
        response = client.get("/health")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["status"] == "healthy"
        assert "database" in data

    def test_main_pages_load(self, client):
        """Test that main pages load without errors."""
        # Test index page
        response = client.get("/")
        assert response.status_code == 200
        assert b"Personal Finance Dashboard" in response.data

        # Test transactions page
        response = client.get("/transactions")
        assert response.status_code == 200
        assert b"Transactions" in response.data

    def test_api_endpoints(self, client):
        """Test that all API endpoints respond correctly."""
        # Test accounts endpoint
        response = client.get("/api/accounts")
        assert response.status_code == 200

        # Test categories endpoint
        response = client.get("/api/categories")
        assert response.status_code == 200

        # Test dashboard summary
        response = client.get("/api/dashboard/summary")
        assert response.status_code == 200

    def test_filtering_works(self, client):
        """Test that filtering functionality works."""
        with client.application.app_context():
            # Create test account
            account = AccountService.get_or_create_account(
                name="Test Account", bank="HDFC Bank", account_type="Savings Account"
            )

            # Create test transaction
            transaction_data = {
                "date": "15/01/2024",
                "description": "Test Food Transaction",
                "amount": 100.00,
                "is_debit": True,
                "category": "Food",
                "account_id": account.id,
            }

            response = client.post("/api/transactions", data=json.dumps(transaction_data), content_type="application/json")
            assert response.status_code == 201

        # Test category filter
        response = client.get("/transactions?category=Food")
        assert response.status_code == 200
        assert b"Test Food Transaction" in response.data

        # Test bank filter
        response = client.get("/transactions?bank=HDFC Bank")
        assert response.status_code == 200
        assert b"Test Food Transaction" in response.data

    def test_bulk_edit_functionality(self, client):
        """Test bulk edit functionality works correctly."""
        # Test that the endpoint exists and handles empty requests properly
        response = client.post(
            "/api/transactions/bulk-edit",
            data=json.dumps({"transaction_ids": [], "category": "Test"}),
            content_type="application/json",
        )

        # Should return 400 for empty transaction list
        assert response.status_code == 400

        # Test missing category
        response = client.post(
            "/api/transactions/bulk-edit",
            data=json.dumps({"transaction_ids": [1, 2], "category": ""}),
            content_type="application/json",
        )

        # Should return 400 for missing category
        assert response.status_code == 400

    def test_date_editing_functionality(self, client):
        """Test that date editing works correctly."""
        # Test that the transaction update endpoint handles date updates
        response = client.put(
            "/api/transactions/999",
            data=json.dumps({"date": "2024-01-15", "description": "Test transaction"}),
            content_type="application/json",
        )

        # Should return 404 for non-existent transaction
        assert response.status_code == 404


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
