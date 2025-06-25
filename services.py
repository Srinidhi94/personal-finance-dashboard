import uuid
import random
import string
import os
import io
import csv
import json
from datetime import datetime
from typing import List, Optional, Dict, Any

try:
    import pandas as pd
except ImportError:
    pd = None

try:
    import PyPDF2
except ImportError:
    PyPDF2 = None

try:
    from flask import request, current_app
except ImportError:
    # Handle case where Flask is not available (e.g., during testing)
    request = None
    current_app = None

try:
    from werkzeug.utils import secure_filename
except ImportError:
    def secure_filename(filename):
        return filename

from sqlalchemy import desc

from models import Account, Category, Transaction, User, db, AuditLog
from models.secure_transaction import SecureTransaction, SecureTransactionError
from llm_services.llm_service import LLMService, LLMServiceError


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


class TraceIDService:
    """
    Service for generating and validating trace IDs for tracking operations
    """
    
    @staticmethod
    def generate_trace_id() -> str:
        """
        Generate a unique trace ID in format: trace_YYYY_MM_DD_randomstring
        
        Returns:
            str: Generated trace ID
        """
        try:
            # Get current date
            current_date = datetime.now()
            date_str = current_date.strftime("%Y_%m_%d")
            
            # Generate random string (8 characters)
            random_string = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
            
            # Combine into trace ID
            trace_id = f"trace_{date_str}_{random_string}"
            
            print(f"Generated trace ID: {trace_id}")
            return trace_id
            
        except Exception as e:
            print(f"Error generating trace ID: {e}")
            # Fallback to UUID-based trace ID
            fallback_id = f"trace_{str(uuid.uuid4())[:8]}"
            print(f"Using fallback trace ID: {fallback_id}")
            return fallback_id
    
    @staticmethod
    def validate_trace_id(trace_id: str) -> bool:
        """
        Validate if a trace ID follows the expected format
        
        Args:
            trace_id: The trace ID to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        try:
            if not trace_id or not isinstance(trace_id, str):
                return False
            
            # Check if it starts with 'trace_'
            if not trace_id.startswith('trace_'):
                return False
            
            # Split by underscores
            parts = trace_id.split('_')
            
            # Should have at least 4 parts: trace, YYYY, MM, DD, randomstring
            if len(parts) < 5:
                return False
            
            # Check if the date parts are valid
            try:
                year = int(parts[1])
                month = int(parts[2])
                day = int(parts[3])
                
                # Basic date validation
                if not (2020 <= year <= 2050):  # Reasonable year range
                    return False
                if not (1 <= month <= 12):
                    return False
                if not (1 <= day <= 31):
                    return False
                
                # Try to create a datetime to validate the date
                datetime(year, month, day)
                
            except (ValueError, TypeError):
                return False
            
            # Check if random string exists and is reasonable length
            random_part = '_'.join(parts[4:])  # In case there are more underscores
            if not random_part or len(random_part) < 3:
                return False
            
            return True
            
        except Exception as e:
            print(f"Error validating trace ID {trace_id}: {e}")
            return False


class AuditService:
    """
    Service for audit logging and trail management
    """
    
    @staticmethod
    def log_action(trace_id: str, user_id: Optional[str], action: str, 
                   entity_type: Optional[str] = None, entity_id: Optional[str] = None, 
                   metadata: Optional[Dict[str, Any]] = None, request_obj=None) -> Optional[AuditLog]:
        """
        Log an audit action with comprehensive details
        
        Args:
            trace_id: Trace ID for tracking related operations
            user_id: ID of the user performing the action
            action: Action being performed (e.g., 'upload_start', 'extraction_complete')
            entity_type: Type of entity being acted upon (e.g., 'transaction', 'account')
            entity_id: ID of the entity being acted upon
            metadata: Additional metadata as a dictionary
            request_obj: Flask request object (defaults to current request)
            
        Returns:
            AuditLog: Created audit log entry or None if failed
        """
        try:
            # Validate trace ID
            if not TraceIDService.validate_trace_id(trace_id):
                print(f"Warning: Invalid trace ID provided: {trace_id}")
                # Don't fail the operation, but log the warning
            
            # Get request information
            ip_address = None
            user_agent = None
            
            if request_obj is None:
                try:
                    # Only try to use request if it was imported successfully
                    if request is not None:
                        request_obj = request
                except (RuntimeError, NameError):
                    # Outside request context or request not available
                    pass
            
            try:
                # Only try to use request if it was imported successfully
                if request is not None and request:
                    ip_address = request.remote_addr
                    user_agent = request.headers.get('User-Agent')
            except (RuntimeError, AttributeError):
                # Outside request context or request not available
                pass
            
            # Create audit log entry
            audit_log = AuditLog.log_action(
                action=action,
                user_id=user_id,
                trace_id=trace_id,
                entity_type=entity_type,
                entity_id=entity_id,
                metadata=metadata,
                ip_address=ip_address,
                user_agent=user_agent,
                success=True
            )
            
            if audit_log:
                try:
                    db.session.commit()
                    print(f"Audit log created: {action} for trace_id {trace_id}")
                    return audit_log
                except Exception as e:
                    db.session.rollback()
                    print(f"Failed to commit audit log: {e}")
                    return None
            else:
                print(f"Failed to create audit log for action: {action}")
                return None
                
        except Exception as e:
            print(f"Error logging audit action {action}: {e}")
            try:
                db.session.rollback()
            except:
                pass
            return None
    
    @staticmethod
    def log_error(trace_id: str, user_id: Optional[str], action: str, 
                  error_message: str, entity_type: Optional[str] = None, 
                  entity_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> Optional[AuditLog]:
        """
        Log an audit action that resulted in an error
        
        Args:
            trace_id: Trace ID for tracking related operations
            user_id: ID of the user performing the action
            action: Action that failed
            error_message: Error message describing the failure
            entity_type: Type of entity being acted upon
            entity_id: ID of the entity being acted upon
            metadata: Additional metadata as a dictionary
            
        Returns:
            AuditLog: Created audit log entry or None if failed
        """
        try:
            # Get request information
            ip_address = None
            user_agent = None
            
            try:
                if request:
                    ip_address = request.remote_addr
                    user_agent = request.headers.get('User-Agent')
            except RuntimeError:
                # Outside request context
                pass
            
            # Create audit log entry for error
            audit_log = AuditLog.log_action(
                action=action,
                user_id=user_id,
                trace_id=trace_id,
                entity_type=entity_type,
                entity_id=entity_id,
                metadata=metadata,
                ip_address=ip_address,
                user_agent=user_agent,
                success=False,
                error_message=error_message
            )
            
            if audit_log:
                try:
                    db.session.commit()
                    print(f"Audit error logged: {action} failed for trace_id {trace_id}: {error_message}")
                    return audit_log
                except Exception as e:
                    db.session.rollback()
                    print(f"Failed to commit audit error log: {e}")
                    return None
            else:
                print(f"Failed to create audit error log for action: {action}")
                return None
                
        except Exception as e:
            print(f"Error logging audit error for action {action}: {e}")
            try:
                db.session.rollback()
            except:
                pass
            return None
    
    @staticmethod
    def get_audit_trail(trace_id: str) -> List[AuditLog]:
        """
        Get all audit log entries for a specific trace ID
        
        Args:
            trace_id: Trace ID to search for
            
        Returns:
            List[AuditLog]: List of audit log entries ordered by timestamp
        """
        try:
            audit_logs = AuditLog.query.filter_by(trace_id=trace_id).order_by(AuditLog.created_at.asc()).all()
            
            print(f"Retrieved {len(audit_logs)} audit log entries for trace_id {trace_id}")
            return audit_logs
            
        except Exception as e:
            print(f"Error retrieving audit trail for trace_id {trace_id}: {e}")
            return []
    
    @staticmethod
    def get_user_audit_logs(user_id: str, limit: int = 100) -> List[AuditLog]:
        """
        Get audit log entries for a specific user
        
        Args:
            user_id: User ID to search for
            limit: Maximum number of entries to return (default: 100)
            
        Returns:
            List[AuditLog]: List of audit log entries ordered by timestamp (newest first)
        """
        try:
            audit_logs = (AuditLog.query
                         .filter_by(user_id=user_id)
                         .order_by(AuditLog.created_at.desc())
                         .limit(limit)
                         .all())
            
            print(f"Retrieved {len(audit_logs)} audit log entries for user {user_id}")
            return audit_logs
            
        except Exception as e:
            print(f"Error retrieving audit logs for user {user_id}: {e}")
            return []
    
    @staticmethod
    def get_audit_summary(trace_id: str) -> Dict[str, Any]:
        """
        Get a summary of audit activities for a trace ID
        
        Args:
            trace_id: Trace ID to summarize
            
        Returns:
            Dict containing summary information
        """
        try:
            audit_logs = AuditService.get_audit_trail(trace_id)
            
            if not audit_logs:
                return {
                    'trace_id': trace_id,
                    'total_actions': 0,
                    'successful_actions': 0,
                    'failed_actions': 0,
                    'start_time': None,
                    'end_time': None,
                    'duration_seconds': None,
                    'actions': [],
                    'entities': []
                }
            
            # Calculate summary statistics
            total_actions = len(audit_logs)
            successful_actions = sum(1 for log in audit_logs if log.success)
            failed_actions = total_actions - successful_actions
            
            start_time = audit_logs[0].created_at
            end_time = audit_logs[-1].created_at
            duration_seconds = (end_time - start_time).total_seconds() if start_time and end_time else 0
            
            # Get unique actions and entities
            actions = list(set(log.action for log in audit_logs))
            entities = list(set(f"{log.entity_type}:{log.entity_id}" for log in audit_logs 
                              if log.entity_type and log.entity_id))
            
            summary = {
                'trace_id': trace_id,
                'total_actions': total_actions,
                'successful_actions': successful_actions,
                'failed_actions': failed_actions,
                'start_time': start_time.isoformat() if start_time else None,
                'end_time': end_time.isoformat() if end_time else None,
                'duration_seconds': duration_seconds,
                'actions': actions,
                'entities': entities
            }
            
            print(f"Generated audit summary for trace_id {trace_id}")
            return summary
            
        except Exception as e:
            print(f"Error generating audit summary for trace_id {trace_id}: {e}")
            return {
                'trace_id': trace_id,
                'error': str(e),
                'total_actions': 0,
                'successful_actions': 0,
                'failed_actions': 0
            }

class DocumentProcessingService:
    """
    Service for orchestrating the complete file-to-transactions pipeline.
    Handles file validation, content extraction, LLM processing, and transaction normalization.
    """
    
    # Supported file types and their MIME types
    SUPPORTED_FILE_TYPES = {
        'pdf': ['application/pdf'],
        'csv': ['text/csv', 'application/csv'],
        'xlsx': ['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'],
        'xls': ['application/vnd.ms-excel'],
        'txt': ['text/plain']
    }
    
    # Maximum file sizes (in bytes)
    MAX_FILE_SIZES = {
        'pdf': 32 * 1024 * 1024,  # 32MB
        'csv': 10 * 1024 * 1024,  # 10MB
        'xlsx': 25 * 1024 * 1024,  # 25MB
        'xls': 25 * 1024 * 1024,   # 25MB
        'txt': 5 * 1024 * 1024     # 5MB
    }
    
    def __init__(self):
        """Initialize the document processing service with required dependencies."""
        self.llm_service = LLMService()
        self.trace_service = TraceIDService()
        self.audit_service = AuditService()
        self.transaction_service = TransactionService()
    
    def process_uploaded_file(self, file, user_id: str, account_id: str, bank_type: str = "unknown") -> dict:
        """
        Process an uploaded file through the complete pipeline.
        
        Args:
            file: File object from Flask request
            user_id: ID of the user uploading the file
            account_id: ID of the target account
            bank_type: Type of bank (for specialized parsing)
            
        Returns:
            dict: Processing results with transaction data and metadata
            
        Raises:
            Exception: If processing fails at any stage
        """
        # Generate trace ID for this processing session
        trace_id = self.trace_service.generate_trace_id()
        
        try:
            # Log the start of processing
            self.audit_service.log_action(
                trace_id=trace_id,
                user_id=user_id,
                action="file_processing_started",
                entity_type="file_upload",
                metadata={
                    "filename": file.filename,
                    "bank_type": bank_type,
                    "account_id": account_id,
                    "file_size": self._get_file_size(file)
                }
            )
            
            # Step 1: Validate file
            validation_result = self.validate_file(file)
            if not validation_result['is_valid']:
                self.audit_service.log_error(
                    trace_id=trace_id,
                    user_id=user_id,
                    action="file_validation_failed",
                    error_message="; ".join(validation_result['errors']),
                    metadata={"filename": file.filename}
                )
                return {
                    "success": False,
                    "trace_id": trace_id,
                    "error": "File validation failed",
                    "details": validation_result['errors']
                }
            
            # Step 2: Extract content from file
            try:
                file_content = self._extract_file_content(file, validation_result['file_type'])
                self.audit_service.log_action(
                    trace_id=trace_id,
                    user_id=user_id,
                    action="file_content_extracted",
                    metadata={
                        "content_length": len(str(file_content)),
                        "file_type": validation_result['file_type']
                    }
                )
            except Exception as e:
                self.audit_service.log_error(
                    trace_id=trace_id,
                    user_id=user_id,
                    action="file_content_extraction_failed",
                    error_message=str(e),
                    metadata={"filename": file.filename}
                )
                return {
                    "success": False,
                    "trace_id": trace_id,
                    "error": "Failed to extract file content",
                    "details": [str(e)]
                }
            
            # Step 3: Process with LLM
            try:
                if validation_result['file_type'] == 'pdf':
                    # For PDFs, use bank statement parsing
                    llm_response = self.llm_service.parse_bank_statement(file_content, bank_type)
                else:
                    # For CSV/Excel, process structured data
                    llm_response = self._process_structured_data(file_content, bank_type)
                
                self.audit_service.log_action(
                    trace_id=trace_id,
                    user_id=user_id,
                    action="llm_processing_completed",
                    metadata={
                        "transactions_found": len(llm_response) if isinstance(llm_response, list) else 0,
                        "processing_method": "bank_statement" if validation_result['file_type'] == 'pdf' else "structured_data"
                    }
                )
            except LLMServiceError as e:
                self.audit_service.log_error(
                    trace_id=trace_id,
                    user_id=user_id,
                    action="llm_processing_failed",
                    error_message=str(e),
                    metadata={"bank_type": bank_type}
                )
                return {
                    "success": False,
                    "trace_id": trace_id,
                    "error": "LLM processing failed",
                    "details": [str(e)]
                }
            
            # Step 4: Normalize and validate LLM response
            try:
                normalized_transactions = self.normalize_llm_response(llm_response, user_id, account_id, trace_id)
                self.audit_service.log_action(
                    trace_id=trace_id,
                    user_id=user_id,
                    action="transaction_normalization_completed",
                    metadata={
                        "normalized_transactions": len(normalized_transactions),
                        "validation_passed": True
                    }
                )
            except Exception as e:
                self.audit_service.log_error(
                    trace_id=trace_id,
                    user_id=user_id,
                    action="transaction_normalization_failed",
                    error_message=str(e)
                )
                return {
                    "success": False,
                    "trace_id": trace_id,
                    "error": "Transaction normalization failed",
                    "details": [str(e)]
                }
            
            # Step 5: Return successful result
            self.audit_service.log_action(
                trace_id=trace_id,
                user_id=user_id,
                action="file_processing_completed",
                metadata={
                    "total_transactions": len(normalized_transactions),
                    "processing_time_ms": None,  # Could add timing if needed
                    "success": True
                }
            )
            
            return {
                "success": True,
                "trace_id": trace_id,
                "transactions": normalized_transactions,
                "metadata": {
                    "filename": file.filename,
                    "file_type": validation_result['file_type'],
                    "bank_type": bank_type,
                    "total_transactions": len(normalized_transactions),
                    "account_id": account_id
                }
            }
            
        except Exception as e:
            # Catch-all error handling
            self.audit_service.log_error(
                trace_id=trace_id,
                user_id=user_id,
                action="file_processing_unexpected_error",
                error_message=str(e),
                metadata={"filename": getattr(file, 'filename', 'unknown')}
            )
            return {
                "success": False,
                "trace_id": trace_id,
                "error": "Unexpected processing error",
                "details": [str(e)]
            }
    
    def validate_file(self, file) -> dict:
        """
        Validate uploaded file for type, size, and basic content checks.
        
        Args:
            file: File object from Flask request
            
        Returns:
            dict: Validation result with is_valid flag, file_type, and error details
        """
        errors = []
        file_type = None
        
        try:
            # Check if file exists
            if not file or not file.filename:
                errors.append("No file provided")
                return {"is_valid": False, "errors": errors, "file_type": None}
            
            # Get file extension
            filename = secure_filename(file.filename)
            if '.' not in filename:
                errors.append("File has no extension")
                return {"is_valid": False, "errors": errors, "file_type": None}
            
            file_ext = filename.rsplit('.', 1)[1].lower()
            
            # Check if extension is supported
            if file_ext not in self.SUPPORTED_FILE_TYPES:
                errors.append(f"Unsupported file type: {file_ext}")
                return {"is_valid": False, "errors": errors, "file_type": file_ext}
            
            file_type = file_ext
            
            # Check file size
            file_size = self._get_file_size(file)
            max_size = self.MAX_FILE_SIZES.get(file_ext, 16 * 1024 * 1024)  # Default 16MB
            
            if file_size > max_size:
                errors.append(f"File size ({file_size / (1024*1024):.1f}MB) exceeds maximum allowed size ({max_size / (1024*1024):.1f}MB)")
            
            # Check MIME type if available
            if hasattr(file, 'content_type') and file.content_type:
                expected_mime_types = self.SUPPORTED_FILE_TYPES[file_ext]
                if file.content_type not in expected_mime_types:
                    errors.append(f"MIME type mismatch: expected {expected_mime_types}, got {file.content_type}")
            
            # Basic content validation
            try:
                file.seek(0)  # Reset file pointer
                first_bytes = file.read(1024)  # Read first 1KB
                file.seek(0)  # Reset again
                
                if not first_bytes:
                    errors.append("File appears to be empty")
                elif file_ext == 'pdf' and not first_bytes.startswith(b'%PDF'):
                    errors.append("File does not appear to be a valid PDF")
                elif file_ext == 'csv' and len(first_bytes.decode('utf-8', errors='ignore').strip()) == 0:
                    errors.append("CSV file appears to be empty")
                    
            except Exception as e:
                errors.append(f"Could not read file content: {str(e)}")
            
            return {
                "is_valid": len(errors) == 0,
                "errors": errors,
                "file_type": file_type,
                "file_size": file_size
            }
            
        except Exception as e:
            errors.append(f"Validation error: {str(e)}")
            return {"is_valid": False, "errors": errors, "file_type": file_type}
    
    def normalize_llm_response(self, llm_response: dict, user_id: str, account_id: str, trace_id: str = None) -> List[dict]:
        """
        Convert LLM output to standardized transaction format with business logic validation.
        
        Args:
            llm_response: Raw response from LLM service
            user_id: ID of the user for audit logging
            account_id: ID of the target account
            trace_id: Optional trace ID for audit logging
            
        Returns:
            List[dict]: Normalized transaction data ready for encryption pipeline
            
        Raises:
            ValueError: If LLM response cannot be normalized
        """
        if not trace_id:
            trace_id = self.trace_service.generate_trace_id()
        
        try:
            # Ensure llm_response is a list
            if not isinstance(llm_response, list):
                raise ValueError("LLM response must be a list of transactions")
            
            normalized_transactions = []
            
            for i, raw_transaction in enumerate(llm_response):
                try:
                    # Validate required fields
                    if not isinstance(raw_transaction, dict):
                        self.audit_service.log_error(
                            trace_id=trace_id,
                            user_id=user_id,
                            action="transaction_normalization_invalid_format",
                            error_message=f"Transaction {i} is not a dictionary",
                            metadata={"transaction_index": i}
                        )
                        continue
                    
                    # Extract and validate core fields
                    normalized = self._normalize_single_transaction(raw_transaction, account_id, i)
                    
                    # Add metadata fields
                    normalized.update({
                        'user_id': user_id,
                        'trace_id': trace_id,
                        'source': 'file_upload',
                        'processing_metadata': {
                            'original_data': raw_transaction,
                            'normalized_at': datetime.now().isoformat(),
                            'normalization_version': '1.0'
                        }
                    })
                    
                    normalized_transactions.append(normalized)
                    
                except Exception as e:
                    self.audit_service.log_error(
                        trace_id=trace_id,
                        user_id=user_id,
                        action="single_transaction_normalization_failed",
                        error_message=str(e),
                        metadata={
                            "transaction_index": i,
                            "raw_transaction": raw_transaction
                        }
                    )
                    # Continue processing other transactions
                    continue
            
            if not normalized_transactions:
                raise ValueError("No valid transactions could be normalized from LLM response")
            
            # Apply business logic validation
            validated_transactions = self._apply_business_logic_validation(normalized_transactions, trace_id, user_id)
            
            return validated_transactions
            
        except Exception as e:
            self.audit_service.log_error(
                trace_id=trace_id,
                user_id=user_id,
                action="llm_response_normalization_failed",
                error_message=str(e),
                metadata={"response_type": type(llm_response).__name__}
            )
            raise ValueError(f"Failed to normalize LLM response: {str(e)}")
    
    def _normalize_single_transaction(self, raw_transaction: dict, account_id: str, index: int) -> dict:
        """Normalize a single transaction from LLM response."""
        # Required fields with validation
        required_fields = ['date', 'description', 'amount']
        for field in required_fields:
            if field not in raw_transaction:
                raise ValueError(f"Missing required field '{field}' in transaction {index}")
        
        # Parse and validate date
        date_str = raw_transaction['date']
        try:
            if isinstance(date_str, str):
                # Try multiple date formats
                for date_format in ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%Y/%m/%d']:
                    try:
                        parsed_date = datetime.strptime(date_str, date_format).date()
                        break
                    except ValueError:
                        continue
                else:
                    raise ValueError(f"Could not parse date: {date_str}")
            else:
                parsed_date = date_str
        except Exception as e:
            raise ValueError(f"Invalid date format in transaction {index}: {e}")
        
        # Parse and validate amount
        try:
            amount = float(raw_transaction['amount'])
            if amount == 0:
                raise ValueError(f"Zero amount not allowed in transaction {index}")
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid amount in transaction {index}: {e}")
        
        # Determine transaction type (debit/credit)
        transaction_type = raw_transaction.get('type', '').lower()
        is_debit = True  # Default to debit
        
        if transaction_type in ['credit', 'deposit', 'income']:
            is_debit = False
        elif transaction_type in ['debit', 'withdrawal', 'expense']:
            is_debit = True
        elif amount < 0:
            is_debit = False
            amount = abs(amount)  # Make amount positive
        
        # Categorize transaction
        description = raw_transaction['description'].strip()
        category = self._categorize_transaction_description(description, amount, is_debit)
        
        # Build normalized transaction
        normalized = {
            'date': parsed_date,
            'description': description,
            'amount': amount,
            'category': category,
            'subcategory': raw_transaction.get('subcategory'),
            'account_id': account_id,
            'is_debit': is_debit,
            'transaction_type': 'file_upload',
            'balance': raw_transaction.get('balance'),
            'reference_number': raw_transaction.get('reference_number', raw_transaction.get('ref_no')),
            'notes': raw_transaction.get('notes', raw_transaction.get('remarks')),
            'tags': self._generate_transaction_tags(description, category, raw_transaction)
        }
        
        return normalized
    
    def _categorize_transaction_description(self, description: str, amount: float, is_debit: bool) -> str:
        """Categorize transaction using LLM service or fallback logic."""
        try:
            return self.llm_service.categorize_transaction(description, amount)
        except Exception:
            # Fallback to simple keyword-based categorization
            description_lower = description.lower()
            
            if any(keyword in description_lower for keyword in ['atm', 'cash', 'withdrawal']):
                return 'Cash & ATM'
            elif any(keyword in description_lower for keyword in ['grocery', 'supermarket', 'food']):
                return 'Food & Dining'
            elif any(keyword in description_lower for keyword in ['fuel', 'petrol', 'gas']):
                return 'Transportation'
            elif any(keyword in description_lower for keyword in ['salary', 'income', 'transfer']):
                return 'Income' if not is_debit else 'Transfer'
            else:
                return 'Other'
    
    def _generate_transaction_tags(self, description: str, category: str, raw_transaction: dict) -> dict:
        """Generate tags for transaction based on description and category."""
        tags = {
            'categories': [category],
            'source': 'file_upload',
            'auto_categorized': True
        }
        
        # Add bank-specific tags if available
        if 'bank' in raw_transaction:
            tags['bank'] = raw_transaction['bank']
        
        # Add reference-based tags
        if raw_transaction.get('reference_number'):
            tags['has_reference'] = True
        
        return tags
    
    def _apply_business_logic_validation(self, transactions: List[dict], trace_id: str, user_id: str) -> List[dict]:
        """Apply business logic validation to normalized transactions."""
        validated_transactions = []
        
        for i, transaction in enumerate(transactions):
            try:
                # Validate amount ranges
                if transaction['amount'] > 1000000:  # 10 lakh
                    self.audit_service.log_action(
                        trace_id=trace_id,
                        user_id=user_id,
                        action="high_value_transaction_detected",
                        metadata={
                            "transaction_index": i,
                            "amount": transaction['amount'],
                            "description": transaction['description']
                        }
                    )
                
                # Validate date ranges (not too far in future/past)
                today = datetime.now().date()
                transaction_date = transaction['date']
                
                if isinstance(transaction_date, str):
                    transaction_date = datetime.strptime(transaction_date, '%Y-%m-%d').date()
                
                days_diff = abs((today - transaction_date).days)
                if days_diff > 365 * 2:  # More than 2 years
                    self.audit_service.log_action(
                        trace_id=trace_id,
                        user_id=user_id,
                        action="unusual_date_detected",
                        metadata={
                            "transaction_index": i,
                            "date": transaction_date.isoformat(),
                            "days_difference": days_diff
                        }
                    )
                
                # Ensure category is not null
                if not transaction.get('category'):
                    transaction['category'] = 'Other'
                
                validated_transactions.append(transaction)
                
            except Exception as e:
                self.audit_service.log_error(
                    trace_id=trace_id,
                    user_id=user_id,
                    action="business_logic_validation_failed",
                    error_message=str(e),
                    metadata={"transaction_index": i}
                )
                # Continue with other transactions
                continue
        
        return validated_transactions
    
    def _extract_file_content(self, file, file_type: str) -> str:
        """Extract content from uploaded file based on file type."""
        file.seek(0)  # Reset file pointer
        
        try:
            if file_type == 'pdf':
                return self._extract_pdf_content(file)
            elif file_type == 'csv':
                return self._extract_csv_content(file)
            elif file_type in ['xlsx', 'xls']:
                return self._extract_excel_content(file)
            elif file_type == 'txt':
                return self._extract_text_content(file)
            else:
                raise ValueError(f"Unsupported file type: {file_type}")
                
        except Exception as e:
            raise Exception(f"Failed to extract content from {file_type} file: {str(e)}")
    
    def _extract_pdf_content(self, file) -> str:
        """Extract text content from PDF file."""
        try:
            pdf_reader = PyPDF2.PdfReader(file)
            text_content = ""
            
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text_content += page.extract_text() + "\n"
            
            if not text_content.strip():
                raise ValueError("PDF appears to contain no extractable text")
            
            return text_content
            
        except Exception as e:
            raise Exception(f"PDF extraction failed: {str(e)}")
    
    def _extract_csv_content(self, file) -> str:
        """Extract content from CSV file."""
        try:
            # Try different encodings
            encodings = ['utf-8', 'latin-1', 'cp1252']
            
            for encoding in encodings:
                try:
                    file.seek(0)
                    content = file.read().decode(encoding)
                    # Validate CSV structure
                    csv_reader = csv.reader(io.StringIO(content))
                    rows = list(csv_reader)
                    
                    if len(rows) < 2:  # At least header + 1 data row
                        raise ValueError("CSV file must contain at least 2 rows (header + data)")
                    
                    return content
                    
                except UnicodeDecodeError:
                    continue
            
            raise ValueError("Could not decode CSV file with any supported encoding")
            
        except Exception as e:
            raise Exception(f"CSV extraction failed: {str(e)}")
    
    def _extract_excel_content(self, file) -> str:
        """Extract content from Excel file."""
        try:
            # Read Excel file
            df = pd.read_excel(file, engine='openpyxl' if file.filename.endswith('.xlsx') else 'xlrd')
            
            if df.empty:
                raise ValueError("Excel file appears to be empty")
            
            # Convert to CSV format for consistent processing
            csv_buffer = io.StringIO()
            df.to_csv(csv_buffer, index=False)
            
            return csv_buffer.getvalue()
            
        except Exception as e:
            raise Exception(f"Excel extraction failed: {str(e)}")
    
    def _extract_text_content(self, file) -> str:
        """Extract content from text file."""
        try:
            # Try different encodings
            encodings = ['utf-8', 'latin-1', 'cp1252']
            
            for encoding in encodings:
                try:
                    file.seek(0)
                    content = file.read().decode(encoding)
                    
                    if not content.strip():
                        raise ValueError("Text file appears to be empty")
                    
                    return content
                    
                except UnicodeDecodeError:
                    continue
            
            raise ValueError("Could not decode text file with any supported encoding")
            
        except Exception as e:
            raise Exception(f"Text extraction failed: {str(e)}")
    
    def _process_structured_data(self, content: str, bank_type: str) -> List[dict]:
        """Process structured data (CSV/Excel) for transaction extraction."""
        try:
            # Parse CSV content
            csv_reader = csv.DictReader(io.StringIO(content))
            transactions = []
            
            for row in csv_reader:
                # Map common CSV column names to standard fields
                mapped_row = self._map_csv_columns(row)
                
                if self._is_valid_transaction_row(mapped_row):
                    transactions.append(mapped_row)
            
            if not transactions:
                raise ValueError("No valid transactions found in structured data")
            
            return transactions
            
        except Exception as e:
            raise Exception(f"Structured data processing failed: {str(e)}")
    
    def _map_csv_columns(self, row: dict) -> dict:
        """Map CSV column names to standard transaction fields."""
        # Common column name mappings
        column_mappings = {
            'date': ['date', 'transaction_date', 'txn_date', 'dt'],
            'description': ['description', 'particulars', 'details', 'narration', 'remarks'],
            'amount': ['amount', 'debit', 'credit', 'withdrawal', 'deposit'],
            'type': ['type', 'transaction_type', 'dr_cr', 'debit_credit'],
            'balance': ['balance', 'running_balance', 'closing_balance'],
            'reference_number': ['reference', 'ref_no', 'cheque_no', 'transaction_id']
        }
        
        mapped = {}
        row_lower = {k.lower().replace(' ', '_'): v for k, v in row.items()}
        
        for standard_field, possible_names in column_mappings.items():
            for possible_name in possible_names:
                if possible_name in row_lower and row_lower[possible_name]:
                    mapped[standard_field] = row_lower[possible_name]
                    break
        
        return mapped
    
    def _is_valid_transaction_row(self, row: dict) -> bool:
        """Check if a CSV row represents a valid transaction."""
        # Must have date, description, and amount
        required_fields = ['date', 'description', 'amount']
        
        for field in required_fields:
            if field not in row or not str(row[field]).strip():
                return False
        
        # Amount must be numeric
        try:
            float(row['amount'])
        except (ValueError, TypeError):
            return False
        
        return True
    
    def _get_file_size(self, file) -> int:
        """Get file size in bytes."""
        try:
            file.seek(0, 2)  # Seek to end
            size = file.tell()
            file.seek(0)  # Reset to beginning
            return size
        except Exception:
            return 0
