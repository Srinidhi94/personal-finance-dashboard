"""
Transaction field-level encryption utilities using Fernet symmetric encryption.
"""

import os
import logging
import base64
from typing import Dict, Any, Optional
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class EncryptionError(Exception):
    """Custom exception for encryption-related errors."""
    pass


class TransactionEncryption:
    """
    Handles field-level encryption for transaction data.
    Encrypts sensitive fields while keeping metadata fields in plain text.
    """
    
    # Fields that should be encrypted
    ENCRYPTED_FIELDS = {'description', 'amount'}
    
    # Fields that remain in plain text
    PLAIN_FIELDS = {'date', 'category', 'bank_name', 'transaction_type'}
    
    def __init__(self, encryption_key: Optional[str] = None):
        """
        Initialize the encryption service.
        
        Args:
            encryption_key: Base64 encoded encryption key. If None, uses DB_ENCRYPTION_KEY from environment
            
        Raises:
            EncryptionError: If encryption key is invalid or missing
        """
        self.logger = logging.getLogger(__name__)
        
        # Get encryption key from parameter or environment
        key_string = encryption_key or os.getenv('DB_ENCRYPTION_KEY')
        
        if not key_string:
            raise EncryptionError("Encryption key not provided. Set DB_ENCRYPTION_KEY environment variable.")
        
        try:
            # Check if it's a 32-character string first (before base64 check)
            if len(key_string) == 32 and key_string.isalnum():
                # Derive key from 32-character string using PBKDF2
                self._fernet = self._derive_key_from_string(key_string)
            elif self._is_base64(key_string):
                # It's a base64 encoded Fernet key
                self._fernet = Fernet(key_string.encode())
            else:
                # Try to derive from any string
                self._fernet = self._derive_key_from_string(key_string)
                
        except Exception as e:
            raise EncryptionError(f"Invalid encryption key format: {e}")
    
    def _is_base64(self, s: str) -> bool:
        """Check if string is valid base64."""
        try:
            base64.urlsafe_b64decode(s.encode())
            return True
        except Exception:
            return False
    
    def _derive_key_from_string(self, key_string: str) -> Fernet:
        """
        Derive a Fernet key from a string using PBKDF2.
        
        Args:
            key_string: String to derive key from
            
        Returns:
            Fernet instance with derived key
        """
        # Use a fixed salt for consistency (in production, consider storing salt separately)
        salt = b'finance_app_salt_2024'
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        
        key = base64.urlsafe_b64encode(kdf.derive(key_string.encode()))
        return Fernet(key)
    
    def encrypt_sensitive_fields(self, transaction_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Encrypt sensitive fields in a transaction dictionary.
        
        Args:
            transaction_dict: Dictionary containing transaction data
            
        Returns:
            Dictionary with sensitive fields encrypted
            
        Raises:
            EncryptionError: If encryption fails
        """
        if not isinstance(transaction_dict, dict):
            raise EncryptionError("Input must be a dictionary")
        
        try:
            encrypted_dict = transaction_dict.copy()
            
            for field in self.ENCRYPTED_FIELDS:
                if field in encrypted_dict and encrypted_dict[field] is not None:
                    # Convert to string if not already
                    field_value = str(encrypted_dict[field])
                    
                    # Encrypt the field value
                    encrypted_value = self._fernet.encrypt(field_value.encode('utf-8'))
                    
                    # Store as base64 string for database compatibility
                    encrypted_dict[field] = base64.urlsafe_b64encode(encrypted_value).decode('utf-8')
                    
                    self.logger.debug(f"Encrypted field '{field}'")
            
            # Add encryption marker
            encrypted_dict['_encrypted'] = True
            
            return encrypted_dict
            
        except Exception as e:
            self.logger.error(f"Failed to encrypt transaction fields: {e}")
            raise EncryptionError(f"Encryption failed: {e}")
    
    def decrypt_sensitive_fields(self, encrypted_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Decrypt sensitive fields in an encrypted transaction dictionary.
        
        Args:
            encrypted_dict: Dictionary containing encrypted transaction data
            
        Returns:
            Dictionary with sensitive fields decrypted
            
        Raises:
            EncryptionError: If decryption fails
        """
        if not isinstance(encrypted_dict, dict):
            raise EncryptionError("Input must be a dictionary")
        
        # If not marked as encrypted, return as-is
        if not encrypted_dict.get('_encrypted', False):
            return encrypted_dict
        
        try:
            decrypted_dict = encrypted_dict.copy()
            
            for field in self.ENCRYPTED_FIELDS:
                if field in decrypted_dict and decrypted_dict[field] is not None:
                    try:
                        # Decode from base64
                        encrypted_bytes = base64.urlsafe_b64decode(decrypted_dict[field].encode('utf-8'))
                        
                        # Decrypt the field value
                        decrypted_bytes = self._fernet.decrypt(encrypted_bytes)
                        decrypted_value = decrypted_bytes.decode('utf-8')
                        
                        # Convert back to appropriate type
                        if field == 'amount':
                            try:
                                decrypted_dict[field] = float(decrypted_value)
                            except ValueError:
                                decrypted_dict[field] = decrypted_value
                        else:
                            decrypted_dict[field] = decrypted_value
                        
                        self.logger.debug(f"Decrypted field '{field}'")
                        
                    except InvalidToken:
                        self.logger.error(f"Invalid encryption token for field '{field}'")
                        raise EncryptionError(f"Failed to decrypt field '{field}': Invalid token")
                    except Exception as e:
                        self.logger.error(f"Failed to decrypt field '{field}': {e}")
                        raise EncryptionError(f"Failed to decrypt field '{field}': {e}")
            
            # Remove encryption marker
            decrypted_dict.pop('_encrypted', None)
            
            return decrypted_dict
            
        except EncryptionError:
            raise
        except Exception as e:
            self.logger.error(f"Failed to decrypt transaction fields: {e}")
            raise EncryptionError(f"Decryption failed: {e}")
    
    @staticmethod
    def generate_key() -> str:
        """
        Generate a new Fernet encryption key.
        
        Returns:
            Base64 encoded encryption key string
        """
        key = Fernet.generate_key()
        return key.decode('utf-8')
