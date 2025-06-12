from models import db, Transaction, Account, Category, User
from datetime import datetime
import json
import os
from sqlalchemy import desc


class TransactionService:
    
    @staticmethod
    def create_transaction(data):
        """Create a new transaction"""
        try:
            # Parse date - handle both HTML date input format (YYYY-MM-DD) and legacy format (DD/MM/YYYY)
            if isinstance(data.get('date'), str):
                date_str = data['date']
                try:
                    # Try HTML date input format first (YYYY-MM-DD)
                    date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
                except ValueError:
                    try:
                        # Fall back to legacy format (DD/MM/YYYY)
                        date_obj = datetime.strptime(date_str, '%d/%m/%Y').date()
                    except ValueError:
                        # If both fail, use current date
                        date_obj = datetime.now().date()
            else:
                date_obj = data.get('date', datetime.now().date())
            
            transaction = Transaction(
                date=date_obj,
                description=data['description'],
                amount=float(data['amount']),
                category=data.get('category', 'Miscellaneous'),
                subcategory=data.get('subcategory'),
                account_id=data['account_id'],
                is_debit=data.get('is_debit', True),
                transaction_type=data.get('transaction_type', 'manual'),
                balance=data.get('balance'),
                reference_number=data.get('reference_number'),
                notes=data.get('notes')
            )
            
            db.session.add(transaction)
            db.session.commit()
            return transaction
        except Exception as e:
            db.session.rollback()
            raise e
    
    @staticmethod
    def update_transaction(transaction_id, data):
        """Update an existing transaction"""
        try:
            transaction = Transaction.query.get(transaction_id)
            if not transaction:
                return None
            
            # Update basic fields
            if 'date' in data:
                if isinstance(data['date'], str):
                    date_str = data['date']
                    try:
                        # Try HTML date input format first (YYYY-MM-DD)
                        transaction.date = datetime.strptime(date_str, '%Y-%m-%d').date()
                    except ValueError:
                        try:
                            # Fall back to legacy format (DD/MM/YYYY)
                            transaction.date = datetime.strptime(date_str, '%d/%m/%Y').date()
                        except ValueError:
                            # If both fail, keep current date
                            pass
                else:
                    transaction.date = data['date']
            
            if 'description' in data:
                transaction.description = data['description']
            if 'amount' in data:
                transaction.amount = float(data['amount'])
            if 'subcategory' in data:
                transaction.subcategory = data['subcategory']
            if 'account_id' in data:
                transaction.account_id = data['account_id']
            if 'is_debit' in data:
                transaction.is_debit = data['is_debit']
            if 'balance' in data:
                transaction.balance = data['balance']
            if 'reference_number' in data:
                transaction.reference_number = data['reference_number']
            if 'notes' in data:
                transaction.notes = data['notes']
            
            # Handle structured tags update - this is the key part
            if 'tags' in data:
                # Use the tags directly from the frontend
                new_tags = data['tags']
                if isinstance(new_tags, dict):
                    transaction.set_tags(new_tags)
                    
                    # Ensure category field is set from tags (for database constraint)
                    if 'categories' in new_tags and new_tags['categories']:
                        transaction.category = new_tags['categories'][0]
                    else:
                        # If no categories in tags, keep current category or set default
                        if not transaction.category:
                            transaction.category = 'Miscellaneous'
                else:
                    # If tags is empty or invalid, set default category
                    transaction.set_tags({})
                    if not transaction.category:
                        transaction.category = 'Miscellaneous'
            
            # Handle individual category update (legacy support)
            if 'category' in data:
                if data['category']:
                    transaction.category = data['category']
                    # Also update tags for consistency
                    current_tags = transaction.get_tags()
                    if 'categories' not in current_tags:
                        current_tags['categories'] = []
                    if data['category'] not in current_tags['categories']:
                        current_tags['categories'] = [data['category']]  # Replace, don't append
                    transaction.set_tags(current_tags)
                else:
                    # If trying to set category to null, use default
                    transaction.category = 'Miscellaneous'
            
            # Handle legacy fields for backward compatibility
            if 'account_name' in data and data['account_name']:
                current_tags = transaction.get_tags()
                if 'accounts' not in current_tags:
                    current_tags['accounts'] = []
                if data['account_name'] not in current_tags['accounts']:
                    current_tags['accounts'] = [data['account_name']]
                transaction.set_tags(current_tags)
            
            # Ensure category is never null (database constraint)
            if not transaction.category or transaction.category.strip() == '':
                transaction.category = 'Miscellaneous'
            
            transaction.updated_at = datetime.utcnow()
            db.session.commit()
            return transaction
        except Exception as e:
            db.session.rollback()
            raise e
    
    @staticmethod
    def delete_transaction(transaction_id):
        """Delete a transaction"""
        try:
            transaction = Transaction.query.get(transaction_id)
            if not transaction:
                return False
            
            db.session.delete(transaction)
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            raise e
    
    @staticmethod
    def get_transactions_summary():
        """Get summary statistics for transactions"""
        try:
            total_transactions = Transaction.query.count()
            
            # Calculate totals manually
            all_transactions = Transaction.query.all()
            total_income = 0
            total_expenses = 0
            
            for transaction in all_transactions:
                if transaction.is_debit:
                    total_expenses += abs(float(transaction.amount))
                else:
                    total_income += float(transaction.amount)
            
            # Category summary for expenses only
            category_stats = db.session.query(
                Transaction.category,
                db.func.sum(Transaction.amount).label('total'),
                db.func.count(Transaction.id).label('count')
            ).filter(
                Transaction.is_debit == True,
                Transaction.category != 'Income'
            ).group_by(Transaction.category).all()
            
            # Account summary with income/expense breakdown - calculate manually
            account_stats = {}
            for transaction in all_transactions:
                account_name = transaction.account.name if transaction.account else 'Unknown'
                account_bank = transaction.account.bank if transaction.account else 'Unknown'
                
                if account_name not in account_stats:
                    account_stats[account_name] = {
                        'name': account_name,
                        'bank': account_bank,
                        'income': 0,
                        'expenses': 0
                    }
                
                if transaction.is_debit:
                    account_stats[account_name]['expenses'] += abs(float(transaction.amount))
                else:
                    account_stats[account_name]['income'] += float(transaction.amount)
            
            # Format category summary
            category_summary = []
            for category, total, count in category_stats:
                category_summary.append({
                    'name': category,
                    'total': float(abs(total)),
                    'count': count
                })
            
            # Sort by total (highest first)
            category_summary.sort(key=lambda x: x['total'], reverse=True)
            
            # Format account summary
            account_summary = []
            for account_data in account_stats.values():
                account_summary.append({
                    'name': account_data['name'],
                    'bank': account_data['bank'],
                    'income': account_data['income'],
                    'expenses': account_data['expenses'],
                    'balance': account_data['income'] - account_data['expenses']
                })
            
            return {
                'total_transactions': total_transactions,
                'total_income': total_income,
                'total_expenses': total_expenses,
                'net_balance': total_income - total_expenses,
                'category_summary': category_summary,
                'account_summary': account_summary,
                'category_distribution': [
                    {'category': cat, 'total': float(total), 'count': count}
                    for cat, total, count in category_stats
                ],
                'account_distribution': [
                    {
                        'account': acc_data['name'], 
                        'total': acc_data['expenses'], 
                        'count': 1  # We don't have count per account in our current structure
                    }
                    for acc_data in account_stats.values()
                ]
            }
        except Exception as e:
            print(f"Error getting transaction summary: {e}")
            # Return default structure with zero values instead of empty dict
            return {
                'total_transactions': 0,
                'total_income': 0,
                'total_expenses': 0,
                'net_balance': 0,
                'category_summary': [],
                'account_summary': [],
                'category_distribution': [],
                'account_distribution': []
            }
    
    @staticmethod
    def get_transactions_by_tags(tag_filters=None, date_from=None, date_to=None):
        """Get transactions filtered by tags"""
        try:
            query = Transaction.query
            
            # Apply date filters
            if date_from:
                query = query.filter(Transaction.date >= date_from)
            if date_to:
                query = query.filter(Transaction.date <= date_to)
            
            # Apply tag filters
            if tag_filters:
                for tag_type, tag_values in tag_filters.items():
                    if tag_values:
                        # Use JSON operations to filter by tags
                        for tag_value in tag_values:
                            query = query.filter(
                                Transaction.tags.like(f'%"{tag_type}"%{tag_value}%')
                            )
            
            return query.order_by(desc(Transaction.date)).all()
        except Exception as e:
            print(f"Error getting transactions by tags: {e}")
            return []
    
    @staticmethod
    def get_spending_by_category_and_account(categories=None, accounts=None, date_from=None, date_to=None):
        """Get spending analysis by category and account combinations"""
        try:
            query = Transaction.query.filter(Transaction.is_debit == True)
            
            # Apply date filters
            if date_from:
                query = query.filter(Transaction.date >= date_from)
            if date_to:
                query = query.filter(Transaction.date <= date_to)
            
            # Apply category filters using tags
            if categories:
                category_conditions = []
                for category in categories:
                    category_conditions.append(
                        Transaction.tags.like(f'%"categories"%{category}%')
                    )
                query = query.filter(db.or_(*category_conditions))
            
            # Apply account filters using tags
            if accounts:
                account_conditions = []
                for account in accounts:
                    account_conditions.append(
                        Transaction.tags.like(f'%"accounts"%{account}%')
                    )
                query = query.filter(db.or_(*account_conditions))
            
            transactions = query.all()
            
            # Group results
            results = {}
            for transaction in transactions:
                tags = transaction.get_tags()
                
                # Get categories from tags
                transaction_categories = tags.get('categories', [transaction.category] if transaction.category else [])
                transaction_accounts = tags.get('accounts', [])
                
                for category in transaction_categories:
                    if category not in results:
                        results[category] = {}
                    
                    for account in transaction_accounts:
                        if account not in results[category]:
                            results[category][account] = 0
                        results[category][account] += float(transaction.amount)
            
            return results
        except Exception as e:
            print(f"Error getting spending analysis: {e}")
            return {}
    
    @staticmethod
    def get_tag_analytics():
        """Get analytics based on tags"""
        try:
            transactions = Transaction.query.all()
            
            tag_stats = {
                'categories': {},
                'accounts': {}
            }
            
            for transaction in transactions:
                tags = transaction.get_tags()
                amount = float(transaction.amount)
                
                for tag_type, tag_values in tags.items():
                    if tag_type in tag_stats:
                        for tag_value in tag_values:
                            if tag_value not in tag_stats[tag_type]:
                                tag_stats[tag_type][tag_value] = {
                                    'total': 0,
                                    'count': 0,
                                    'income': 0,
                                    'expenses': 0
                                }
                            
                            tag_stats[tag_type][tag_value]['total'] += amount
                            tag_stats[tag_type][tag_value]['count'] += 1
                            
                            if transaction.is_debit:
                                tag_stats[tag_type][tag_value]['expenses'] += amount
                            else:
                                tag_stats[tag_type][tag_value]['income'] += amount
            
            return tag_stats
        except Exception as e:
            print(f"Error getting tag analytics: {e}")
            return {}


