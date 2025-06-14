import json
from datetime import datetime

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func

db = SQLAlchemy()


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

    # Relationship
    account = db.relationship("Account", backref=db.backref("transactions", lazy=True))

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
