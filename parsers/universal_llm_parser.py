"""
Universal LLM Parser for bank statements with robust error handling.
Provides intelligent parsing using LLM with proper error management.
"""

import logging
import json
from datetime import datetime
from typing import List, Dict, Optional, Any
import sys
import os

# Add project root to path for imports
try:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
except NameError:
    # Handle case when __file__ is not defined (e.g., when exec'd)
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath('.'))))

from llm_services.llm_service import LLMService, LLMServiceError
from .exceptions import PDFParsingError


class UniversalLLMParser:
    """
    Universal parser that uses LLM for intelligent bank statement parsing.
    """
    
    def __init__(self, enable_llm: bool = True):
        """
        Initialize the universal parser.
        
        Args:
            enable_llm: Whether to enable LLM parsing (default: True)
        """
        self.enable_llm = enable_llm
        self.logger = logging.getLogger(__name__)
        
        # Initialize LLM service
        self.llm_service = None
        
        if self.enable_llm:
            try:
                self.llm_service = LLMService()
                self.logger.info("LLM service initialized successfully")
            except Exception as e:
                self.logger.error(f"Failed to initialize LLM service: {e}")
                raise PDFParsingError(
                    f"LLM service is not available. Please ensure Ollama is running and accessible. Error: {e}",
                    "llm_service_unavailable"
                )
        
        # Bank parser mapping for reference
        self.parser_mapping = {
            'federal bank': 'federal_bank_parser',
            'hdfc bank': 'hdfc_savings',
            'hdfc credit card': 'hdfc_credit_card',
            'hdfc': 'hdfc_savings'
        }
    
    def parse_statement(self, pdf_text: str, bank_name: str) -> List[Dict]:
        """
        Parse bank statement using LLM with proper error handling.
        
        Args:
            pdf_text: Raw text extracted from PDF
            bank_name: Name of the bank (e.g., "Federal Bank", "HDFC Bank")
            
        Returns:
            List of transaction dictionaries with enhanced categorization
            
        Raises:
            PDFParsingError: If parsing fails with specific error types
        """
        bank_name_lower = bank_name.lower().strip()
        start_time = datetime.now()
        
        self.logger.info(f"Starting LLM statement parsing for {bank_name} at {start_time}")
        
        if not self.enable_llm or not self.llm_service:
            raise PDFParsingError(
                "LLM parsing is disabled or service unavailable",
                "llm_service_disabled"
            )
        
        # Validate PDF text
        if not pdf_text or len(pdf_text.strip()) < 50:
            raise PDFParsingError(
                "PDF text is too short or empty. The PDF may be corrupted or contain no readable text.",
                "invalid_pdf_content"
            )
        
        try:
            self.logger.info(f"Processing {len(pdf_text)} characters with LLM for {bank_name}")
            transactions = self._parse_with_llm(pdf_text, bank_name)
            
            if not transactions:
                raise PDFParsingError(
                    f"No transactions could be extracted from the {bank_name} statement. The PDF may not contain transaction data or may be in an unsupported format.",
                    "no_transactions_found"
                )
            
            # Add automatic categorization
            try:
                transactions = self._add_llm_categorization(transactions)
                self.logger.info(f"Added LLM categorization to {len(transactions)} transactions")
            except Exception as e:
                self.logger.warning(f"Failed to add LLM categorization: {e}")
                # Continue without categorization rather than failing completely
                for txn in transactions:
                    if 'category' not in txn:
                        txn['category'] = 'Other'
            
            # Validate and log success
            validated_transactions = self._validate_transactions(transactions)
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            self.logger.info(f"✅ LLM parsing successful for {bank_name}: "
                           f"{len(validated_transactions)} transactions in {duration:.2f}s")
            
            return validated_transactions
                
        except LLMServiceError as e:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            self.logger.error(f"❌ LLM parsing failed for {bank_name} after {duration:.2f}s: {e}")
            
            # Determine specific error type based on the LLM error
            if "invalid JSON" in str(e).lower():
                error_type = "json_parsing_error"
                message = f"The LLM service returned malformed data for the {bank_name} statement. This may indicate the PDF format is not supported or the content is unclear."
            elif "timeout" in str(e).lower():
                error_type = "llm_timeout"
                message = f"LLM processing timed out for the {bank_name} statement. The PDF may be too large or complex to process."
            elif "connection" in str(e).lower():
                error_type = "llm_connection_error"
                message = f"Cannot connect to the LLM service. Please ensure Ollama is running and accessible."
            else:
                error_type = "llm_processing_error"
                message = f"Failed to process the {bank_name} statement with LLM: {str(e)}"
            
            raise PDFParsingError(message, error_type)
            
        except Exception as e:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            self.logger.error(f"❌ Unexpected error during parsing for {bank_name} after {duration:.2f}s: {e}")
            raise PDFParsingError(
                f"An unexpected error occurred while processing the {bank_name} statement: {str(e)}",
                "unexpected_error"
            )
    
    def _parse_with_llm(self, pdf_text: str, bank_name: str) -> List[Dict]:
        """
        Parse statement using LLM service.
        
        Args:
            pdf_text: Raw PDF text
            bank_name: Bank name
            
        Returns:
            List of transaction dictionaries
            
        Raises:
            LLMServiceError: If LLM parsing fails
        """
        if not self.llm_service:
            raise LLMServiceError("LLM service not available")
        
        self.logger.info(f"Using LLM service to parse {len(pdf_text)} characters")
        
        # Use LLM service to parse the statement
        transactions = self.llm_service.parse_bank_statement(pdf_text, bank_name)
        
        if not transactions:
            raise LLMServiceError("LLM returned empty transaction list")
        
        self.logger.info(f"LLM extracted {len(transactions)} transactions")
        return transactions
    
    def _add_llm_categorization(self, transactions: List[Dict]) -> List[Dict]:
        """
        Add LLM-based categorization to transactions.
        
        Args:
            transactions: List of transaction dictionaries
            
        Returns:
            Transactions with added 'category' field
        """
        if not self.llm_service:
            return transactions
        
        categorized_transactions = []
        
        for transaction in transactions:
            try:
                # Get description and amount for categorization
                description = transaction.get('description', '')
                amount = float(transaction.get('amount', 0))
                
                # Use LLM to categorize
                category = self.llm_service.categorize_transaction(description, amount)
                
                # Add category to transaction
                transaction['category'] = category
                transaction['categorization_method'] = 'llm'
                
                self.logger.debug(f"Categorized '{description}' as '{category}'")
                
            except Exception as e:
                self.logger.warning(f"Failed to categorize transaction '{transaction.get('description', '')}': {e}")
                transaction['category'] = 'Other'
                transaction['categorization_method'] = 'fallback'
            
            categorized_transactions.append(transaction)
        
        return categorized_transactions
    
    def _validate_transactions(self, transactions: List[Dict]) -> List[Dict]:
        """
        Validate and clean transaction data.
        
        Args:
            transactions: List of transaction dictionaries
            
        Returns:
            Validated and cleaned transactions
            
        Raises:
            PDFParsingError: If validation fails
        """
        if not transactions:
            raise PDFParsingError("No transactions to validate", "no_transactions")
        
        validated_transactions = []
        required_fields = ['date', 'description', 'amount']
        
        for i, transaction in enumerate(transactions):
            try:
                # Check required fields
                for field in required_fields:
                    if field not in transaction or transaction[field] is None:
                        raise ValueError(f"Missing required field: {field}")
                
                # Validate and clean data
                cleaned_transaction = {
                    'date': self._validate_date(transaction['date']),
                    'description': str(transaction['description']).strip(),
                    'amount': self._validate_amount(transaction['amount']),
                    'category': transaction.get('category', 'Other'),
                    'type': transaction.get('type', 'debit' if float(transaction['amount']) < 0 else 'credit'),
                    'categorization_method': transaction.get('categorization_method', 'llm')
                }
                
                validated_transactions.append(cleaned_transaction)
                
            except Exception as e:
                self.logger.warning(f"Skipping invalid transaction {i+1}: {e}")
                # Continue processing other transactions rather than failing completely
                continue
        
        if not validated_transactions:
            raise PDFParsingError(
                "All extracted transactions failed validation. The PDF may contain invalid or unrecognizable transaction data.",
                "validation_failed"
            )
        
        self.logger.info(f"Validated {len(validated_transactions)} out of {len(transactions)} transactions")
        return validated_transactions
    
    def _validate_date(self, date_str: str) -> str:
        """Validate and normalize date string"""
        if not date_str:
            raise ValueError("Date is empty")
        
        # Try to parse the date to ensure it's valid
        try:
            # Common date formats
            for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y']:
                try:
                    parsed_date = datetime.strptime(str(date_str), fmt)
                    return parsed_date.strftime('%Y-%m-%d')
                except ValueError:
                    continue
            
            raise ValueError(f"Unrecognized date format: {date_str}")
            
        except Exception as e:
            raise ValueError(f"Invalid date: {date_str} - {e}")
    
    def _validate_amount(self, amount) -> float:
        """Validate and normalize amount"""
        try:
            amount_float = float(amount)
            if abs(amount_float) > 10000000:  # 10 million limit
                raise ValueError(f"Amount too large: {amount_float}")
            return amount_float
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid amount: {amount} - {e}")


def parse_bank_statement(pdf_text: str, bank_name: str, enable_llm: bool = True) -> List[Dict]:
    """
    Convenience function to parse bank statement using Universal LLM Parser.
    
    Args:
        pdf_text: Raw text extracted from PDF
        bank_name: Name of the bank
        enable_llm: Whether to enable LLM parsing
        
    Returns:
        List of transaction dictionaries
        
    Raises:
        PDFParsingError: If parsing fails
    """
    parser = UniversalLLMParser(enable_llm=enable_llm)
    return parser.parse_statement(pdf_text, bank_name)


# Convenience functions for specific banks
def parse_federal_bank_statement_llm(pdf_text: str) -> List[Dict]:
    """Parse Federal Bank statement with LLM support."""
    return parse_bank_statement(pdf_text, "Federal Bank")


def parse_hdfc_statement_llm(pdf_text: str, account_type: str = "savings") -> List[Dict]:
    """Parse HDFC statement with LLM support."""
    bank_name = "HDFC Bank" if account_type.lower() == "savings" else "HDFC Credit Card"
    return parse_bank_statement(pdf_text, bank_name)


if __name__ == "__main__":
    # Test the universal parser
    import sys
    
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    logger.info("Testing Universal LLM Parser")
    
    # Test initialization
    parser = UniversalLLMParser()
    logger.info(f"Parser initialized - LLM enabled: {parser.enable_llm}")
    
    # Test with sample data
    sample_text = """
    Date: 2024-01-15
    Description: ATM Withdrawal
    Amount: 5000.00
    Type: Debit
    """
    
    try:
        transactions = parser.parse_statement(sample_text, "Federal Bank")
        logger.info(f"Test successful: {len(transactions)} transactions parsed")
        for transaction in transactions:
            logger.info(f"  - {transaction}")
    except Exception as e:
        logger.error(f"Test failed: {e}") 