class CategoryService:
    
    @staticmethod
    def categorize_transaction(description, amount=None, is_debit=None):
        """Categorize a transaction based on its description and amount"""
        description = description.lower() if description else ""
        
        # If it's a credit (positive amount), categorize as income
        if amount is not None and amount > 0 and not is_debit:
            return "Income"
        
        # Check for income-related transaction based on common keywords
        income_keywords = ["salary", "interest", "dividend", "deposit", "credit", "bonus", 
                         "refund", "cashback", "income", "payment received", "add fund", 
                         "add money", "credit received", "ftd", "neft cr", "imps", "salary", 
                         "interest earned"]
        
        for keyword in income_keywords:
            if keyword in description:
                return "Income"
        
        # Rule-based categorization using database categories
        categories = Category.query.filter_by(is_active=True).all()
        for category in categories:
            keywords = category.get_keywords()
            for keyword in keywords:
                if keyword.lower() in description:
                    return category.name
        
        return "Miscellaneous"
    
    @staticmethod
    def categorize_subcategory(description, category):
        """Determine the subcategory based on description and main category"""
        description = description.lower()
        
        # Get category from database
        category_obj = Category.query.filter_by(name=category, is_active=True).first()
        if not category_obj:
            return ""
        
        # Rule-based subcategory assignment
        subcategories = category_obj.get_subcategories()
        for subcategory, keywords in subcategories.items():
            for keyword in keywords:
                if keyword.lower() in description:
                    return subcategory
        
        return ""


