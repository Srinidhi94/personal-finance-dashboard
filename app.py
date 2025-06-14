import os
from datetime import datetime, timedelta

from flask import Flask, flash, jsonify, redirect, render_template, request, send_from_directory, session, url_for
from flask_migrate import Migrate
from sqlalchemy import desc, func, or_
from werkzeug.utils import secure_filename

from config import config
from models import Account, Category, Transaction, User, db
from services import AccountService, CategoryService, DataMigrationService, TransactionService


# Initialize Flask app
def create_app(config_name=None):
    app = Flask(__name__)

    # Load configuration
    config_name = config_name or os.environ.get("FLASK_ENV", "development")
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    # Initialize extensions
    db.init_app(app)
    migrate = Migrate(app, db)

    # Register routes
    register_routes(app)

    # Create database tables and migrate data
    with app.app_context():
        db.create_all()

        # Check if we need to migrate from JSON files
        # Commented out to prevent auto-loading of sample data
        # if Transaction.query.count() == 0:
        #     DataMigrationService.migrate_from_json()

    return app


def register_routes(app):

    @app.route("/")
    def index():
        """Main dashboard page with analytics"""
        try:
            # Get summary data
            summary = TransactionService.get_transactions_summary()

            # Get recent transactions
            recent_transactions = Transaction.query.order_by(desc(Transaction.date)).limit(10).all()

            # Get accounts
            accounts = Account.query.filter_by(is_active=True).all()

            # Define categories and options for modals
            expense_categories = [
                "Food",
                "Gifts",
                "Health/medical",
                "Home",
                "Transportation",
                "Personal",
                "Pets",
                "Family",
                "Travel",
                "Debt",
                "Other",
                "Rent",
                "Credit Card",
                "Alcohol",
                "Consumables",
                "Investments",
            ]

            income_categories = ["Savings", "Paycheck", "Bonus", "Interest", "Splitwise", "RSU"]

            account_types = ["Savings Account", "Credit Card"]
            banks = ["HDFC Bank", "Federal Bank"]

            return render_template(
                "index.html",
                summary=summary,
                recent_transactions=recent_transactions,
                accounts=[a.to_dict() for a in accounts],
                expense_categories=expense_categories,
                income_categories=income_categories,
                account_types=account_types,
                banks=banks,
            )
        except Exception as e:
            print(f"Error loading dashboard: {e}")
            return render_template(
                "index.html",
                summary={"total_transactions": 0, "total_income": 0, "total_expenses": 0, "net_balance": 0},
                recent_transactions=[],
                accounts=[],
                expense_categories=[],
                income_categories=[],
                account_types=[],
                banks=[],
            )

    @app.route("/transactions")
    def transactions():
        """Transactions page with filtering and pagination"""
        try:
            # Define categories
            expense_categories = [
                "Food",
                "Gifts",
                "Health/medical",
                "Home",
                "Transportation",
                "Personal",
                "Pets",
                "Family",
                "Travel",
                "Debt",
                "Other",
                "Rent",
                "Credit Card",
                "Alcohol",
                "Consumables",
                "Investments",
            ]

            income_categories = ["Savings", "Paycheck", "Bonus", "Interest", "Splitwise", "RSU"]

            account_types = ["Savings Account", "Credit Card"]
            banks = ["HDFC Bank", "Federal Bank"]

            # Get filter parameters
            category_filter = request.args.get("category")
            account_filter = request.args.get("account")
            bank_filter = request.args.get("bank")
            date_from = request.args.get("date_from")
            date_to = request.args.get("date_to")
            page = int(request.args.get("page", 1))
            per_page = int(request.args.get("per_page", 50))

            # Build query
            query = Transaction.query

            if category_filter:
                # Filter by tags JSON field or category column
                # Use LIKE pattern to match category in JSON array
                query = query.filter(
                    or_(
                        Transaction.tags.like(f'%"categories":%[%"{category_filter}"%]%'),
                        Transaction.category == category_filter,
                    )
                )

            # Always join Account table for filtering
            query = query.outerjoin(Account)

            if account_filter:
                # Filter by tags JSON field or account table
                # Check both the tags.account_type array and the Account table
                query = query.filter(
                    or_(
                        Transaction.tags.like(f'%"account_type":%[%"{account_filter}"%]%'),
                        Account.account_type == account_filter,
                    )
                )

            if bank_filter:
                query = query.filter(Account.bank == bank_filter)

            if date_from:
                date_from_obj = datetime.strptime(date_from, "%Y-%m-%d").date()
                query = query.filter(Transaction.date >= date_from_obj)

            if date_to:
                date_to_obj = datetime.strptime(date_to, "%Y-%m-%d").date()
                query = query.filter(Transaction.date <= date_to_obj)

            # Order by date (newest first)
            query = query.order_by(desc(Transaction.date))

            # Paginate
            transactions_paginated = query.paginate(page=page, per_page=per_page, error_out=False)

            return render_template(
                "transactions.html",
                transactions=transactions_paginated,
                categories=expense_categories + income_categories,
                account_types=account_types,
                banks=banks,
                expense_categories=expense_categories,
                income_categories=income_categories,
                filters={
                    "category": category_filter,
                    "account": account_filter,
                    "bank": bank_filter,
                    "date_from": date_from,
                    "date_to": date_to,
                },
            )
        except Exception as e:
            print(f"Error loading transactions: {e}")
            return render_template(
                "transactions.html",
                transactions=None,
                categories=[],
                account_types=[],
                banks=[],
                expense_categories=[],
                income_categories=[],
                filters={},
            )

    @app.route("/review-upload")
    def review_upload():
        """Review/confirmation page for uploaded transactions"""
        try:
            # Get parsed transactions from session
            pending_transactions = session.get("pending_transactions", [])

            if not pending_transactions:
                flash("No transactions to review", "warning")
                return redirect(url_for("index"))

            expense_categories = [
                "Food",
                "Gifts",
                "Health/medical",
                "Home",
                "Transportation",
                "Personal",
                "Pets",
                "Family",
                "Travel",
                "Debt",
                "Other",
                "Rent",
                "Credit Card",
                "Alcohol",
                "Consumables",
                "Investments",
            ]

            income_categories = ["Savings", "Paycheck", "Bonus", "Interest", "Splitwise", "RSU"]

            account_types = ["Savings Account", "Credit Card"]

            return render_template(
                "review_upload.html",
                transactions=pending_transactions,
                expense_categories=expense_categories,
                income_categories=income_categories,
                account_types=account_types,
            )
        except Exception as e:
            print(f"Error loading review page: {e}")
            flash("Error loading review page", "error")
            return redirect(url_for("index"))

    @app.route("/api/transactions", methods=["GET"])
    def api_get_transactions():
        """API endpoint to get transaction data"""
        try:
            transactions = Transaction.query.order_by(desc(Transaction.date)).limit(100).all()
            return jsonify([t.to_dict() for t in transactions])
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/transactions", methods=["POST"])
    def api_create_transaction():
        """API endpoint to create a new transaction"""
        try:
            data = request.get_json()

            # Validate required fields
            required_fields = ["description", "amount", "date"]
            for field in required_fields:
                if field not in data:
                    return jsonify({"error": f"Missing required field: {field}"}), 400

            # Get or create account based on account name and account_type
            if "account_id" not in data:
                bank = data.get("bank", "HDFC")
                account_type = data.get("account_type", "Savings Account")
                account = AccountService.get_or_create_account(
                    name=f"{bank} {account_type}", bank=bank, account_type=account_type
                )
                data["account_id"] = account.id

            # Auto-categorize if not provided
            if "category" not in data:
                data["category"] = CategoryService.categorize_transaction(
                    data["description"], float(data["amount"]), data.get("is_debit", True)
                )

            # Auto-subcategorize if not provided
            if "subcategory" not in data:
                data["subcategory"] = CategoryService.categorize_subcategory(data["description"], data["category"])

            # Create transaction
            transaction = TransactionService.create_transaction(data)

            return jsonify(transaction.to_dict()), 201
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/transactions/<int:transaction_id>", methods=["PUT"])
    def api_update_transaction(transaction_id):
        """API endpoint to update a transaction"""
        try:
            data = request.get_json()
            transaction = TransactionService.update_transaction(transaction_id, data)

            if not transaction:
                return jsonify({"error": "Transaction not found"}), 404

            return jsonify(transaction.to_dict())
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/transactions/<int:transaction_id>", methods=["DELETE"])
    def api_delete_transaction(transaction_id):
        """API endpoint to delete a transaction"""
        try:
            success = TransactionService.delete_transaction(transaction_id)

            if not success:
                return jsonify({"error": "Transaction not found"}), 404

            return jsonify({"message": "Transaction deleted successfully"})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/transactions/bulk-edit", methods=["POST"])
    def api_bulk_edit_transactions():
        """API endpoint to bulk edit transactions"""
        try:
            data = request.get_json()
            transaction_ids = data.get("transaction_ids", [])
            new_category = data.get("category")

            if not transaction_ids:
                return jsonify({"error": "No transactions selected"}), 400

            if not new_category:
                return jsonify({"error": "Category is required"}), 400

            # Update transactions
            updated_count = 0
            for transaction_id in transaction_ids:
                transaction = Transaction.query.get(transaction_id)
                if transaction:
                    transaction.category = new_category
                    updated_count += 1

            db.session.commit()

            return jsonify({"message": f"Successfully updated {updated_count} transactions", "updated_count": updated_count})
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500

    @app.route("/api/accounts", methods=["GET"])
    def api_get_accounts():
        """API endpoint to get accounts"""
        try:
            accounts = Account.query.filter_by(is_active=True).all()
            return jsonify([a.to_dict() for a in accounts])
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/categories", methods=["GET"])
    def api_get_categories():
        """API endpoint to get categories"""
        try:
            categories = Category.query.filter_by(is_active=True).all()
            return jsonify([c.to_dict() for c in categories])
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/dashboard/summary", methods=["GET"])
    def api_dashboard_summary():
        """API endpoint for dashboard summary data"""
        try:
            summary = TransactionService.get_transactions_summary()
            return jsonify(summary)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/charts/category_distribution", methods=["GET"])
    def api_category_distribution():
        """API endpoint for category distribution chart data"""
        try:
            # Get expense categories (excluding income)
            category_data = (
                db.session.query(Transaction.category, func.sum(Transaction.amount).label("total"))
                .filter(Transaction.is_debit == True, Transaction.category != "Income")
                .group_by(Transaction.category)
                .all()
            )

            if not category_data:
                return jsonify({})

            # Format for chart
            categories = {}
            for category, total in category_data:
                categories[category] = abs(float(total))

            # Generate colors
            labels = list(categories.keys())
            values = list(categories.values())
            colors = [f"hsl({hash(label) % 360}, 70%, 60%)" for label in labels]

            return jsonify({"labels": labels, "datasets": [{"data": values, "backgroundColor": colors}]})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/charts/category-distribution", methods=["GET"])
    def api_category_distribution_alt():
        """Alternative API endpoint for category distribution chart data"""
        try:
            # Get expense categories (excluding income)
            category_data = (
                db.session.query(Transaction.category, func.sum(Transaction.amount).label("total"))
                .filter(Transaction.is_debit == True, Transaction.category != "Income")
                .group_by(Transaction.category)
                .all()
            )

            return jsonify([{"category": category, "amount": float(abs(amount))} for category, amount in category_data])
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/charts/monthly_trends", methods=["GET"])
    def api_monthly_trends():
        """API endpoint for monthly income/expense trend (original format)"""
        try:
            # Get all transactions and process in Python
            transactions = Transaction.query.all()

            # Group by month
            monthly_data = {}
            for transaction in transactions:
                month_key = transaction.date.strftime("%Y-%m")
                if month_key not in monthly_data:
                    monthly_data[month_key] = {"income": 0, "expenses": 0}

                if transaction.is_debit:
                    monthly_data[month_key]["expenses"] += abs(float(transaction.amount))
                else:
                    monthly_data[month_key]["income"] += float(transaction.amount)

            # Sort by month and get last 12 months
            sorted_months = sorted(monthly_data.keys())[-12:]

            if not sorted_months:
                return jsonify({})

            # Format for chart
            labels = []
            income_data = []
            expense_data = []

            for month_key in sorted_months:
                # Format month label
                year, month = month_key.split("-")
                month_name = datetime(int(year), int(month), 1).strftime("%b")
                labels.append(f"{month_name} '{str(int(year))[2:]}")
                income_data.append(monthly_data[month_key]["income"])
                expense_data.append(monthly_data[month_key]["expenses"])

            return jsonify(
                {
                    "labels": labels,
                    "datasets": [
                        {"label": "Income", "data": income_data, "backgroundColor": "rgba(75, 192, 192, 0.6)"},
                        {"label": "Expenses", "data": expense_data, "backgroundColor": "rgba(255, 99, 132, 0.6)"},
                    ],
                }
            )
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/charts/monthly-trend", methods=["GET"])
    def api_monthly_trend():
        """API endpoint for monthly income/expense trend"""
        try:
            # Get all transactions and process in Python
            transactions = Transaction.query.all()

            # Group by month
            monthly_data = {}
            for transaction in transactions:
                month_key = transaction.date.strftime("%Y-%m")
                if month_key not in monthly_data:
                    monthly_data[month_key] = {"income": 0, "expenses": 0}

                if transaction.is_debit:
                    monthly_data[month_key]["expenses"] += abs(float(transaction.amount))
                else:
                    monthly_data[month_key]["income"] += float(transaction.amount)

            # Sort by month and get last 12 months
            sorted_months = sorted(monthly_data.keys())[-12:]

            return jsonify(
                [
                    {
                        "month": month_key,
                        "income": monthly_data[month_key]["income"],
                        "expenses": monthly_data[month_key]["expenses"],
                    }
                    for month_key in sorted_months
                ]
            )
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/charts/account_distribution", methods=["GET"])
    def api_account_distribution():
        """API endpoint for account distribution chart"""
        try:
            # Get all transactions and process in Python
            transactions = Transaction.query.join(Account).all()

            # Group by account
            account_data = {}
            for transaction in transactions:
                account_name = transaction.account.name
                if account_name not in account_data:
                    account_data[account_name] = {"income": 0, "expenses": 0}

                if transaction.is_debit:
                    account_data[account_name]["expenses"] += abs(float(transaction.amount))
                else:
                    account_data[account_name]["income"] += float(transaction.amount)

            if not account_data:
                return jsonify({})

            # Format for chart
            labels = []
            income_data = []
            expense_data = []

            for account_name, data in account_data.items():
                labels.append(account_name)
                income_data.append(data["income"])
                expense_data.append(data["expenses"])

            return jsonify(
                {
                    "labels": labels,
                    "datasets": [
                        {
                            "label": "Income",
                            "data": income_data,
                            "backgroundColor": "rgba(75, 192, 192, 0.6)",
                            "borderColor": "rgba(75, 192, 192, 1)",
                            "borderWidth": 1,
                        },
                        {
                            "label": "Expenses",
                            "data": expense_data,
                            "backgroundColor": "rgba(255, 99, 132, 0.6)",
                            "borderColor": "rgba(255, 99, 132, 1)",
                            "borderWidth": 1,
                        },
                    ],
                }
            )
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    def allowed_file(filename):
        """Check if file extension is allowed"""
        ALLOWED_EXTENSIONS = {"pdf", "csv", "txt"}
        return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

    def extract_transactions_from_file(filepath, bank, account_type, account_name):
        """Extract transactions from uploaded file using parsers"""
        try:
            # Import parsers
            from parsers import extract_transactions_from_file as parse_file

            # Use the parser system to extract transactions
            transactions = parse_file(filepath, bank, account_type, account_name)

            # Add metadata to transactions
            for transaction in transactions:
                transaction["bank"] = bank
                transaction["account_type"] = account_type
                transaction["account_name"] = account_name or f"{bank} {account_type.title()}"

                # Ensure required fields exist
                if "category" not in transaction:
                    transaction["category"] = "Uncategorized"
                if "subcategory" not in transaction:
                    transaction["subcategory"] = ""
                if "transaction_id" not in transaction:
                    transaction["transaction_id"] = f"{transaction['date']}_{transaction['amount']}_{len(transactions)}"

            return transactions
        except Exception as e:
            print(f"Error extracting transactions from file: {e}")
            return []

    def extract_transactions_from_file_new(filepath, bank, account_type, account_name):
        """Extract transactions from uploaded file for review flow"""
        try:
            if filepath.endswith(".pdf"):
                # Use appropriate parser
                if bank.lower() == "federal bank":
                    from parsers.federal_bank_parser import extract_federal_bank_savings

                    transactions = extract_federal_bank_savings(filepath)
                elif bank.lower() == "hdfc":
                    if account_type.lower() == "credit card":
                        from parsers.hdfc_credit_card import HDFCCreditCardParser

                        parser = HDFCCreditCardParser()
                        transactions = parser.parse(filepath)
                    else:
                        from parsers.hdfc_savings import HDFCSavingsParser

                        parser = HDFCSavingsParser()
                        transactions = parser.parse(filepath)
                else:
                    from parsers.generic import GenericParser

                    parser = GenericParser()
                    transactions = parser.parse(filepath)

                # Transform to our format
                formatted_transactions = []
                for trans in transactions:
                    amount = float(trans.get("amount", 0))
                    formatted_trans = {
                        "date": trans.get("date"),
                        "description": trans.get("description", ""),
                        "amount": amount,
                        "bank": bank,
                        "account_type": account_type,
                        "account_name": account_name,
                        "category": "Paycheck" if amount > 0 else "Other",
                        "subcategory": "",
                        "notes": "",
                    }
                    formatted_transactions.append(formatted_trans)

                return formatted_transactions
            else:
                # Handle CSV/Excel files
                return []

        except Exception as e:
            print(f"Error parsing file: {e}")
            return []

    @app.route("/upload", methods=["POST"])
    def upload_file():
        """Handle file upload with review/confirmation flow"""
        try:
            if "file" not in request.files:
                return jsonify({"error": "No file selected"}), 400

            file = request.files["file"]
            bank = request.form.get("bank", "HDFC")
            account_type = request.form.get("account_type", "Savings Account")
            account_name = request.form.get("account_name", f"{bank} {account_type}")

            if file.filename == "":
                return jsonify({"error": "No file selected"}), 400

            if not allowed_file(file.filename):
                return jsonify({"error": "Invalid file type. Please upload PDF, CSV, or Excel files."}), 400

            # Save file
            filename = secure_filename(file.filename)
            upload_path = os.path.join(app.config.get("UPLOAD_FOLDER", "uploads"), filename)
            os.makedirs(os.path.dirname(upload_path), exist_ok=True)
            file.save(upload_path)

            # Extract transactions
            transactions = extract_transactions_from_file_new(upload_path, bank, account_type, account_name)

            if not transactions:
                return jsonify({"error": "Could not extract transactions from file"}), 400

            # Store transactions in session for review
            session["pending_transactions"] = transactions

            # Return success with redirect URL
            return jsonify(
                {
                    "success": True,
                    "message": f"Extracted {len(transactions)} transactions",
                    "transaction_count": len(transactions),
                    "redirect_url": url_for("review_upload"),
                }
            )

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/upload/confirm", methods=["POST"])
    def confirm_upload():
        """Confirm and save reviewed transactions"""
        try:
            data = request.get_json()
            transactions_data = data.get("transactions", [])

            if not transactions_data:
                return jsonify({"error": "No transactions to save"}), 400

            saved_transactions = []

            for trans_data in transactions_data:
                # Get or create account
                bank = trans_data.get("bank", "HDFC")
                account_type = trans_data.get("account_type", "Savings Account")
                account = AccountService.get_or_create_account(
                    name=trans_data.get("account_name", f"{bank} {account_type}"), bank=bank, account_type=account_type
                )

                # Create transaction
                # Handle multiple date formats
                date_str = trans_data["date"]
                if "/" in date_str:
                    # Handle DD/MM/YYYY format
                    transaction_date = datetime.strptime(date_str, "%d/%m/%Y").date()
                else:
                    # Handle YYYY-MM-DD format
                    transaction_date = datetime.strptime(date_str, "%Y-%m-%d").date()

                transaction = Transaction(
                    date=transaction_date,
                    description=trans_data["description"],
                    amount=float(trans_data["amount"]),
                    category=trans_data.get("category", "Other"),
                    subcategory=trans_data.get("subcategory"),
                    account_id=account.id,
                    is_debit=float(trans_data["amount"]) < 0,
                    transaction_type="pdf_parsed",
                    notes=trans_data.get("notes"),
                )

                # Set tags - combine categories and account types
                tags = {"categories": [trans_data.get("category", "Other")], "account_type": [account_type]}
                transaction.set_tags(tags)

                # Also set legacy fields for backward compatibility
                transaction.category = trans_data.get("category", "Other")
                transaction.bank = bank

                db.session.add(transaction)
                saved_transactions.append(transaction)

            db.session.commit()

            # Clear pending transactions from session
            session.pop("pending_transactions", None)

            return jsonify(
                {
                    "success": True,
                    "message": f"Successfully saved {len(saved_transactions)} transactions",
                    "transaction_count": len(saved_transactions),
                }
            )

        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500

    @app.route("/health")
    def health_check():
        """Health check endpoint"""
        try:
            # Check database connection
            transaction_count = Transaction.query.count()
            account_count = Account.query.count()

            return jsonify(
                {"status": "healthy", "database": "connected", "transactions": transaction_count, "accounts": account_count}
            )
        except Exception as e:
            return jsonify({"status": "unhealthy", "error": str(e)}), 500

    @app.route("/debug/db")
    def debug_db():
        """Debug endpoint to check database configuration and data"""
        try:
            import os

            from flask import current_app

            # Get current config
            db_uri = current_app.config.get("SQLALCHEMY_DATABASE_URI", "Not configured")

            # Check transaction count
            transaction_count = Transaction.query.count()
            account_count = Account.query.count()

            # Get sample transactions
            sample_transactions = []
            transactions = Transaction.query.limit(5).all()
            for t in transactions:
                sample_transactions.append(
                    {
                        "id": t.id,
                        "date": t.date.isoformat(),
                        "description": t.description[:50],
                        "amount": float(t.amount),
                        "is_debit": t.is_debit,
                    }
                )

            # Check if database file exists
            db_file_exists = "N/A"
            if "sqlite" in db_uri:
                db_path = db_uri.replace("sqlite:///", "")
                if not db_path.startswith("/"):
                    db_path = os.path.join(os.getcwd(), db_path)
                db_file_exists = os.path.exists(db_path)

            return jsonify(
                {
                    "database_uri": db_uri,
                    "transaction_count": transaction_count,
                    "account_count": account_count,
                    "sample_transactions": sample_transactions,
                    "database_file_exists": db_file_exists,
                    "working_directory": os.getcwd(),
                }
            )
        except Exception as e:
            return (
                jsonify(
                    {"error": str(e), "database_uri": current_app.config.get("SQLALCHEMY_DATABASE_URI", "Not configured")}
                ),
                500,
            )

    @app.route("/api/analytics/tags", methods=["GET"])
    def api_tag_analytics():
        """API endpoint to get tag-based analytics"""
        try:
            analytics = TransactionService.get_tag_analytics()
            return jsonify(analytics)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/analytics/spending", methods=["GET"])
    def api_spending_analysis():
        """API endpoint to get spending analysis by category and account"""
        try:
            categories = request.args.getlist("categories")
            accounts = request.args.getlist("accounts")
            date_from = request.args.get("date_from")
            date_to = request.args.get("date_to")

            # Parse dates if provided
            date_from_obj = None
            date_to_obj = None
            if date_from:
                date_from_obj = datetime.strptime(date_from, "%Y-%m-%d").date()
            if date_to:
                date_to_obj = datetime.strptime(date_to, "%Y-%m-%d").date()

            analysis = TransactionService.get_spending_by_category_and_account(
                categories=categories if categories else None,
                accounts=accounts if accounts else None,
                date_from=date_from_obj,
                date_to=date_to_obj,
            )

            return jsonify(analysis)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/transactions/by-tags", methods=["GET"])
    def api_transactions_by_tags():
        """API endpoint to get transactions filtered by tags"""
        try:
            tag_filters = {}
            date_from = request.args.get("date_from")
            date_to = request.args.get("date_to")

            # Parse tag filters from query parameters
            for param in request.args:
                if param.startswith("tags["):
                    # Extract tag type from parameter name like 'tags[categories]'
                    tag_type = param[5:-1]  # Remove 'tags[' and ']'
                    tag_values = request.args.getlist(param)
                    tag_filters[tag_type] = tag_values

            transactions = TransactionService.get_transactions_by_tags(
                tag_filters=tag_filters,
                date_from=datetime.strptime(date_from, "%Y-%m-%d").date() if date_from else None,
                date_to=datetime.strptime(date_to, "%Y-%m-%d").date() if date_to else None,
            )

            return jsonify([t.to_dict() for t in transactions])
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/dashboard/tag-analytics", methods=["GET"])
    def api_dashboard_tag_analytics():
        """Comprehensive tag-based dashboard analytics"""
        try:
            date_from = request.args.get("date_from")
            date_to = request.args.get("date_to")

            # Parse date filters
            from_date = datetime.strptime(date_from, "%Y-%m-%d").date() if date_from else None
            to_date = datetime.strptime(date_to, "%Y-%m-%d").date() if date_to else None

            # Get all transactions in date range
            query = Transaction.query
            if from_date:
                query = query.filter(Transaction.date >= from_date)
            if to_date:
                query = query.filter(Transaction.date <= to_date)

            transactions = query.all()

            # Aggregate analytics
            analytics = {
                "total_transactions": len(transactions),
                "total_income": 0,
                "total_expenses": 0,
                "category_breakdown": {},
                "bank_breakdown": {},
                "account_breakdown": {},
                "monthly_trends": {},
                "top_categories": [],
                "spending_by_account_and_category": [],
                "tag_combinations": {},
            }

            # Process each transaction
            for transaction in transactions:
                amount = float(transaction.amount)
                tags = transaction.get_tags()

                # Income/Expense totals
                if transaction.is_debit:
                    analytics["total_expenses"] += abs(amount)
                else:
                    analytics["total_income"] += amount

                # Monthly trends
                month_key = transaction.date.strftime("%Y-%m")
                if month_key not in analytics["monthly_trends"]:
                    analytics["monthly_trends"][month_key] = {"income": 0, "expenses": 0}

                if transaction.is_debit:
                    analytics["monthly_trends"][month_key]["expenses"] += abs(amount)
                else:
                    analytics["monthly_trends"][month_key]["income"] += amount

                # Tag-based breakdowns
                categories = tags.get("categories", [transaction.category] if transaction.category else ["Miscellaneous"])
                banks = tags.get("banks", [])
                accounts = tags.get("accounts", [])

                # Category breakdown
                for category in categories:
                    if category not in analytics["category_breakdown"]:
                        analytics["category_breakdown"][category] = {"income": 0, "expenses": 0, "count": 0}

                    analytics["category_breakdown"][category]["count"] += 1
                    if transaction.is_debit:
                        analytics["category_breakdown"][category]["expenses"] += abs(amount)
                    else:
                        analytics["category_breakdown"][category]["income"] += amount

                # Bank breakdown
                for bank in banks:
                    if bank not in analytics["bank_breakdown"]:
                        analytics["bank_breakdown"][bank] = {"income": 0, "expenses": 0, "count": 0}

                    analytics["bank_breakdown"][bank]["count"] += 1
                    if transaction.is_debit:
                        analytics["bank_breakdown"][bank]["expenses"] += abs(amount)
                    else:
                        analytics["bank_breakdown"][bank]["income"] += amount

                # Account breakdown
                for account in accounts:
                    if account not in analytics["account_breakdown"]:
                        analytics["account_breakdown"][account] = {"income": 0, "expenses": 0, "count": 0}

                    analytics["account_breakdown"][account]["count"] += 1
                    if transaction.is_debit:
                        analytics["account_breakdown"][account]["expenses"] += abs(amount)
                    else:
                        analytics["account_breakdown"][account]["income"] += amount

                # Tag combinations for advanced insights
                if categories and banks:
                    for category in categories:
                        for bank in banks:
                            combo_key = f"{category}|{bank}"
                            if combo_key not in analytics["tag_combinations"]:
                                analytics["tag_combinations"][combo_key] = {"income": 0, "expenses": 0, "count": 0}

                            analytics["tag_combinations"][combo_key]["count"] += 1
                            if transaction.is_debit:
                                analytics["tag_combinations"][combo_key]["expenses"] += abs(amount)
                            else:
                                analytics["tag_combinations"][combo_key]["income"] += amount

            # Calculate derived metrics
            analytics["net_balance"] = analytics["total_income"] - analytics["total_expenses"]

            # Top categories by expense amount
            analytics["top_categories"] = sorted(
                [{"name": k, **v} for k, v in analytics["category_breakdown"].items()],
                key=lambda x: x["expenses"],
                reverse=True,
            )[:10]

            # Spending by account and category combinations
            analytics["spending_by_account_and_category"] = [
                {"combination": k.replace("|", " via "), "category": k.split("|")[0], "bank": k.split("|")[1], **v}
                for k, v in analytics["tag_combinations"].items()
                if v["expenses"] > 0
            ]
            analytics["spending_by_account_and_category"].sort(key=lambda x: x["expenses"], reverse=True)

            return jsonify(analytics)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/dashboard/filters", methods=["GET"])
    def api_dashboard_filters():
        """Get available filter options from existing tags"""
        try:
            # Get all unique tags from transactions
            transactions = Transaction.query.all()

            filters = {"categories": set(), "banks": set(), "accounts": set(), "date_range": {"min": None, "max": None}}

            for transaction in transactions:
                tags = transaction.get_tags()

                # Collect unique values
                for category in tags.get("categories", []):
                    filters["categories"].add(category)

                for bank in tags.get("banks", []):
                    filters["banks"].add(bank)

                for account in tags.get("accounts", []):
                    filters["accounts"].add(account)

                # Date range
                if not filters["date_range"]["min"] or transaction.date < filters["date_range"]["min"]:
                    filters["date_range"]["min"] = transaction.date
                if not filters["date_range"]["max"] or transaction.date > filters["date_range"]["max"]:
                    filters["date_range"]["max"] = transaction.date

            # Convert sets to sorted lists
            filters["categories"] = sorted(list(filters["categories"]))
            filters["banks"] = sorted(list(filters["banks"]))
            filters["accounts"] = sorted(list(filters["accounts"]))

            # Format dates
            if filters["date_range"]["min"]:
                filters["date_range"]["min"] = filters["date_range"]["min"].isoformat()
            if filters["date_range"]["max"]:
                filters["date_range"]["max"] = filters["date_range"]["max"].isoformat()

            return jsonify(filters)
        except Exception as e:
            return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
