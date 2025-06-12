import os
from flask import Flask, request, jsonify, render_template, redirect, url_for, send_from_directory, flash
from flask_migrate import Migrate
from datetime import datetime, timedelta
from sqlalchemy import desc, func
from werkzeug.utils import secure_filename
import json

from models import db, Transaction, Account, Category, User
from services import TransactionService, CategoryService, AccountService, DataMigrationService
from config import config

# Define expense and income categories as per requirements
EXPENSE_CATEGORIES = [
    'Food', 'Gifts', 'Health/medical', 'Home', 'Transportation', 
    'Personal', 'Pets', 'Family', 'Travel', 'Debt', 'Other', 
    'Rent', 'Credit Card', 'Alcohol', 'Consumables', 'Investments'
]

INCOME_CATEGORIES = [
    'Savings', 'Paycheck', 'Bonus', 'Interest', 'Splitwise', 'RSU'
]

ACCOUNT_TYPES = ['Savings Account', 'Credit Card']

BANKS = ['HDFC', 'Federal Bank']

# Initialize Flask app
def create_app(config_name=None):
    app = Flask(__name__)
    
    # Load configuration
    config_name = config_name or os.environ.get('FLASK_ENV', 'development')
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
        if Transaction.query.count() == 0:
            DataMigrationService.migrate_from_json()
    
    return app