class AccountService:
    
    @staticmethod
    def create_account(data):
        """Create a new account"""
        try:
            account = Account(
                name=data['name'],
                bank=data['bank'],
                account_type=data['account_type'],
                account_number=data.get('account_number'),
                is_active=data.get('is_active', True)
            )
            
            db.session.add(account)
            db.session.commit()
            return account
        except Exception as e:
            db.session.rollback()
            raise e
    
    @staticmethod
    def get_or_create_default_account():
        """Get or create a default account for manual transactions"""
        default_account = Account.query.filter_by(name="Default Account").first()
        if not default_account:
            default_account = AccountService.create_account({
                'name': 'Default Account',
                'bank': 'Manual Entry',
                'account_type': 'savings',
                'is_active': True
            })
        return default_account
    
    @staticmethod
    def get_or_create_account(name, account_type, bank):
        """Get or create an account by name, type, and bank"""
        account = Account.query.filter_by(name=name, bank=bank).first()
        if not account:
            account = AccountService.create_account({
                'name': name,
                'bank': bank,
                'account_type': account_type,
                'is_active': True
            })
        return account


class DataMigrationService:
    
    @staticmethod
    def migrate_from_json():
        """Migrate existing JSON data to database"""
        print("Starting data migration from JSON files...")
        
        # Migrate categories
        DataMigrationService._migrate_categories()
        
        # Migrate accounts
        DataMigrationService._migrate_accounts()
        
        # Migrate transactions
        DataMigrationService._migrate_transactions()
        
        print("Data migration completed successfully!")
    
    @staticmethod
    def _migrate_categories():
        """Migrate categories from JSON"""
        categories_file = 'data/categories.json'
        if not os.path.exists(categories_file):
            return
        
        try:
            with open(categories_file, 'r') as f:
                categories_data = json.load(f)
            
            for category_name, category_info in categories_data.items():
                existing_category = Category.query.filter_by(name=category_name).first()
                if not existing_category:
                    category = Category(
                        name=category_name,
                        is_active=True
                    )
                    category.set_keywords(category_info.get('keywords', []))
                    category.set_subcategories(category_info.get('subcategories', {}))
                    
                    db.session.add(category)
            
            db.session.commit()
            print(f"Migrated {len(categories_data)} categories")
        except Exception as e:
            db.session.rollback()
            print(f"Error migrating categories: {e}")
    
    @staticmethod
    def _migrate_accounts():
        """Migrate accounts from JSON"""
        account_config_file = 'data/account_config.json'
        if not os.path.exists(account_config_file):
            # Create default account
            AccountService.get_or_create_default_account()
            return
        
        try:
            with open(account_config_file, 'r') as f:
                account_data = json.load(f)
            
            accounts = account_data.get('accounts', [])
            for account_info in accounts:
                existing_account = Account.query.filter_by(
                    name=account_info.get('account_name', 'Unknown')
                ).first()
                
                if not existing_account:
                    account = Account(
                        name=account_info.get('account_name', 'Unknown'),
                        bank=account_info.get('bank', 'Unknown'),
                        account_type=account_info.get('account_type', 'savings'),
                        is_active=True
                    )
                    db.session.add(account)
            
            # Ensure default account exists
            AccountService.get_or_create_default_account()
            
            db.session.commit()
            print(f"Migrated {len(accounts)} accounts")
        except Exception as e:
            db.session.rollback()
            print(f"Error migrating accounts: {e}")
    
    @staticmethod
    def _migrate_transactions():
        """Migrate transactions from JSON"""
        transactions_file = 'data/transactions.json'
        if not os.path.exists(transactions_file):
            return
        
        try:
            with open(transactions_file, 'r') as f:
                transactions_data = json.load(f)
            
            default_account = AccountService.get_or_create_default_account()
            
            for transaction_data in transactions_data:
                # Skip if transaction already exists (based on description, amount, date)
                existing_transaction = Transaction.query.filter_by(
                    description=transaction_data.get('description', ''),
                    amount=float(transaction_data.get('amount', 0)),
                    date=datetime.strptime(transaction_data.get('date'), '%d/%m/%Y').date()
                ).first()
                
                if existing_transaction:
                    continue
                
                # Find or use default account
                account = Account.query.filter_by(
                    name=transaction_data.get('account_name', 'Default Account')
                ).first() or default_account
                
                transaction = Transaction(
                    date=datetime.strptime(transaction_data.get('date'), '%d/%m/%Y').date(),
                    description=transaction_data.get('description', ''),
                    amount=float(transaction_data.get('amount', 0)),
                    category=transaction_data.get('category', 'Miscellaneous'),
                    subcategory=transaction_data.get('subcategory'),
                    account_id=account.id,
                    is_debit=transaction_data.get('is_debit', True),
                    transaction_type='pdf_parsed',
                    balance=transaction_data.get('balance'),
                    reference_number=transaction_data.get('transaction_id')
                )
                
                db.session.add(transaction)
            
            db.session.commit()
            print(f"Migrated {len(transactions_data)} transactions")
        except Exception as e:
            db.session.rollback()
            print(f"Error migrating transactions: {e}") 