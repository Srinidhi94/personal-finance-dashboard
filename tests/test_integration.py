#!/usr/bin/env python3

"""
Integration tests for the Personal Finance Dashboard application.

This module contains comprehensive integration tests that verify the complete
workflows and interactions between different components of the application.
"""

import json
from datetime import date, datetime

import pytest

from app import create_app
from models import Account, Transaction, db
from services import AccountService, CategoryService, TransactionService


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


class TestCompleteWorkflows:
    """Test complete user workflows from start to finish."""

    def test_complete_manual_transaction_workflow(self, client):
        """Test the complete workflow of manually adding a transaction."""
        with client.application.app_context():
            # Step 1: Create an account first
            account = AccountService.get_or_create_account(
                name="Test Savings Account", bank="HDFC Bank", account_type="Savings Account"
            )

            # Step 2: Create a transaction
            transaction_data = {
                "date": "2024-01-15",
                "description": "Grocery Shopping",
                "amount": 150.00,
                "is_debit": True,
                "category": "Food",
                "account_id": account.id,
            }

            response = client.post("/api/transactions", data=json.dumps(transaction_data), content_type="application/json")

            assert response.status_code == 201

            created_transaction = json.loads(response.data)
            transaction_id = created_transaction["id"]

            # Step 3: Verify transaction appears in API
            response = client.get("/api/transactions")
            assert response.status_code == 200

            transactions = json.loads(response.data)
            assert len(transactions) == 1
            assert transactions[0]["description"] == "Grocery Shopping"

            # Step 4: Update the transaction
            update_data = {"description": "Updated Grocery Shopping", "amount": 175.00, "category": "Food & Dining"}

            response = client.put(
                f"/api/transactions/{transaction_id}", data=json.dumps(update_data), content_type="application/json"
            )

            assert response.status_code == 200

            updated_transaction = json.loads(response.data)
            assert updated_transaction["description"] == "Updated Grocery Shopping"
            assert updated_transaction["amount"] == 175.00
            assert updated_transaction["category"] == "Food & Dining"

            # Step 5: Verify update in transactions list
            response = client.get("/api/transactions")
            transactions = json.loads(response.data)
            assert transactions[0]["description"] == "Updated Grocery Shopping"

            # Step 6: Delete the transaction
            response = client.delete(f"/api/transactions/{transaction_id}")
            assert response.status_code == 200

            # Step 7: Verify deletion
            response = client.get("/api/transactions")
            transactions = json.loads(response.data)
            assert len(transactions) == 0

    def test_filtering_workflow(self, client):
        """Test the complete filtering workflow."""
        with client.application.app_context():
            # Create multiple accounts
            hdfc_savings = AccountService.get_or_create_account(
                name="HDFC Savings", bank="HDFC Bank", account_type="Savings Account"
            )

            hdfc_credit = AccountService.get_or_create_account(
                name="HDFC Credit Card", bank="HDFC Bank", account_type="Credit Card"
            )

            federal_savings = AccountService.get_or_create_account(
                name="Federal Savings", bank="Federal Bank", account_type="Savings Account"
            )

            # Create diverse transactions
            transactions_data = [
                {
                    "date": "2024-01-15",
                    "description": "Grocery Store",
                    "amount": 150.00,
                    "is_debit": True,
                    "category": "Food",
                    "account_id": hdfc_savings.id,
                },
                {
                    "date": "2024-01-20",
                    "description": "Salary Credit",
                    "amount": 50000.00,
                    "is_debit": False,
                    "category": "Income",
                    "account_id": hdfc_savings.id,
                },
                {
                    "date": "2024-01-25",
                    "description": "Restaurant Bill",
                    "amount": 75.00,
                    "is_debit": True,
                    "category": "Food",
                    "account_id": hdfc_credit.id,
                },
                {
                    "date": "2024-02-01",
                    "description": "Gas Station",
                    "amount": 60.00,
                    "is_debit": True,
                    "category": "Transportation",
                    "account_id": federal_savings.id,
                },
            ]

            # Create all transactions
            for transaction_data in transactions_data:
                response = client.post("/api/transactions", data=json.dumps(transaction_data), content_type="application/json")
                assert response.status_code == 201

            # Test filtering by category
            response = client.get("/transactions?category=Food")
            assert response.status_code == 200
            assert b"Grocery Store" in response.data
            assert b"Restaurant Bill" in response.data
            assert b"Gas Station" not in response.data

            # Test filtering by bank
            response = client.get("/transactions?bank=HDFC Bank")
            assert response.status_code == 200
            assert b"HDFC" in response.data

            # Test filtering by account type
            response = client.get("/transactions?account=Credit Card")
            assert response.status_code == 200
            assert b"Restaurant Bill" in response.data

            # Test filtering by date range
            response = client.get("/transactions?date_from=2024-01-01&date_to=2024-01-31")
            assert response.status_code == 200
            assert b"Grocery Store" in response.data
            assert b"Gas Station" not in response.data  # This is in February

            # Test multiple filters
            response = client.get("/transactions?category=Food&bank=HDFC Bank")
            assert response.status_code == 200
            assert b"Grocery Store" in response.data
            assert b"Restaurant Bill" in response.data

    def test_dashboard_data_workflow(self, client):
        """Test dashboard data aggregation workflow."""
        with client.application.app_context():
            # Create account and transactions for dashboard testing
            account = AccountService.get_or_create_account(
                name="Dashboard Test Account", bank="HDFC Bank", account_type="Savings Account"
            )

            # Create transactions with different categories and amounts
            transactions_data = [
                {
                    "date": "2024-01-15",
                    "description": "Grocery Shopping",
                    "amount": 150.00,
                    "is_debit": True,
                    "category": "Food",
                    "account_id": account.id,
                },
                {
                    "date": "2024-01-20",
                    "description": "Salary",
                    "amount": 50000.00,
                    "is_debit": False,
                    "category": "Income",
                    "account_id": account.id,
                },
                {
                    "date": "2024-02-01",
                    "description": "Rent Payment",
                    "amount": 15000.00,
                    "is_debit": True,
                    "category": "Housing",
                    "account_id": account.id,
                },
                {
                    "date": "2024-02-15",
                    "description": "Bonus",
                    "amount": 50000.00,
                    "is_debit": False,
                    "category": "Income",
                    "account_id": account.id,
                },
            ]

            for transaction_data in transactions_data:
                response = client.post("/api/transactions", data=json.dumps(transaction_data), content_type="application/json")
                assert response.status_code == 201

        # Test dashboard summary
        response = client.get("/api/dashboard/summary")
        assert response.status_code == 200

        summary_data = json.loads(response.data)
        assert isinstance(summary_data, dict)

        # Test category distribution
        response = client.get("/api/charts/category_distribution")
        assert response.status_code == 200

        category_data = json.loads(response.data)
        assert isinstance(category_data, dict)

        # Test monthly trends
        response = client.get("/api/charts/monthly_trends")
        assert response.status_code == 200

        monthly_data = json.loads(response.data)
        assert isinstance(monthly_data, dict)  # Monthly trends returns dict, not list

        # Test account distribution
        response = client.get("/api/charts/account_distribution")
        assert response.status_code == 200

        account_data = json.loads(response.data)
        assert isinstance(account_data, dict)


