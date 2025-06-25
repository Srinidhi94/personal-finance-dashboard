import json
import hashlib
import uuid
from datetime import datetime
from enum import Enum

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, UniqueConstraint, Enum as SQLEnum

db = SQLAlchemy()


# Enum for transaction source
class TransactionSource(Enum):
    MANUAL_ENTRY = 'manual_entry'
    FILE_UPLOAD = 'file_upload'


class Transaction(db.Model):
    __tablename__ = "transactions"

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, index=True)
    description = db.Column(db.Text, nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    category = db.Column(db.String(50), nullable=False, default="Miscellaneous")
    subcategory = db.Column(db.String(50), nullable=True)
    tags = db.Column(db.Text, nullable=True)  # JSON field for storing multiple tags
    account_id = db.Column(db.Integer, db.ForeignKey("accounts.id"), nullable=False)
    is_debit = db.Column(db.Boolean, nullable=False, default=True)
    transaction_type = db.Column(db.String(20), nullable=False, default="manual")  # manual, pdf_parsed
    balance = db.Column(db.Numeric(12, 2), nullable=True)
    reference_number = db.Column(db.String(100), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # New encryption fields - added for encryption support
    encrypted_description = db.Column(db.Text, nullable=True)  # Encrypted version of description
    encrypted_amount = db.Column(db.Text, nullable=True)  # Encrypted version of amount
    encryption_key_id = db.Column(db.String(50), nullable=True)  # ID of encryption key used
    is_encrypted = db.Column(db.Boolean, default=False)  # Flag to indicate if transaction is encrypted

    # New fields for file upload tracking and audit purposes
    trace_id = db.Column(db.String(100), nullable=True, index=True)  # For tracking file upload operations
    source = db.Column(SQLEnum(TransactionSource), nullable=False, default=TransactionSource.MANUAL_ENTRY)  # Source of transaction
    processing_metadata = db.Column(db.Text, nullable=True)  # JSON field for storing processing details

    # Relationship
    account = db.relationship("Account", backref=db.backref("transactions", lazy=True))
    
    # Add unique constraint to prevent duplicate transactions
    __table_args__ = (
        UniqueConstraint('date', 'description', 'amount', 'account_id', name='unique_transaction'),
    )

    def get_tags(self):
        """Get tags as a dictionary"""
        if self.tags:
            try:
                if isinstance(self.tags, str):
                    return json.loads(self.tags)
                elif isinstance(self.tags, dict):
                    return self.tags
                else:
                    return {}
            except (json.JSONDecodeError, TypeError):
                return {}
        return {}

    def set_tags(self, tags_dict):
        """Set tags from a dictionary"""
        self.tags = json.dumps(tags_dict) if tags_dict else None

    def add_tag(self, tag_type, tag_value):
        """Add a single tag"""
        current_tags = self.get_tags()
        if tag_type not in current_tags:
            current_tags[tag_type] = []
        if tag_value not in current_tags[tag_type]:
            current_tags[tag_type].append(tag_value)
        self.set_tags(current_tags)

    def remove_tag(self, tag_type, tag_value):
        """Remove a single tag"""
        current_tags = self.get_tags()
        if tag_type in current_tags and tag_value in current_tags[tag_type]:
            current_tags[tag_type].remove(tag_value)
            if not current_tags[tag_type]:
                del current_tags[tag_type]
        self.set_tags(current_tags)

    def get_all_tag_values(self):
        """Get all tag values as a flat list"""
        all_tags = []
        for tag_type, tag_values in self.get_tags().items():
            all_tags.extend(tag_values)
        return all_tags

    def get_processing_metadata(self):
        """Get processing metadata as a dictionary"""
        if self.processing_metadata:
            try:
                if isinstance(self.processing_metadata, str):
                    return json.loads(self.processing_metadata)
                elif isinstance(self.processing_metadata, dict):
                    return self.processing_metadata
                else:
                    return {}
            except (json.JSONDecodeError, TypeError):
                return {}
        return {}

    def set_processing_metadata(self, metadata_dict):
        """Set processing metadata from a dictionary"""
        self.processing_metadata = json.dumps(metadata_dict) if metadata_dict else None

    def to_dict(self):
        tags_dict = self.get_tags()
        # Ensure tags_dict is always a proper dictionary
        if not isinstance(tags_dict, dict):
            tags_dict = {}

        return {
            "id": self.id,
            "date": self.date.strftime("%d/%m/%Y") if self.date else None,
            "description": self.description,
            "amount": float(self.amount),
            "category": self.category,
            "subcategory": self.subcategory,
            "tags": tags_dict,
            "account_name": self.account.name if self.account else "Unknown",
            "account_type": self.account.account_type if self.account else "Unknown",
            "bank": self.account.bank if self.account else "Unknown",
            "is_debit": self.is_debit,
            "type": "debit" if self.is_debit else "credit",
            "balance": float(self.balance) if self.balance else None,
            "reference_number": self.reference_number,
            "notes": self.notes,
            "transaction_type": self.transaction_type,
            "is_encrypted": self.is_encrypted,
            "trace_id": self.trace_id,
            "source": self.source.value if self.source else None,
            "processing_metadata": self.get_processing_metadata(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Account(db.Model):
    __tablename__ = "accounts"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    bank = db.Column(db.String(50), nullable=False)
    account_type = db.Column(db.String(20), nullable=False)  # savings, checking, credit_card
    account_number = db.Column(db.String(50), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "bank": self.bank,
            "account_type": self.account_type,
            "account_number": self.account_number,
            "is_active": self.is_active,
            "transaction_count": len(self.transactions),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    keywords = db.Column(db.Text, nullable=True)  # JSON string of keywords
    subcategories = db.Column(db.Text, nullable=True)  # JSON string of subcategories
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def get_keywords(self):
        return json.loads(self.keywords) if self.keywords else []

    def set_keywords(self, keywords_list):
        self.keywords = json.dumps(keywords_list)

    def get_subcategories(self):
        return json.loads(self.subcategories) if self.subcategories else {}

    def set_subcategories(self, subcategories_dict):
        self.subcategories = json.dumps(subcategories_dict)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "keywords": self.get_keywords(),
            "subcategories": self.get_subcategories(),
            "is_active": self.is_active,
        }


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=True)  # For future authentication
    is_premium = db.Column(db.Boolean, default=False)  # For PDF parsing feature
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "is_premium": self.is_premium,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ChatSession(db.Model):
    __tablename__ = "chat_sessions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)  # Nullable for anonymous sessions
    message = db.Column(db.Text, nullable=False)  # User's message/query
    response = db.Column(db.Text, nullable=False)  # LLM's response
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    session_id = db.Column(db.String(100), nullable=True, index=True)  # For grouping related messages
    processing_time_ms = db.Column(db.Integer, nullable=True)  # Time taken to process the query
    tokens_used = db.Column(db.Integer, nullable=True)  # Number of tokens used (if available)
    
    # Relationship
    user = db.relationship("User", backref=db.backref("chat_sessions", lazy=True))

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "message": self.message,
            "response": self.response,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "session_id": self.session_id,
            "processing_time_ms": self.processing_time_ms,
            "tokens_used": self.tokens_used,
        }


class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))  # UUID primary key
    trace_id = db.Column(db.String(100), nullable=True, index=True)  # For tracking related operations
    user_id = db.Column(db.String(36), nullable=True, index=True)  # UUID foreign key to users
    action = db.Column(db.String(100), nullable=False, index=True)  # e.g., 'upload_start', 'extraction_complete'
    entity_type = db.Column(db.String(50), nullable=True)  # e.g., 'transaction', 'account', 'file'
    entity_id = db.Column(db.String(36), nullable=True)  # UUID of the affected entity
    audit_metadata = db.Column(db.Text, nullable=True)  # JSON field for additional details
    ip_address = db.Column(db.String(45), nullable=True)  # IPv4/IPv6 address
    user_agent = db.Column(db.String(500), nullable=True)  # User agent string
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Legacy fields for backward compatibility
    user_id_hash = db.Column(db.String(64), nullable=True, index=True)  # Hashed user ID for privacy
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)  # Alias for created_at
    details = db.Column(db.Text, nullable=True)  # Alias for audit_metadata
    ip_address_hash = db.Column(db.String(64), nullable=True)  # Hashed IP address for privacy
    user_agent_hash = db.Column(db.String(64), nullable=True)  # Hashed user agent for privacy
    resource_type = db.Column(db.String(50), nullable=True)  # Alias for entity_type
    resource_id = db.Column(db.String(50), nullable=True)  # Alias for entity_id
    success = db.Column(db.Boolean, default=True)  # Whether the action was successful
    error_message = db.Column(db.Text, nullable=True)  # Error message if action failed

    @staticmethod
    def hash_sensitive_data(data):
        """Hash sensitive data for privacy"""
        if not data:
            return None
        return hashlib.sha256(str(data).encode()).hexdigest()

    @classmethod
    def log_action(cls, action, user_id=None, details=None, ip_address=None, user_agent=None, 
                   resource_type=None, resource_id=None, success=True, error_message=None,
                   trace_id=None, entity_type=None, entity_id=None, metadata=None):
        """
        Log an audit action with both new and legacy field support
        
        Args:
            action: Action being performed
            user_id: User ID (can be UUID string or integer)
            details: Legacy details field (use metadata instead)
            ip_address: IP address of the user
            user_agent: User agent string
            resource_type: Legacy resource type (use entity_type instead)
            resource_id: Legacy resource ID (use entity_id instead)
            success: Whether the action was successful
            error_message: Error message if action failed
            trace_id: Trace ID for tracking related operations
            entity_type: Type of entity being acted upon
            entity_id: ID of the entity being acted upon
            metadata: JSON metadata (preferred over details)
        """
        try:
            # Use new fields if provided, otherwise fall back to legacy fields
            final_entity_type = entity_type or resource_type
            final_entity_id = entity_id or resource_id
            final_metadata = metadata or details
            
            audit_log = cls(
                trace_id=trace_id,
                user_id=str(user_id) if user_id else None,
                action=action,
                entity_type=final_entity_type,
                entity_id=str(final_entity_id) if final_entity_id else None,
                audit_metadata=json.dumps(final_metadata) if isinstance(final_metadata, dict) else final_metadata,
                ip_address=ip_address,
                user_agent=user_agent,
                success=success,
                error_message=error_message,
                # Legacy fields for backward compatibility
                user_id_hash=cls.hash_sensitive_data(user_id) if user_id else None,
                timestamp=datetime.utcnow(),
                details=json.dumps(final_metadata) if isinstance(final_metadata, dict) else final_metadata,
                ip_address_hash=cls.hash_sensitive_data(ip_address) if ip_address else None,
                user_agent_hash=cls.hash_sensitive_data(user_agent) if user_agent else None,
                resource_type=final_entity_type,
                resource_id=str(final_entity_id) if final_entity_id else None
            )
            
            db.session.add(audit_log)
            return audit_log
        except Exception as e:
            print(f"Error logging audit action: {e}")
            return None

    def get_metadata(self):
        """Get metadata as a dictionary"""
        metadata_field = self.audit_metadata or self.details
        if metadata_field:
            try:
                if isinstance(metadata_field, str):
                    return json.loads(metadata_field)
                elif isinstance(metadata_field, dict):
                    return metadata_field
                else:
                    return {}
            except (json.JSONDecodeError, TypeError):
                return {}
        return {}

    def to_dict(self):
        return {
            "id": self.id,
            "trace_id": self.trace_id,
            "user_id": self.user_id,
            "action": self.action,
            "entity_type": self.entity_type or self.resource_type,
            "entity_id": self.entity_id or self.resource_id,
            "metadata": self.get_metadata(),
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "success": self.success,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            # Legacy fields
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "details": self.get_metadata(),  # Alias for metadata
        }