def register_routes(app):
    
    @app.route('/')
    def index():
        """Main dashboard page with analytics"""
        try:
            # Get summary data
            summary = TransactionService.get_transactions_summary()
            
            # Get recent transactions
            recent_transactions = Transaction.query.order_by(desc(Transaction.date)).limit(10).all()
            
            # Get accounts
            accounts = Account.query.filter_by(is_active=True).all()
            
            # Get all available filter options
            available_categories = EXPENSE_CATEGORIES + INCOME_CATEGORIES
            available_account_types = ACCOUNT_TYPES
            available_banks = BANKS
            
            return render_template('index.html', 
                                 summary=summary,
                                 recent_transactions=[t.to_dict() for t in recent_transactions],
                                 accounts=[a.to_dict() for a in accounts],
                                 available_categories=available_categories,
                                 available_account_types=available_account_types,
                                 available_banks=available_banks)
        except Exception as e:
            print(f"Error loading dashboard: {e}")
            return render_template('index.html', 
                                 summary={
                                     'total_transactions': 0,
                                     'total_income': 0,
                                     'total_expenses': 0,
                                     'net_balance': 0
                                 },
                                 recent_transactions=[],
                                 accounts=[],
                                 available_categories=[],
                                 available_account_types=[],
                                 available_banks=[])
    
    @app.route('/transactions')
    def transactions():
        """Transactions page with filtering and pagination"""
        try:
            # Get filter parameters
            category_filter = request.args.get('category')
            account_filter = request.args.get('account')
            bank_filter = request.args.get('bank')
            date_from = request.args.get('date_from')
            date_to = request.args.get('date_to')
            page = int(request.args.get('page', 1))
            per_page = int(request.args.get('per_page', 50))
            
            # Build query
            query = Transaction.query
            
            if category_filter:
                query = query.filter(Transaction.category == category_filter)
            
            if account_filter:
                query = query.join(Account).filter(Account.account_type == account_filter)
                
            if bank_filter:
                query = query.join(Account).filter(Account.bank == bank_filter)
            
            if date_from:
                date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
                query = query.filter(Transaction.date >= date_from_obj)
            
            if date_to:
                date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
                query = query.filter(Transaction.date <= date_to_obj)
            
            # Order by date (newest first)
            query = query.order_by(desc(Transaction.date))
            
            # Paginate
            transactions_paginated = query.paginate(
                page=page, per_page=per_page, error_out=False
            )
            
            # Get filter options
            categories = EXPENSE_CATEGORIES + INCOME_CATEGORIES
            account_types = ACCOUNT_TYPES
            banks = BANKS
            
            return render_template('transactions.html',
                                 transactions=transactions_paginated,
                                 categories=categories,
                                 account_types=account_types,
                                 banks=banks,
                                 filters={
                                     'category': category_filter,
                                     'account': account_filter,
                                     'bank': bank_filter,
                                     'date_from': date_from,
                                     'date_to': date_to
                                 })
        except Exception as e:
            print(f"Error loading transactions: {e}")
            return render_template('transactions.html',
                                 transactions=None,
                                 categories=[],
                                 account_types=[],
                                 banks=[],
                                 filters={})
    
    @app.route('/review-upload')
    def review_upload():
        """Review/confirmation page for uploaded transactions"""
        try:
            # Get parsed transactions from session or temp storage
            # For now, we'll get recent unparsed transactions
            pending_transactions = request.args.get('transactions', '[]')
            if isinstance(pending_transactions, str):
                pending_transactions = json.loads(pending_transactions)
            
            return render_template('review_upload.html',
                                 transactions=pending_transactions,
                                 expense_categories=EXPENSE_CATEGORIES,
                                 income_categories=INCOME_CATEGORIES,
                                 account_types=ACCOUNT_TYPES)
        except Exception as e:
            print(f"Error loading review page: {e}")
            flash('Error loading review page', 'error')
            return redirect(url_for('index'))
    
    @app.route('/api/transactions', methods=['GET'])
    def api_get_transactions():
        """API endpoint to get transaction data"""
        try:
            transactions = Transaction.query.order_by(desc(Transaction.date)).limit(100).all()
            return jsonify([t.to_dict() for t in transactions])
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/transactions', methods=['POST'])
    def api_create_transaction():
        """API endpoint to create a new transaction"""
        try:
            data = request.get_json()
            
            # Validate required fields
            required_fields = ['description', 'amount', 'date']
            for field in required_fields:
                if field not in data:
                    return jsonify({'error': f'Missing required field: {field}'}), 400
            
            # Get or create account
            bank = data.get('bank', 'HDFC')
            account_type = data.get('account_type', 'Savings Account')
            account = AccountService.get_or_create_account(
                name=f"{bank} {account_type}",
                bank=bank,
                account_type=account_type
            )
            
            # Auto-categorize if not provided
            category = data.get('category')
            if not category:
                amount = float(data['amount'])
                if amount > 0:
                    category = 'Income'  # Will be refined in review
                else:
                    category = 'Other'  # Will be refined in review
            
            # Create transaction
            transaction = Transaction(
                date=datetime.strptime(data['date'], '%Y-%m-%d').date(),
                description=data['description'],
                amount=float(data['amount']),
                category=category,
                subcategory=data.get('subcategory'),
                account_id=account.id,
                is_debit=float(data['amount']) < 0,
                notes=data.get('notes')
            )
            
            # Set tags (only categories and account type)
            tags = {
                'categories': [category] if category else [],
                'account_type': [account_type]
            }
            transaction.set_tags(tags)
            
            db.session.add(transaction)
            db.session.commit()
            
            return jsonify(transaction.to_dict()), 201
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/transactions/<int:transaction_id>', methods=['PUT'])
    def api_update_transaction(transaction_id):
        """API endpoint to update a transaction"""
        try:
            transaction = Transaction.query.get_or_404(transaction_id)
            data = request.get_json()
            
            # Update fields
            if 'description' in data:
                transaction.description = data['description']
            if 'amount' in data:
                transaction.amount = float(data['amount'])
                transaction.is_debit = float(data['amount']) < 0
            if 'date' in data:
                transaction.date = datetime.strptime(data['date'], '%Y-%m-%d').date()
            if 'category' in data:
                transaction.category = data['category']
            if 'subcategory' in data:
                transaction.subcategory = data['subcategory']
            if 'notes' in data:
                transaction.notes = data['notes']
            
            # Update tags if provided
            if 'tags' in data:
                tags = data['tags']
                # Ensure tags only contain valid categories and account type
                valid_tags = {
                    'categories': [tag for tag in tags.get('categories', []) 
                                 if tag in EXPENSE_CATEGORIES + INCOME_CATEGORIES],
                    'account_type': [tag for tag in tags.get('account_type', []) 
                                   if tag in ACCOUNT_TYPES]
                }
                transaction.set_tags(valid_tags)
            
            transaction.updated_at = datetime.utcnow()
            db.session.commit()
            
            return jsonify(transaction.to_dict())
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/transactions/<int:transaction_id>', methods=['DELETE'])
    def api_delete_transaction(transaction_id):
        """API endpoint to delete a transaction"""
        try:
            transaction = Transaction.query.get_or_404(transaction_id)
            db.session.delete(transaction)
            db.session.commit()
            return jsonify({'message': 'Transaction deleted successfully'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500
    
    def allowed_file(filename):
        """Check if file extension is allowed"""
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'pdf', 'csv', 'xlsx', 'xls'}
    
    def extract_transactions_from_file(filepath, bank, account_type, account_name):
        """Extract transactions from uploaded file"""
        try:
            if filepath.endswith('.pdf'):
                # Use appropriate parser
                if bank.lower() == 'federal bank':
                    from parsers.federal_bank_parser import FederalBankParser
                    parser = FederalBankParser()
                elif bank.lower() == 'hdfc':
                    if account_type.lower() == 'credit card':
                        from parsers.hdfc_credit_card import HDFCCreditCardParser
                        parser = HDFCCreditCardParser()
                    else:
                        from parsers.hdfc_savings import HDFCSavingsParser
                        parser = HDFCSavingsParser()
                else:
                    from parsers.generic import GenericParser
                    parser = GenericParser()
                
                transactions = parser.parse(filepath)
                
                # Transform to our format
                formatted_transactions = []
                for trans in transactions:
                    formatted_trans = {
                        'date': trans.get('date'),
                        'description': trans.get('description', ''),
                        'amount': float(trans.get('amount', 0)),
                        'bank': bank,
                        'account_type': account_type,
                        'account_name': account_name,
                        'category': 'Income' if float(trans.get('amount', 0)) > 0 else 'Other',
                        'tags': {
                            'categories': ['Income' if float(trans.get('amount', 0)) > 0 else 'Other'],
                            'account_type': [account_type]
                        }
                    }
                    formatted_transactions.append(formatted_trans)
                
                return formatted_transactions
            else:
                # Handle CSV/Excel files
                return []
                
        except Exception as e:
            print(f"Error parsing file: {e}")
            return []
    
    @app.route('/upload', methods=['POST'])
    def upload_file():
        """Handle file upload with review/confirmation flow"""
        try:
            if 'file' not in request.files:
                return jsonify({'error': 'No file selected'}), 400
            
            file = request.files['file']
            bank = request.form.get('bank', 'HDFC')
            account_type = request.form.get('account_type', 'Savings Account')
            account_name = request.form.get('account_name', f'{bank} {account_type}')
            
            if file.filename == '':
                return jsonify({'error': 'No file selected'}), 400
            
            if not allowed_file(file.filename):
                return jsonify({'error': 'Invalid file type. Please upload PDF, CSV, or Excel files.'}), 400
            
            # Save file
            filename = secure_filename(file.filename)
            upload_path = os.path.join(app.config.get('UPLOAD_FOLDER', 'uploads'), filename)
            os.makedirs(os.path.dirname(upload_path), exist_ok=True)
            file.save(upload_path)
            
            # Extract transactions
            transactions = extract_transactions_from_file(upload_path, bank, account_type, account_name)
            
            if not transactions:
                return jsonify({'error': 'Could not extract transactions from file'}), 400
            
            # Redirect to review page with transactions
            return jsonify({
                'success': True,
                'message': f'Extracted {len(transactions)} transactions',
                'transactions': transactions,
                'redirect_url': url_for('review_upload')
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/upload/confirm', methods=['POST'])
    def confirm_upload():
        """Confirm and save reviewed transactions"""
        try:
            data = request.get_json()
            transactions_data = data.get('transactions', [])
            
            if not transactions_data:
                return jsonify({'error': 'No transactions to save'}), 400
            
            saved_transactions = []
            
            for trans_data in transactions_data:
                # Get or create account
                bank = trans_data.get('bank', 'HDFC')
                account_type = trans_data.get('account_type', 'Savings Account')
                account = AccountService.get_or_create_account(
                    name=trans_data.get('account_name', f'{bank} {account_type}'),
                    bank=bank,
                    account_type=account_type
                )
                
                # Create transaction
                transaction = Transaction(
                    date=datetime.strptime(trans_data['date'], '%Y-%m-%d').date(),
                    description=trans_data['description'],
                    amount=float(trans_data['amount']),
                    category=trans_data.get('category', 'Other'),
                    subcategory=trans_data.get('subcategory'),
                    account_id=account.id,
                    is_debit=float(trans_data['amount']) < 0,
                    transaction_type='pdf_parsed',
                    notes=trans_data.get('notes')
                )
                
                # Set tags
                tags = {
                    'categories': [trans_data.get('category', 'Other')],
                    'account_type': [account_type]
                }
                transaction.set_tags(tags)
                
                db.session.add(transaction)
                saved_transactions.append(transaction)
            
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': f'Successfully saved {len(saved_transactions)} transactions',
                'transaction_count': len(saved_transactions)
            })
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500
    
    @app.route('/health')
    def health_check():
        """Health check endpoint"""
        try:
            # Test database connection
            db.session.execute('SELECT 1')
            return jsonify({
                'status': 'healthy',
                'timestamp': datetime.utcnow().isoformat(),
                'database': 'connected'
            })
        except Exception as e:
            return jsonify({
                'status': 'unhealthy',
                'timestamp': datetime.utcnow().isoformat(),
                'error': str(e)
            }), 500
    
    @app.route('/api/dashboard/summary', methods=['GET'])
    def api_dashboard_summary():
        """API endpoint for dashboard summary data"""
        try:
            summary = TransactionService.get_transactions_summary()
            return jsonify(summary)
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/charts/category-distribution', methods=['GET'])
    def api_category_distribution():
        """API endpoint for category distribution chart data"""
        try:
            # Get expense categories
            category_data = db.session.query(
                Transaction.category,
                func.sum(Transaction.amount).label('total')
            ).filter(
                Transaction.is_debit == True,
                Transaction.category.in_(EXPENSE_CATEGORIES)
            ).group_by(Transaction.category).all()
            
            return jsonify([
                {'category': category, 'amount': float(abs(amount))}
                for category, amount in category_data
            ])
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/charts/monthly-trend', methods=['GET'])
    def api_monthly_trend():
        """API endpoint for monthly income/expense trend"""
        try:
            # Get all transactions and process in Python
            transactions = Transaction.query.all()
            
            # Group by month
            monthly_data = {}
            for transaction in transactions:
                month_key = transaction.date.strftime('%Y-%m')
                if month_key not in monthly_data:
                    monthly_data[month_key] = {'income': 0, 'expenses': 0}
                
                if transaction.is_debit:
                    monthly_data[month_key]['expenses'] += abs(float(transaction.amount))
                else:
                    monthly_data[month_key]['income'] += float(transaction.amount)
            
            # Sort by month and get last 12 months
            sorted_months = sorted(monthly_data.keys())[-12:]
            
            return jsonify([
                {
                    'month': month_key,
                    'income': monthly_data[month_key]['income'],
                    'expenses': monthly_data[month_key]['expenses']
                }
                for month_key in sorted_months
            ])
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/charts/bank-distribution', methods=['GET'])
    def api_bank_distribution():
        """API endpoint for bank distribution chart"""
        try:
            # Get bank data
            bank_data = db.session.query(
                Account.bank,
                func.sum(Transaction.amount).label('total')
            ).join(Transaction).group_by(Account.bank).all()
            
            return jsonify([
                {'bank': bank, 'amount': float(amount)}
                for bank, amount in bank_data
            ])
        except Exception as e:
            return jsonify({'error': str(e)}), 500


# Create and run the app
if __name__ == '__main__':
    app = create_app()
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug)