import os
from datetime import datetime

from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for
from flask_migrate import Migrate
from flask_cors import CORS, cross_origin
from sqlalchemy import desc, func, or_
from werkzeug.utils import secure_filename

from config import config
from models import Account, Category, Transaction, db
from services import AccountService, TransactionService

# Import background task manager
from background_tasks import task_manager
# Import monitoring routes
from monitoring_routes import register_monitoring_routes

# Import monitoring components
from monitoring import init_monitoring, HealthChecker, MetricsCollector, StructuredLogger


# Initialize Flask app
def create_app(config_name=None):
    """Create and configure the Flask application"""
    app = Flask(__name__)

    # Load configuration
    config_name = config_name or os.environ.get("FLASK_ENV", "development")
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    # Initialize extensions
    db.init_app(app)
    Migrate(app, db)
    
    # Initialize monitoring components
    init_monitoring(app)
    # Initialize CORS
    CORS(app, origins=["http://localhost:3000", "http://localhost:8080", "http://127.0.0.1:8080"])

    # Make config available to templates
    @app.context_processor
    def inject_config():
        return dict(config=app.config)

    # Register routes
    # Register monitoring routes
    register_monitoring_routes(app)
    register_routes(app)

    # Create tables
    with app.app_context():
        db.create_all()

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

    @app.route("/api/pending-transactions", methods=["GET"])
    def api_get_pending_transactions():
        """API endpoint to get pending transactions from session"""
        try:
            pending_transactions = session.get("pending_transactions", [])
            return jsonify({
                "transactions": pending_transactions,
                "count": len(pending_transactions)
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500

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
        """Create a new transaction"""
        try:
            # Validate JSON data
            if not request.is_json:
                return jsonify({"error": "Content-Type must be application/json"}), 400

            try:
                data = request.get_json()
            except Exception:
                return jsonify({"error": "Invalid JSON data"}), 400

            if data is None:
                return jsonify({"error": "Invalid JSON data"}), 400

            # Validate required fields
            required_fields = ["date", "description", "amount"]
            for field in required_fields:
                if field not in data:
                    return jsonify({"error": f"Missing required field: {field}"}), 400

            # Handle bank + account_type combination
            if "bank" in data and "account_type" in data:
                # Create account name from bank and account_type
                account_name = f"{data['bank']} {data['account_type']}"
                
                # Get or create the account
                account = AccountService.get_or_create_account(
                    name=account_name,
                    account_type=data["account_type"],
                    bank=data["bank"]
                )
                
                # Add account_id to the data
                data["account_id"] = account.id
                
                # Remove bank and account_type from data as they're not needed for TransactionService
                data.pop("bank", None)
                data.pop("account_type", None)

            # Create transaction using service
            transaction = TransactionService.create_transaction(data)
            return jsonify(transaction.to_dict()), 201
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/transactions/<int:transaction_id>", methods=["GET"])
    def api_get_transaction(transaction_id):
        """Get a specific transaction by ID"""
        try:
            transaction = Transaction.query.get(transaction_id)
            if not transaction:
                return jsonify({"error": "Transaction not found"}), 404

            return jsonify(transaction.to_dict())
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
                .filter(Transaction.is_debit.is_(True), Transaction.category != "Income")
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
                .filter(Transaction.is_debit.is_(True), Transaction.category != "Income")
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
        """Extract transactions from uploaded file for review flow using Universal LLM Parser"""
        try:
            if filepath.endswith(".pdf"):
                # Use Universal LLM Parser for all PDF files
                from parsers.universal_llm_parser import UniversalLLMParser
                from parsers.exceptions import PDFParsingError
                
                # Extract text from PDF
                import fitz  # PyMuPDF
                doc = fitz.open(filepath)
                pdf_text = ""
                for page in doc:
                    pdf_text += page.get_text()
                doc.close()
                
                if not pdf_text or len(pdf_text.strip()) < 100:
                    raise PDFParsingError("Failed to extract meaningful text from PDF", "pdf_extraction_failed")
                
                # Use Universal LLM Parser
                parser = UniversalLLMParser(enable_llm=True)
                transactions = parser.parse_statement(pdf_text, bank)

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
                        "category": trans.get("category", "Other"),
                        "subcategory": "",
                        "notes": "",
                    }
                    formatted_transactions.append(formatted_trans)

                return formatted_transactions
            else:
                # Handle CSV/Excel files
                return []

        except PDFParsingError:
            # Re-raise PDFParsingError to preserve error handling
            raise
        except Exception as e:
            print(f"Error parsing file: {e}")
            raise PDFParsingError(f"Unexpected error parsing file: {str(e)}", "unexpected_error")

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
            try:
                transactions = extract_transactions_from_file_new(upload_path, bank, account_type, account_name)

                if not transactions:
                    return jsonify({
                        "error": "Could not extract transactions from file",
                        "error_type": "no_transactions_found",
                        "user_message": f"No transactions could be found in the {bank} statement. Please verify the PDF contains transaction data."
                    }), 400

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

            except Exception as pe:
                # Import here to avoid circular imports
                from parsers.exceptions import PDFParsingError
                
                if isinstance(pe, PDFParsingError):
                    # Map error types to user-friendly messages
                    error_messages = {
                        'llm_service_unavailable': 'The AI service is currently unavailable. Please ensure the LLM service is running and try again.',
                        'llm_service_disabled': 'AI parsing is currently disabled. Please contact support.',
                        'invalid_pdf_content': 'The PDF file appears to be empty or corrupted. Please upload a valid bank statement.',
                        'no_transactions_found': f'No transactions could be found in the {bank} statement. Please verify the PDF contains transaction data.',
                        'json_parsing_error': f'The AI service had trouble understanding the {bank} statement format. This PDF format may not be supported.',
                        'llm_timeout': f'Processing the {bank} statement took too long. The PDF may be too large or complex.',
                        'llm_connection_error': 'Cannot connect to the AI service. Please check your connection and try again.',
                        'llm_processing_error': f'An error occurred while processing the {bank} statement with AI.',
                        'validation_failed': 'The extracted transaction data failed validation. The PDF may contain invalid data.',
                        'pdf_extraction_failed': 'Could not extract readable text from the PDF. The file may be corrupted or password-protected.',
                        'unexpected_error': 'An unexpected error occurred while processing the PDF.'
                    }
                    
                    user_message = error_messages.get(pe.error_type, pe.message)
                    
                    return jsonify({
                        "error": pe.message,
                        "error_type": pe.error_type,
                        "user_message": user_message
                    }), 422  # Unprocessable Entity
                else:
                    # Handle other exceptions
                    return jsonify({
                        "error": str(pe),
                        "error_type": "unexpected_error",
                        "user_message": "An unexpected error occurred while processing your PDF. Please try again."
                    }), 500

        except Exception as e:
            return jsonify({
                "error": str(e),
                "error_type": "server_error",
                "user_message": "A server error occurred. Please try again later."
            }), 500

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

    # Phase 3: New File Upload Routes with Async Processing
    @app.route("/api/upload-statement", methods=["POST"])
    @cross_origin()
    def api_upload_statement():
        """Phase 3: Upload statement file with async processing"""
        try:
            # Validate file upload
            if "file" not in request.files:
                return jsonify({"error": "No file provided"}), 400
            
            file = request.files["file"]
            if file.filename == "":
                return jsonify({"error": "No file selected"}), 400
            
            # Get form data
            bank_type = request.form.get("bank_type")
            account_id = request.form.get("account_id")
            
            if not bank_type:
                return jsonify({"error": "Bank type is required"}), 400
            
            if not account_id:
                return jsonify({"error": "Account ID is required"}), 400
            
            # Validate file type
            if not allowed_file(file.filename):
                return jsonify({
                    "error": "Invalid file type. Supported formats: PDF, CSV, Excel"
                }), 400
            
            # Check file size
            file.seek(0, 2)  # Seek to end
            file_size = file.tell()
            file.seek(0)  # Reset to beginning
            
            max_size = app.config.get("MAX_CONTENT_LENGTH", 16 * 1024 * 1024)
            if file_size > max_size:
                return jsonify({
                    "error": f"File too large. Maximum size: {max_size // (1024*1024)}MB"
                }), 400
            
            # Get user context (for now, use a default user_id)
            # In production, extract from session/JWT token
            user_id = session.get("user_id", "default_user")
            
            # Save file temporarily
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_filename = f"{timestamp}_{filename}"
            
            upload_path = os.path.join(app.config.get("UPLOAD_FOLDER", "uploads"), safe_filename)
            os.makedirs(os.path.dirname(upload_path), exist_ok=True)
            file.save(upload_path)
            
            # Start background processing
            trace_id = task_manager.start_file_processing(
                file_path=upload_path,
                filename=filename,
                user_id=user_id,
                account_id=account_id,
                bank_type=bank_type
            )
            
            return jsonify({
                "success": True,
                "trace_id": trace_id,
                "message": "File uploaded successfully. Processing started.",
                "filename": filename,
                "file_size": file_size,
                "status_url": f"/api/upload-status/{trace_id}",
                "results_url": f"/api/upload-results/{trace_id}"
            }), 202
            
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/upload-status/<trace_id>", methods=["GET"])
    @cross_origin()
    def api_upload_status(trace_id):
        """Get upload processing status by trace ID"""
        try:
            # Get user context
            user_id = session.get("user_id", "default_user")
            
            # Get task status
            task_status = task_manager.get_task_status(trace_id)
            
            if not task_status:
                return jsonify({"error": "Task not found"}), 404
            
            # Basic authorization check
            if task_status.get("user_id") != user_id:
                return jsonify({"error": "Unauthorized"}), 403
            
            # Return status information
            response_data = {
                "trace_id": trace_id,
                "status": task_status["status"],
                "progress": task_status["progress"],
                "message": task_status["message"],
                "created_at": task_status["created_at"],
                "updated_at": task_status["updated_at"],
                "filename": task_status["filename"]
            }
            
            # Include error details if present
            if task_status.get("error"):
                response_data["error"] = task_status["error"]
            
            # Include completion info if done
            if task_status["status"] == "completed":
                response_data["transaction_count"] = len(task_status.get("transactions", []))
                response_data["results_url"] = f"/api/upload-results/{trace_id}"
            
            return jsonify(response_data)
            
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/upload-results/<trace_id>", methods=["GET"])
    @cross_origin()
    def api_upload_results(trace_id):
        """Get extracted transactions for review"""
        try:
            # Get user context
            user_id = session.get("user_id", "default_user")
            
            # Get task results
            results = task_manager.get_task_results(trace_id)
            
            if not results:
                task_status = task_manager.get_task_status(trace_id)
                if not task_status:
                    return jsonify({"error": "Task not found"}), 404
                elif task_status["status"] != "completed":
                    return jsonify({
                        "error": "Processing not completed yet",
                        "status": task_status["status"],
                        "progress": task_status["progress"]
                    }), 202
                else:
                    return jsonify({"error": "Results not available"}), 404
            
            # Basic authorization check
            task_status = task_manager.get_task_status(trace_id)
            if task_status and task_status.get("user_id") != user_id:
                return jsonify({"error": "Unauthorized"}), 403
            
            # Format response
            response_data = {
                "trace_id": trace_id,
                "status": results["status"],
                "filename": results["filename"],
                "bank_type": results["bank_type"],
                "account_id": results["account_id"],
                "transactions": results["transactions"],
                "metadata": results["metadata"],
                "transaction_count": len(results["transactions"]),
                "confirm_url": f"/api/confirm-transactions/{trace_id}"
            }
            
            return jsonify(response_data)
            
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/confirm-transactions/<trace_id>", methods=["POST"])
    @cross_origin()
    def api_confirm_transactions(trace_id):
        """Confirm and save extracted transactions"""
        try:
            # Get user context
            user_id = session.get("user_id", "default_user")
            
            # Get request data
            data = request.get_json() if request.is_json else {}
            transaction_confirmations = data.get("transactions", None)
            
            # Confirm transactions
            result = task_manager.confirm_transactions(
                trace_id=trace_id,
                user_id=user_id,
                transaction_confirmations=transaction_confirmations
            )
            
            return jsonify(result)
            
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/cancel-upload/<trace_id>", methods=["POST"])
    @cross_origin()
    def api_cancel_upload(trace_id):
        """Cancel a running upload task"""
        try:
            # Get user context
            user_id = session.get("user_id", "default_user")
            
            # Cancel task
            success = task_manager.cancel_task(trace_id, user_id)
            
            if not success:
                return jsonify({"error": "Task not found or unauthorized"}), 404
            
            return jsonify({
                "success": True,
                "message": "Upload task cancelled successfully",
                "trace_id": trace_id
            })
            
        except Exception as e:
            return jsonify({"error": str(e)}), 500


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

    @app.route("/confirm-upload", methods=["POST"])
    def confirm_upload_legacy():
        """Legacy confirm upload endpoint - redirects to new API endpoint"""
        if "pending_transactions" not in session:
            return redirect(url_for("transactions"))
        
        return redirect(url_for("review_upload"))


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5001)), debug=True)

# Create app instance for gunicorn
app = create_app()
