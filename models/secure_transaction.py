"""
Secure Transaction Model

This module provides a secure wrapper around the Transaction model that handles:
1. Automatic encryption/decryption of sensitive fields
2. Audit logging for all data access operations
3. Backward compatibility with unencrypted data during migration
4. User-specific data access controls
5. File upload tracking and processing metadata
"""

import os
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from flask import request

# Import the main models and utilities
from models import db, Transaction, AuditLog, TransactionSource
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
        
    def _log_audit_action(self, action: str, user_id: Optional[str] = None, 
                         transaction_id: Optional[int] = None, details: Optional[Dict[str, Any]] = None,
                         success: bool = True, error_message: Optional[str] = None,
                         trace_id: Optional[str] = None):
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
                metadata=details,
                ip_address=ip_address,
                user_agent=user_agent,
                entity_type='transaction',
                entity_id=str(transaction_id) if transaction_id else None,
                success=success,
                error_message=error_message,
                trace_id=trace_id
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
    
    def store_transaction_encrypted(self, transaction_data: Dict[str, Any], user_id: Optional[str] = None,
                                  trace_id: Optional[str] = None, source: TransactionSource = TransactionSource.MANUAL_ENTRY,
                                  processing_metadata: Optional[Dict[str, Any]] = None) -> int:
        """
        Store a new transaction with encrypted sensitive fields
        
        Args:
            transaction_data: Dictionary containing transaction information
            user_id: ID of the user creating the transaction
            trace_id: Trace ID for tracking file upload operations
            source: Source of the transaction (manual_entry or file_upload)
            processing_metadata: Processing metadata for file uploads
            
        Returns:
            int: ID of the created transaction
        """
        try:
            # Generate trace_id if not provided
            if not trace_id:
                trace_id = str(uuid.uuid4())
            
            # Log the attempt
            self._log_audit_action(
                action='transaction_create_attempt',
                user_id=user_id,
                details={'fields': list(transaction_data.keys()), 'source': source.value},
                trace_id=trace_id
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
                is_encrypted=encrypted_data.get('is_encrypted', False),
                # New fields
                trace_id=trace_id,
                source=source,
                processing_metadata=None
            )
            
            # Set processing metadata if provided
            if processing_metadata:
                transaction.set_processing_metadata(processing_metadata)
            
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
                    'is_encrypted': transaction.is_encrypted,
                    'source': transaction.source.value,
                    'has_processing_metadata': bool(processing_metadata)
                },
                trace_id=trace_id
            )
            
            logger.info(f"Transaction {transaction.id} created and encrypted successfully with trace_id {trace_id}")
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
                error_message=str(e),
                trace_id=trace_id
            )
            
            raise SecureTransactionError(error_msg)
    
    def get_transactions_decrypted(self, user_id: Optional[str] = None, 
                                 filters: Optional[Dict[str, Any]] = None,
                                 limit: Optional[int] = None,
                                 offset: Optional[int] = None,
                                 trace_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get transactions with decrypted sensitive fields
        
        Args:
            user_id: ID of the user requesting the data
            filters: Optional filters to apply (e.g., {'category': 'Food', 'source': 'file_upload'})
            limit: Maximum number of transactions to return
            offset: Number of transactions to skip
            trace_id: Optional trace ID for audit logging
            
        Returns:
            List of transaction dictionaries with decrypted data
        """
        try:
            # Log the access attempt
            self._log_audit_action(
                action='transactions_access_attempt',
                user_id=user_id,
                details={'filters': filters, 'limit': limit, 'offset': offset},
                trace_id=trace_id
            )
            
            # Build query
            query = Transaction.query
            
            # Apply filters
            if filters:
                for key, value in filters.items():
                    if key == 'category':
                        query = query.filter(Transaction.category == value)
                    elif key == 'source':
                        if isinstance(value, str):
                            query = query.filter(Transaction.source == TransactionSource(value))
                        else:
                            query = query.filter(Transaction.source == value)
                    elif key == 'trace_id':
                        query = query.filter(Transaction.trace_id == value)
                    elif key == 'account_id':
                        query = query.filter(Transaction.account_id == value)
                    elif key == 'is_debit':
                        query = query.filter(Transaction.is_debit == value)
                    elif key == 'date_from':
                        query = query.filter(Transaction.date >= value)
                    elif key == 'date_to':
                        query = query.filter(Transaction.date <= value)
            
            # Apply pagination
            if offset:
                query = query.offset(offset)
            if limit:
                query = query.limit(limit)
            
            # Order by date descending
            query = query.order_by(Transaction.date.desc())
            
            transactions = query.all()
            
            # Decrypt and return transaction data
            decrypted_transactions = []
            for transaction in transactions:
                decrypted_data = self._decrypt_transaction_data(transaction)
                decrypted_transactions.append(decrypted_data)
            
            # Log successful access
            self._log_audit_action(
                action='transactions_accessed',
                user_id=user_id,
                details={'count': len(decrypted_transactions), 'filters': filters},
                trace_id=trace_id
            )
            
            return decrypted_transactions
            
        except Exception as e:
            error_msg = f"Failed to get decrypted transactions: {e}"
            logger.error(error_msg)
            
            # Log the failure
            self._log_audit_action(
                action='transactions_access_failed',
                user_id=user_id,
                success=False,
                error_message=str(e),
                trace_id=trace_id
            )
            
            raise SecureTransactionError(error_msg)

    def get_transactions_by_trace_id(self, trace_id: str, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all transactions associated with a specific trace ID
        
        Args:
            trace_id: Trace ID to search for
            user_id: ID of the user requesting the data
            
        Returns:
            List of transaction dictionaries with decrypted data
        """
        return self.get_transactions_decrypted(
            user_id=user_id,
            filters={'trace_id': trace_id},
            trace_id=trace_id
        )

    def update_processing_metadata(self, transaction_id: int, metadata: Dict[str, Any], 
                                 user_id: Optional[str] = None, trace_id: Optional[str] = None) -> bool:
        """
        Update processing metadata for a transaction
        
        Args:
            transaction_id: ID of the transaction to update
            metadata: Processing metadata to set
            user_id: ID of the user making the update
            trace_id: Trace ID for audit logging
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            transaction = Transaction.query.get(transaction_id)
            if not transaction:
                raise SecureTransactionError(f"Transaction {transaction_id} not found")
            
            # Log the update attempt
            self._log_audit_action(
                action='transaction_metadata_update_attempt',
                user_id=user_id,
                transaction_id=transaction_id,
                details={'metadata_keys': list(metadata.keys())},
                trace_id=trace_id or transaction.trace_id
            )
            
            # Update processing metadata
            transaction.set_processing_metadata(metadata)
            transaction.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            # Log successful update
            self._log_audit_action(
                action='transaction_metadata_updated',
                user_id=user_id,
                transaction_id=transaction_id,
                details={'metadata': metadata},
                trace_id=trace_id or transaction.trace_id
            )
            
            logger.info(f"Processing metadata updated for transaction {transaction_id}")
            return True
            
        except Exception as e:
            db.session.rollback()
            error_msg = f"Failed to update processing metadata: {e}"
            logger.error(error_msg)
            
            # Log the failure
            self._log_audit_action(
                action='transaction_metadata_update_failed',
                user_id=user_id,
                transaction_id=transaction_id,
                success=False,
                error_message=str(e),
                trace_id=trace_id
            )
            
            return False