class LLMProcessingLog(db.Model):
    __tablename__ = "llm_processing_logs"

    id = db.Column(db.Integer, primary_key=True)
    processing_type = db.Column(db.String(50), nullable=False, index=True)  # e.g., 'bank_statement_parsing', 'transaction_categorization', 'chat_query'
    success = db.Column(db.Boolean, nullable=False, index=True)  # Whether the LLM processing was successful
    duration_ms = db.Column(db.Integer, nullable=False)  # Processing time in milliseconds
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    model_name = db.Column(db.String(100), nullable=True)  # Name of the LLM model used
    prompt_tokens = db.Column(db.Integer, nullable=True)  # Number of tokens in the prompt
    completion_tokens = db.Column(db.Integer, nullable=True)  # Number of tokens in the completion
    total_tokens = db.Column(db.Integer, nullable=True)  # Total tokens used
    error_message = db.Column(db.Text, nullable=True)  # Error message if processing failed
    retry_count = db.Column(db.Integer, default=0)  # Number of retries attempted
    endpoint_url = db.Column(db.String(200), nullable=True)  # LLM endpoint used
    request_size_bytes = db.Column(db.Integer, nullable=True)  # Size of the request
    response_size_bytes = db.Column(db.Integer, nullable=True)  # Size of the response

    @classmethod
    def log_processing(cls, processing_type, success, duration_ms, model_name=None, 
                      prompt_tokens=None, completion_tokens=None, total_tokens=None,
                      error_message=None, retry_count=0, endpoint_url=None,
                      request_size_bytes=None, response_size_bytes=None):
        """Convenience method to create LLM processing log entries"""
        log_entry = cls(
            processing_type=processing_type,
            success=success,
            duration_ms=duration_ms,
            model_name=model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            error_message=error_message,
            retry_count=retry_count,
            endpoint_url=endpoint_url,
            request_size_bytes=request_size_bytes,
            response_size_bytes=response_size_bytes
        )
        db.session.add(log_entry)
        return log_entry

    def to_dict(self):
        return {
            "id": self.id,
            "processing_type": self.processing_type,
            "success": self.success,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "model_name": self.model_name,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "endpoint_url": self.endpoint_url,
            "request_size_bytes": self.request_size_bytes,
            "response_size_bytes": self.response_size_bytes,
        }