class TestServiceIntegration:
    """Test service layer integration."""

    def test_transaction_service_integration(self, app):
        """Test TransactionService integration with database."""
        with app.app_context():
            # Create account first
            account = AccountService.get_or_create_account(
                name="Test Account", bank="HDFC Bank", account_type="Savings Account"
            )

            # Test transaction creation
            transaction_data = {
                "date": "2024-01-15",
                "description": "Test Transaction",
                "amount": 100.00,
                "is_debit": True,
                "category": "Food",
                "account_id": account.id,
            }

            transaction = TransactionService.create_transaction(transaction_data)
            assert transaction is not None
            assert transaction.description == "Test Transaction"
            assert transaction.amount == 100.00

            # Test transaction update
            update_data = {"description": "Updated Transaction", "amount": 150.00}

            updated_transaction = TransactionService.update_transaction(transaction.id, update_data)
            assert updated_transaction.description == "Updated Transaction"
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
                name="Test Savings", bank="HDFC Bank", account_type="Savings Account"
            )

            assert account is not None
            assert account.name == "Test Savings"
            assert account.bank == "HDFC Bank"
            assert account.account_type == "Savings Account"

            # Test get_or_create returns existing account
            same_account = AccountService.get_or_create_account(
                name="Test Savings", bank="HDFC Bank", account_type="Savings Account"
            )

            assert same_account.id == account.id

    def test_category_service_integration(self, app):
        """Test CategoryService integration."""
        with app.app_context():
            # Test auto-categorization
            category = CategoryService.categorize_transaction(description="McDonald's Restaurant", amount=25.50, is_debit=True)

            assert category in ["Food", "Miscellaneous"]  # Should categorize as Food or fallback to Miscellaneous

            # Test subcategory
            subcategory = CategoryService.categorize_subcategory(description="McDonald's Restaurant", category="Food")

            assert isinstance(subcategory, str)


