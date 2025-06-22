from datetime import datetime

from sqlalchemy import desc

from models import Account, Category, Transaction, User, db
from models.secure_transaction import SecureTransaction, SecureTransactionError


class TransactionService:
    """
    Service layer for transaction operations using secure encrypted storage
    """
    
    def __init__(self):
        self.secure_transaction = SecureTransaction()

    @staticmethod
    def create_transaction(data):
        """Create a new transaction using secure encryption"""
        try:
            # Initialize secure transaction handler
            secure_tx = SecureTransaction()
            
            # Parse date - handle both HTML date input format (YYYY-MM-DD) and legacy format (DD/MM/YYYY)
            if isinstance(data.get("date"), str):
                date_str = data["date"]
                try:
                    # Try HTML date input format first (YYYY-MM-DD)
                    date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
                except ValueError:
                    try:
                        # Fall back to legacy format (DD/MM/YYYY)
                        date_obj = datetime.strptime(date_str, "%d/%m/%Y").date()
                    except ValueError:
                        # If both fail, use current date
                        date_obj = datetime.now().date()
            else:
                date_obj = data.get("date", datetime.now().date())

            # Prepare transaction data
            transaction_data = {
                'date': date_obj,
                'description': data["description"],
                'amount': float(data["amount"]),
                'category': data.get("category", "Miscellaneous"),
                'subcategory': data.get("subcategory"),
                'account_id': data["account_id"],
                'is_debit': data.get("is_debit", True),
                'transaction_type': data.get("transaction_type", "manual"),
                'balance': data.get("balance"),
                'reference_number': data.get("reference_number"),
                'notes': data.get("notes"),
                'tags': data.get("tags")
            }

            # Create transaction using secure method
            transaction_id = secure_tx.store_transaction_encrypted(
                transaction_data, 
                user_id=data.get('user_id')  # Pass user_id for audit logging
            )
            
            # Return the created transaction
            transaction = Transaction.query.get(transaction_id)
            return transaction
            
        except SecureTransactionError as e:
            db.session.rollback()
            raise e
        except Exception as e:
            db.session.rollback()
            raise e

    @staticmethod
    def update_transaction(transaction_id, data):
        """Update an existing transaction using secure encryption"""
        try:
            # Initialize secure transaction handler
            secure_tx = SecureTransaction()
            
            # Prepare update data
            updates = {}
            
            # Handle date update
            if "date" in data:
                if isinstance(data["date"], str):
                    date_str = data["date"]
                    try:
                        # Try HTML date input format first (YYYY-MM-DD)
                        updates['date'] = datetime.strptime(date_str, "%Y-%m-%d").date()
                    except ValueError:
                        try:
                            # Fall back to legacy format (DD/MM/YYYY)
                            updates['date'] = datetime.strptime(date_str, "%d/%m/%Y").date()
                        except ValueError:
                            # If both fail, skip date update
                            pass
                else:
                    updates['date'] = data["date"]

            # Handle basic field updates
            if "description" in data:
                updates['description'] = data["description"]
            if "amount" in data:
                updates['amount'] = float(data["amount"])
            if "subcategory" in data:
                updates['subcategory'] = data["subcategory"]
            if "account_id" in data:
                updates['account_id'] = data["account_id"]
            if "is_debit" in data:
                updates['is_debit'] = data["is_debit"]
            if "balance" in data:
                updates['balance'] = data["balance"]
            if "reference_number" in data:
                updates['reference_number'] = data["reference_number"]
            if "notes" in data:
                updates['notes'] = data["notes"]

            # Handle tags update
            if "tags" in data:
                new_tags = data["tags"]
                if isinstance(new_tags, dict):
                    updates['tags'] = new_tags
                    # Ensure category field is set from tags
                    if "categories" in new_tags and new_tags["categories"]:
                        updates['category'] = new_tags["categories"][0]
                    elif 'category' not in updates:
                        updates['category'] = "Miscellaneous"
                else:
                    updates['tags'] = {}
                    if 'category' not in updates:
                        updates['category'] = "Miscellaneous"

            # Handle individual category update
            if "category" in data:
                if data["category"]:
                    updates['category'] = data["category"]
                else:
                    updates['category'] = "Miscellaneous"

            # Ensure category is never null
            if 'category' in updates and (not updates['category'] or updates['category'].strip() == ""):
                updates['category'] = "Miscellaneous"

            # Update transaction using secure method
            success = secure_tx.update_transaction_encrypted(
                transaction_id, 
                updates, 
                user_id=data.get('user_id')  # Pass user_id for audit logging
            )
            
            if success:
                # Return the updated transaction
                transaction = Transaction.query.get(transaction_id)
                return transaction
            else:
                return None
                
        except SecureTransactionError as e:
            db.session.rollback()
            raise e
        except Exception as e:
            db.session.rollback()
            raise e

    @staticmethod
    def delete_transaction(transaction_id):
        """Delete a transaction with audit logging"""
        try:
            # For deletion, we'll use the secure transaction for audit logging
            # but still use direct database deletion
            secure_tx = SecureTransaction()
            
            transaction = Transaction.query.get(transaction_id)
            if not transaction:
                return False

            # Log the deletion attempt
            secure_tx._log_audit_action(
                action='transaction_delete_attempt',
                transaction_id=transaction_id,
                details={
                    'category': transaction.category,
                    'amount': float(transaction.amount),
                    'is_encrypted': transaction.is_encrypted
                }
            )

            db.session.delete(transaction)
            db.session.commit()
            
            # Log successful deletion
            secure_tx._log_audit_action(
                action='transaction_deleted',
                transaction_id=transaction_id,
                details={'deleted': True}
            )
            
            return True
            
        except Exception as e:
            db.session.rollback()
            # Log deletion failure
            try:
                secure_tx._log_audit_action(
                    action='transaction_delete_failed',
                    transaction_id=transaction_id,
                    success=False,
                    error_message=str(e)
                )
            except:
                pass
            raise e

    @staticmethod
    def get_transactions_summary():
        """Get summary statistics for transactions with secure access"""
        try:
            # Use secure transaction handler for getting decrypted data
            secure_tx = SecureTransaction()
            
            # Log the summary request
            secure_tx._log_audit_action(
                action='transaction_summary_request',
                details={'operation': 'get_summary_statistics'}
            )
            
            # Get all transactions using secure method (decrypted)
            all_transactions_data = secure_tx.get_transactions_decrypted(
                user_id=None,  # For now, no user authentication
                filters=None,
                limit=None,  # Get all transactions
                offset=None
            )
            
            total_transactions = len(all_transactions_data)
            total_income = 0
            total_expenses = 0

            # Calculate totals from decrypted data
            for transaction_data in all_transactions_data:
                amount = float(transaction_data.get('amount', 0))
                if transaction_data.get('is_debit', True):
                    total_expenses += abs(amount)
                else:
                    total_income += amount

            # Category summary for expenses only
            category_stats = {}
            account_stats = {}
            
            for transaction_data in all_transactions_data:
                amount = float(transaction_data.get('amount', 0))
                category = transaction_data.get('category', 'Miscellaneous')
                account_name = transaction_data.get('account_name', 'Unknown')
                account_bank = transaction_data.get('bank', 'Unknown')
                is_debit = transaction_data.get('is_debit', True)
                
                # Category stats (expenses only)
                if is_debit and category != "Income":
                    if category not in category_stats:
                        category_stats[category] = {'total': 0, 'count': 0}
                    category_stats[category]['total'] += abs(amount)
                    category_stats[category]['count'] += 1

                # Account stats
                if account_name not in account_stats:
                    account_stats[account_name] = {
                        "name": account_name, 
                        "bank": account_bank, 
                        "income": 0, 
                        "expenses": 0
                    }

                if is_debit:
                    account_stats[account_name]["expenses"] += abs(amount)
                else:
                    account_stats[account_name]["income"] += amount

            # Format category summary
            category_summary = []
            for category, stats in category_stats.items():
                category_summary.append({
                    "name": category, 
                    "total": stats['total'], 
                    "count": stats['count']
                })

            # Sort by total (highest first)
            category_summary.sort(key=lambda x: x["total"], reverse=True)

            # Format account summary
            account_summary = []
            for account_data in account_stats.values():
                account_summary.append(
                    {
                        "name": account_data["name"],
                        "bank": account_data["bank"],
                        "income": account_data["income"],
                        "expenses": account_data["expenses"],
                        "balance": account_data["income"] - account_data["expenses"],
                    }
                )

            # Format category distribution
            category_distribution = []
            for category, stats in category_stats.items():
                category_distribution.append({
                    "category": category, 
                    "total": stats['total'], 
                    "count": stats['count']
                })

            # Format account distribution
            account_distribution = []
            for account_data in account_stats.values():
                account_distribution.append({
                    "account": account_data["name"],
                    "total": account_data["expenses"],
                    "count": 1,  # Simplified count
                })

            return {
                "total_transactions": total_transactions,
                "total_income": total_income,
                "total_expenses": total_expenses,
                "net_balance": total_income - total_expenses,
                "category_summary": category_summary,
                "account_summary": account_summary,
                "category_distribution": category_distribution,
                "account_distribution": account_distribution,
            }
        except Exception as e:
            print(f"Error getting transaction summary: {e}")
            # Return default structure with zero values instead of empty dict
            return {
                "total_transactions": 0,
                "total_income": 0,
                "total_expenses": 0,
                "net_balance": 0,
                "category_summary": [],
                "account_summary": [],
                "category_distribution": [],
                "account_distribution": [],
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
                            query = query.filter(Transaction.tags.like(f'%"{tag_type}"%{tag_value}%'))

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
                    category_conditions.append(Transaction.tags.like(f'%"categories"%{category}%'))
                query = query.filter(db.or_(*category_conditions))

            # Apply account filters using tags
            if accounts:
                account_conditions = []
                for account in accounts:
                    account_conditions.append(Transaction.tags.like(f'%"accounts"%{account}%'))
                query = query.filter(db.or_(*account_conditions))

            transactions = query.all()

            # Group results
            results = {}
            for transaction in transactions:
                tags = transaction.get_tags()

                # Get categories from tags
                transaction_categories = tags.get("categories", [transaction.category] if transaction.category else [])
                transaction_accounts = tags.get("accounts", [])

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

            tag_stats = {"categories": {}, "accounts": {}}

            for transaction in transactions:
                tags = transaction.get_tags()
                amount = float(transaction.amount)

                for tag_type, tag_values in tags.items():
                    if tag_type in tag_stats:
                        for tag_value in tag_values:
                            if tag_value not in tag_stats[tag_type]:
                                tag_stats[tag_type][tag_value] = {"total": 0, "count": 0, "income": 0, "expenses": 0}

                            tag_stats[tag_type][tag_value]["total"] += amount
                            tag_stats[tag_type][tag_value]["count"] += 1

                            if transaction.is_debit:
                                tag_stats[tag_type][tag_value]["expenses"] += amount
                            else:
                                tag_stats[tag_type][tag_value]["income"] += amount

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
        income_keywords = [
            "salary",
            "interest",
            "dividend",
            "deposit",
            "credit",
            "bonus",
            "refund",
            "cashback",
            "income",
            "payment received",
            "add fund",
            "add money",
            "credit received",
            "ftd",
            "neft cr",
            "imps",
            "salary",
            "interest earned",
        ]

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
                name=data["name"],
                bank=data["bank"],
                account_type=data["account_type"],
                account_number=data.get("account_number"),
                is_active=data.get("is_active", True),
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
            default_account = AccountService.create_account(
                {"name": "Default Account", "bank": "Manual Entry", "account_type": "savings", "is_active": True}
            )
        return default_account

    @staticmethod
    def get_or_create_account(name, account_type, bank):
        """Get or create an account by name, type, and bank"""
        account = Account.query.filter_by(name=name, bank=bank).first()
        if not account:
            account = AccountService.create_account(
                {"name": name, "bank": bank, "account_type": account_type, "is_active": True}
            )
        return account


# Migration logic removed - all data should be stored only in database
