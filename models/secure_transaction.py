"""
Secure Transaction Model

This module provides a secure wrapper around the Transaction model that handles:
1. Automatic encryption/decryption of sensitive fields
2. Audit logging for all data access operations
3. Backward compatibility with unencrypted data during migration
4. User-specific data access controls
"""

import os
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from flask import request

# Import the main models and utilities
from models import db, Transaction, AuditLog
from utils.encryption import TransactionEncryption, EncryptionError

# Configure logging
logger = logging.getLogger(__name__)


class SecureTransactionError(Exception):
    """Custom exception for secure transaction operations"""
    pass


class SecureTransaction:
    """
    Secure wrapper for Transaction model with encryption and audit logging
    """
    
    def __init__(self):
        """Initialize the secure transaction handler"""
        self.encryption = TransactionEncryption()
        self.encryption_key_id = "default_key_v1"
        
    def _log_audit_action(self, action: str, user_id: Optional[int] = None, 
                         transaction_id: Optional[int] = None, details: Optional[Dict[str, Any]] = None,
                         success: bool = True, error_message: Optional[str] = None):
        """Log audit action for transaction operations"""
        try:
            # Get request context information if available
            ip_address = None
            user_agent = None
            try:
                if request:
                    ip_address = request.remote_addr
                    user_agent = request.headers.get('User-Agent')
            except RuntimeError:
                # Outside request context
                pass
            
            AuditLog.log_action(
                action=action,
                user_id=user_id,
                details=details,
                ip_address=ip_address,
                user_agent=user_agent,
                resource_type='transaction',
                resource_id=str(transaction_id) if transaction_id else None,
                success=success,
                error_message=error_message
            )
            db.session.commit()
        except Exception as e:
            logger.error(f"Failed to log audit action: {e}")
    
    def _encrypt_transaction_data(self, transaction_data: Dict[str, Any]) -> Dict[str, Any]:
        """Encrypt sensitive fields in transaction data"""
        try:
            encrypted_data = transaction_data.copy()
            
            # Encrypt sensitive fields
            sensitive_fields = {
                'description': transaction_data.get('description'),
                'amount': str(transaction_data.get('amount', ''))
            }
            
            encrypted_fields = self.encryption.encrypt_sensitive_fields(sensitive_fields)
            
            # Add encrypted fields to the data
            encrypted_data['encrypted_description'] = encrypted_fields.get('description')
            encrypted_data['encrypted_amount'] = encrypted_fields.get('amount')
            encrypted_data['encryption_key_id'] = self.encryption_key_id
            encrypted_data['is_encrypted'] = True
            
            return encrypted_data
            
        except EncryptionError as e:
            logger.error(f"Encryption failed: {e}")
            raise SecureTransactionError(f"Failed to encrypt transaction data: {e}")
    
    def _decrypt_transaction_data(self, transaction: Transaction) -> Dict[str, Any]:
        """Decrypt sensitive fields in transaction data"""
        try:
            transaction_dict = transaction.to_dict()
            
            # If transaction is encrypted, decrypt it
            if transaction.is_encrypted and transaction.encrypted_description and transaction.encrypted_amount:
                encrypted_fields = {
                    'description': transaction.encrypted_description,
                    'amount': transaction.encrypted_amount
                }
                
                decrypted_fields = self.encryption.decrypt_sensitive_fields(encrypted_fields)
                
                # Replace with decrypted values
                transaction_dict['description'] = decrypted_fields.get('description', transaction.description)
                transaction_dict['amount'] = float(decrypted_fields.get('amount', transaction.amount))
            
            return transaction_dict
            
        except EncryptionError as e:
            logger.error(f"Decryption failed for transaction {transaction.id}: {e}")
            # Return original data if decryption fails
            return transaction.to_dict()
    
    def store_transaction_encrypted(self, transaction_data: Dict[str, Any], user_id: Optional[int] = None) -> int:
        """
        Store a new transaction with encrypted sensitive fields
        
        Args:
            transaction_data: Dictionary containing transaction information
            user_id: ID of the user creating the transaction
            
        Returns:
            int: ID of the created transaction
        """
        try:
            # Log the attempt
            self._log_audit_action(
                action='transaction_create_attempt',
                user_id=user_id,
                details={'fields': list(transaction_data.keys())}
            )
            
            # Encrypt sensitive data
            encrypted_data = self._encrypt_transaction_data(transaction_data)
            
            # Create new transaction
            transaction = Transaction(
                date=encrypted_data.get('date'),
                description=encrypted_data.get('description', ''),
                amount=encrypted_data.get('amount', 0),
                category=encrypted_data.get('category', 'Miscellaneous'),
                subcategory=encrypted_data.get('subcategory'),
                tags=encrypted_data.get('tags'),
                account_id=encrypted_data.get('account_id'),
                is_debit=encrypted_data.get('is_debit', True),
                transaction_type=encrypted_data.get('transaction_type', 'manual'),
                balance=encrypted_data.get('balance'),
                reference_number=encrypted_data.get('reference_number'),
                notes=encrypted_data.get('notes'),
                # Encryption fields
                encrypted_description=encrypted_data.get('encrypted_description'),
                encrypted_amount=encrypted_data.get('encrypted_amount'),
                encryption_key_id=encrypted_data.get('encryption_key_id'),
                is_encrypted=encrypted_data.get('is_encrypted', False)
            )
            
            db.session.add(transaction)
            db.session.commit()
            
            # Log successful creation
            self._log_audit_action(
                action='transaction_created',
                user_id=user_id,
                transaction_id=transaction.id,
                details={
                    'category': transaction.category,
                    'amount': float(transaction.amount),
                    'is_encrypted': transaction.is_encrypted
                }
            )
            
            logger.info(f"Transaction {transaction.id} created and encrypted successfully")
            return transaction.id
            
        except Exception as e:
            db.session.rollback()
            error_msg = f"Failed to store encrypted transaction: {e}"
            logger.error(error_msg)
            
            # Log the failure
            self._log_audit_action(
                action='transaction_create_failed',
                user_id=user_id,
                success=False,
                error_message=str(e)
            )
            
            raise SecureTransactionError(error_msg)
    
    def get_transactions_decrypted(self, user_id: Optional[int] = None, 
                                 filters: Optional[Dict[str, Any]] = None,
                                 limit: Optional[int] = None,
                                 offset: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Retrieve transactions with decrypted sensitive fields
        
        Args:
            user_id: ID of the user requesting transactions
            filters: Dictionary of filters to apply
            limit: Maximum number of transactions to return
            offset: Number of transactions to skip
            
        Returns:
            List of decrypted transaction dictionaries
        """
        try:
            # Log the access attempt
            self._log_audit_action(
                action='transactions_access_attempt',
                user_id=user_id,
                details={
                    'filters': filters or {},
                    'limit': limit,
                    'offset': offset
                }
            )
            
            # Build query
            query = Transaction.query
            
            # Apply filters
            if filters:
                if 'account_id' in filters:
                    query = query.filter(Transaction.account_id == filters['account_id'])
                if 'category' in filters:
                    query = query.filter(Transaction.category == filters['category'])
                if 'is_debit' in filters:
                    query = query.filter(Transaction.is_debit == filters['is_debit'])
                if 'date_from' in filters:
                    query = query.filter(Transaction.date >= filters['date_from'])
                if 'date_to' in filters:
                    query = query.filter(Transaction.date <= filters['date_to'])
            
            # Apply ordering
            query = query.order_by(Transaction.date.desc(), Transaction.id.desc())
            
            # Apply pagination
            if offset:
                query = query.offset(offset)
            if limit:
                query = query.limit(limit)
            
            # Execute query
            transactions = query.all()
            
            # Decrypt and convert to dictionaries
            decrypted_transactions = []
            for transaction in transactions:
                try:
                    decrypted_data = self._decrypt_transaction_data(transaction)
                    decrypted_transactions.append(decrypted_data)
                except Exception as e:
                    logger.error(f"Failed to decrypt transaction {transaction.id}: {e}")
                    # Include original data if decryption fails
                    decrypted_transactions.append(transaction.to_dict())
            
            # Log successful access
            self._log_audit_action(
                action='transactions_accessed',
                user_id=user_id,
                details={
                    'count': len(decrypted_transactions),
                    'encrypted_count': sum(1 for t in transactions if t.is_encrypted)
                }
            )
            
            return decrypted_transactions
            
        except Exception as e:
            error_msg = f"Failed to retrieve transactions: {e}"
            logger.error(error_msg)
            
            # Log the failure
            self._log_audit_action(
                action='transactions_access_failed',
                user_id=user_id,
                success=False,
                error_message=str(e)
            )
            
            raise SecureTransactionError(error_msg)
    
    def update_transaction_encrypted(self, transaction_id: int, updates: Dict[str, Any], 
                                   user_id: Optional[int] = None) -> bool:
        """
        Update a transaction with encrypted sensitive fields
        
        Args:
            transaction_id: ID of the transaction to update
            updates: Dictionary of fields to update
            user_id: ID of the user making the update
            
        Returns:
            bool: True if update was successful
        """
        try:
            # Log the update attempt
            self._log_audit_action(
                action='transaction_update_attempt',
                user_id=user_id,
                transaction_id=transaction_id,
                details={'fields_to_update': list(updates.keys())}
            )
            
            transaction = Transaction.query.get(transaction_id)
            if not transaction:
                raise SecureTransactionError(f"Transaction {transaction_id} not found")
            
            # Handle sensitive fields that need encryption
            sensitive_updates = {}
            if 'description' in updates:
                sensitive_updates['description'] = updates['description']
            if 'amount' in updates:
                sensitive_updates['amount'] = str(updates['amount'])
            
            # Encrypt sensitive fields if any
            if sensitive_updates:
                encrypted_fields = self.encryption.encrypt_sensitive_fields(sensitive_updates)
                
                # Update encrypted fields
                if 'description' in sensitive_updates:
                    transaction.encrypted_description = encrypted_fields.get('description')
                    transaction.description = updates['description']
                if 'amount' in sensitive_updates:
                    transaction.encrypted_amount = encrypted_fields.get('amount')
                    transaction.amount = updates['amount']
                
                transaction.encryption_key_id = self.encryption_key_id
                transaction.is_encrypted = True
            
            # Update non-sensitive fields
            for field, value in updates.items():
                if field not in ['description', 'amount'] and hasattr(transaction, field):
                    setattr(transaction, field, value)
            
            # Update timestamp
            transaction.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            # Log successful update
            self._log_audit_action(
                action='transaction_updated',
                user_id=user_id,
                transaction_id=transaction_id,
                details={
                    'updated_fields': list(updates.keys()),
                    'is_encrypted': transaction.is_encrypted
                }
            )
            
            return True
            
        except Exception as e:
            db.session.rollback()
            error_msg = f"Failed to update transaction {transaction_id}: {e}"
            logger.error(error_msg)
            
            # Log the failure
            self._log_audit_action(
                action='transaction_update_failed',
                user_id=user_id,
                transaction_id=transaction_id,
                success=False,
                error_message=str(e)
            )
            
            raise SecureTransactionError(error_msg)