class TestErrorScenarios:
    """Test error handling in integration scenarios."""

    def test_invalid_transaction_creation(self, client):
        """Test error handling for invalid transaction creation."""
        # Test with missing required fields
        invalid_data = {
            "description": "Test Transaction"
            # Missing amount and date
        }

        response = client.post("/api/transactions", data=json.dumps(invalid_data), content_type="application/json")

        assert response.status_code == 400

        error_data = json.loads(response.data)
        assert "error" in error_data

    def test_nonexistent_transaction_operations(self, client):
        """Test operations on non-existent transactions."""
        # Test updating non-existent transaction
        update_data = {"description": "Updated"}

        response = client.put("/api/transactions/99999", data=json.dumps(update_data), content_type="application/json")

        assert response.status_code == 404

        # Test deleting non-existent transaction
        response = client.delete("/api/transactions/99999")
        assert response.status_code == 404

    def test_invalid_filter_parameters(self, client):
        """Test filtering with invalid parameters."""
        # Test with invalid date format
        response = client.get("/transactions?date_from=invalid-date")
        # Should handle gracefully and return 200 with no filtering
        assert response.status_code == 200

        # Test with non-existent category
        response = client.get("/transactions?category=NonExistentCategory")
        assert response.status_code == 200


class TestDataConsistency:
    """Test data consistency across operations."""

    def test_transaction_account_consistency(self, client):
        """Test that transactions maintain consistency with accounts."""
        with client.application.app_context():
            # Create account
            account = AccountService.get_or_create_account(
                name="Consistency Test Account", bank="HDFC Bank", account_type="Savings Account"
            )

            # Create transaction
            transaction_data = {
                "date": "2024-01-15",
                "description": "Consistency Test",
                "amount": 100.00,
                "is_debit": True,
                "category": "Food",
                "account_id": account.id,
            }

            response = client.post("/api/transactions", data=json.dumps(transaction_data), content_type="application/json")

            assert response.status_code == 201

            # Verify transaction has correct account information
            transaction_data = json.loads(response.data)
            assert transaction_data["bank"] == "HDFC Bank"
            assert transaction_data["account_type"] == "Savings Account"
            assert transaction_data["account_name"] == "Consistency Test Account"

    def test_tag_structure_consistency(self, client):
        """Test that tag structure remains consistent."""
        with client.application.app_context():
            account = AccountService.get_or_create_account(
                name="Tag Test Account", bank="HDFC Bank", account_type="Savings Account"
            )

            # Create transaction
            transaction_data = {
                "date": "2024-01-15",
                "description": "Tag Test",
                "amount": 100.00,
                "is_debit": True,
                "category": "Food",
                "account_id": account.id,
            }

            response = client.post("/api/transactions", data=json.dumps(transaction_data), content_type="application/json")

            assert response.status_code == 201

            # Get the created transaction
            created_transaction = json.loads(response.data)

            # Verify tag structure - tags should be populated by the system
            assert "tags" in created_transaction
            # The tags might be empty initially, which is acceptable
            if created_transaction["tags"]:
                assert isinstance(created_transaction["tags"], dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
