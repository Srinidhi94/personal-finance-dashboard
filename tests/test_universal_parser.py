#!/usr/bin/env python3

"""
Comprehensive test suite for Universal LLM Parser.

This module tests the universal parser functionality including:
- LLM parsing success scenarios
- LLM parsing failure scenarios with fallback
- Transaction categorization with LLM
- Output format validation
- Environment variable control
"""

import os
import sys
from datetime import datetime
from unittest.mock import MagicMock, patch, Mock
import json

import pytest

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.universal_llm_parser import UniversalLLMParser, parse_bank_statement
from llm_services.llm_service import LLMService, LLMServiceError


@pytest.fixture
def mock_pdf_text():
    """Mock PDF text content for testing."""
    return """
    FEDERAL BANK
    SAVINGS A/C NO: 12345678901
    Statement Period: 01 May 2024 to 31 May 2024
    
    Opening Balance on 01 May 2024: ₹10,000.00
    
    01 May 2024
    UPI/CR/123456/SALARY PAYMENT
    Credit: 50,000.00
    Balance: 60,000.00
    
    02 May 2024
    POS/DEBIT CARD/STARBUCKS COFFEE
    Debit: 450.00
    Balance: 59,550.00
    
    03 May 2024
    ATM/CASH WITHDRAWAL/ATM001
    Debit: 2,000.00
    Balance: 57,550.00
    
    04 May 2024
    UPI/DR/AMAZON PURCHASE
    Debit: 1,299.00
    Balance: 56,251.00
    
    Closing Balance on 31 May 2024: ₹56,251.00
    """


@pytest.fixture
def mock_llm_response_success():
    """Mock successful LLM response for transaction parsing."""
    return {
        "transactions": [
            {
                "date": "01/05/2024",
                "description": "SALARY PAYMENT",
                "amount": 50000.00,
                "transaction_type": "credit"
            },
            {
                "date": "02/05/2024", 
                "description": "STARBUCKS COFFEE",
                "amount": -450.00,
                "transaction_type": "debit"
            },
            {
                "date": "03/05/2024",
                "description": "ATM CASH WITHDRAWAL",
                "amount": -2000.00,
                "transaction_type": "debit"
            },
            {
                "date": "04/05/2024",
                "description": "AMAZON PURCHASE", 
                "amount": -1299.00,
                "transaction_type": "debit"
            }
        ]
    }


@pytest.fixture
def mock_categorization_responses():
    """Mock LLM categorization responses."""
    return {
        "SALARY PAYMENT": "Income",
        "STARBUCKS COFFEE": "Food & Dining",
        "ATM CASH WITHDRAWAL": "Cash & ATM",
        "AMAZON PURCHASE": "Shopping"
    }


class TestUniversalLLMParser:
    """Test Universal LLM Parser functionality."""

    def test_parser_initialization(self):
        """Test parser initialization with different configurations."""
        # Test default initialization
        parser = UniversalLLMParser()
        assert parser is not None
        assert hasattr(parser, 'llm_service')
        assert hasattr(parser, 'logger')

    @patch('parsers.universal_llm_parser.LLMService')
    def test_llm_parsing_success(self, mock_llm_service_class, mock_pdf_text, mock_llm_response_success):
        """Test successful LLM parsing scenario."""
        # Setup mock LLM service
        mock_llm_service = Mock()
        mock_llm_service.parse_bank_statement.return_value = mock_llm_response_success
        mock_llm_service_class.return_value = mock_llm_service
        
        # Setup categorization responses
        mock_llm_service.categorize_transaction.side_effect = [
            "Income", "Food & Dining", "Cash & ATM", "Shopping"
        ]
        
        parser = UniversalLLMParser()
        result = parser.parse_statement(mock_pdf_text, "Federal Bank")
        
        # Verify LLM service was called
        mock_llm_service.parse_bank_statement.assert_called_once_with(mock_pdf_text)
        
        # Verify result structure
        assert isinstance(result, list)
        assert len(result) == 4
        
        # Verify transaction structure
        for transaction in result:
            assert "date" in transaction
            assert "description" in transaction
            assert "amount" in transaction
            assert "category" in transaction
            assert "categorization_method" in transaction
            assert transaction["categorization_method"] == "llm"

    @patch('parsers.universal_llm_parser.LLMService')
    def test_llm_parsing_failure_fallback(self, mock_llm_service_class, mock_pdf_text):
        """Test LLM parsing failure with fallback to traditional parsers."""
        # Setup mock LLM service to fail
        mock_llm_service = Mock()
        mock_llm_service.parse_bank_statement.side_effect = LLMServiceError("LLM service unavailable")
        mock_llm_service_class.return_value = mock_llm_service
        
        # Mock traditional parser
        with patch('parsers.universal_llm_parser.extract_federal_bank_savings') as mock_traditional_parser:
            mock_traditional_parser.return_value = [
                {
                    "date": "01/05/2024",
                    "description": "SALARY PAYMENT",
                    "amount": 50000.00,
                    "type": "credit"
                },
                {
                    "date": "02/05/2024",
                    "description": "STARBUCKS COFFEE", 
                    "amount": -450.00,
                    "type": "debit"
                }
            ]
            
            # Mock categorization for fallback transactions
            mock_llm_service.categorize_transaction.side_effect = ["Income", "Food & Dining"]
            
            parser = UniversalLLMParser()
            result = parser.parse_statement(mock_pdf_text, "Federal Bank")
            
            # Verify LLM parsing was attempted
            mock_llm_service.parse_bank_statement.assert_called_once()
            
            # Verify fallback parser was called
            mock_traditional_parser.assert_called_once()
            
            # Verify result structure
            assert isinstance(result, list)
            assert len(result) == 2
            
            # Verify categorization method is marked as fallback
            for transaction in result:
                assert transaction["categorization_method"] == "llm"

    @patch('parsers.universal_llm_parser.LLMService')
    def test_transaction_categorization(self, mock_llm_service_class, mock_categorization_responses):
        """Test transaction categorization with LLM."""
        mock_llm_service = Mock()
        mock_llm_service_class.return_value = mock_llm_service
        
        parser = UniversalLLMParser()
        
        # Test individual categorizations
        test_descriptions = [
            "STARBUCKS COFFEE",
            "SALARY PAYMENT", 
            "AMAZON PURCHASE",
            "ATM CASH WITHDRAWAL"
        ]
        
        expected_categories = [
            "Food & Dining",
            "Income",
            "Shopping", 
            "Cash & ATM"
        ]
        
        mock_llm_service.categorize_transaction.side_effect = expected_categories
        
        for desc, expected_cat in zip(test_descriptions, expected_categories):
            category = parser._categorize_with_llm(desc)
            assert category == expected_cat
        
        # Verify all categorization calls were made
        assert mock_llm_service.categorize_transaction.call_count == len(test_descriptions)

    @patch('parsers.universal_llm_parser.LLMService')
    def test_categorization_failure_fallback(self, mock_llm_service_class):
        """Test categorization failure with fallback to default."""
        mock_llm_service = Mock()
        mock_llm_service.categorize_transaction.side_effect = LLMServiceError("Categorization failed")
        mock_llm_service_class.return_value = mock_llm_service
        
        parser = UniversalLLMParser()
        category = parser._categorize_with_llm("SOME TRANSACTION")
        
        # Should fallback to default category
        assert category == "Other"

    def test_output_format_validation(self, mock_pdf_text):
        """Test output format validation and standardization."""
        with patch('parsers.universal_llm_parser.LLMService') as mock_llm_service_class:
            mock_llm_service = Mock()
            mock_llm_service_class.return_value = mock_llm_service
            
            # Mock LLM response with various formats
            mock_llm_service.parse_bank_statement.return_value = {
                "transactions": [
                    {
                        "date": "01/05/2024",
                        "description": "TEST TRANSACTION",
                        "amount": 1000.00,
                        "transaction_type": "credit"
                    },
                    {
                        "date": "02-05-2024",  # Different date format
                        "description": "ANOTHER TEST",
                        "amount": "-500",  # String amount
                        "transaction_type": "debit"
                    }
                ]
            }
            
            mock_llm_service.categorize_transaction.side_effect = ["Income", "Shopping"]
            
            parser = UniversalLLMParser()
            result = parser.parse_statement(mock_pdf_text, "Federal Bank")
            
            # Verify output format standardization
            assert isinstance(result, list)
            
            for transaction in result:
                # Required fields
                assert "date" in transaction
                assert "description" in transaction
                assert "amount" in transaction
                assert "category" in transaction
                assert "categorization_method" in transaction
                
                # Data types
                assert isinstance(transaction["date"], str)
                assert isinstance(transaction["description"], str)
                assert isinstance(transaction["amount"], (int, float))
                assert isinstance(transaction["category"], str)
                assert isinstance(transaction["categorization_method"], str)
                
                # Amount should be numeric
                assert transaction["amount"] != ""
                assert transaction["amount"] is not None

    @patch.dict(os.environ, {'ENABLE_LLM_PARSING': 'false'})
    def test_llm_disabled_fallback(self, mock_pdf_text):
        """Test behavior when LLM parsing is disabled via environment variable."""
        with patch('parsers.universal_llm_parser.extract_federal_bank_savings') as mock_traditional_parser:
            mock_traditional_parser.return_value = [
                {
                    "date": "01/05/2024",
                    "description": "TEST TRANSACTION",
                    "amount": 1000.00,
                    "type": "credit"
                }
            ]
            
            # Mock LLM service for categorization only
            with patch('parsers.universal_llm_parser.LLMService') as mock_llm_service_class:
                mock_llm_service = Mock()
                mock_llm_service.categorize_transaction.return_value = "Income"
                mock_llm_service_class.return_value = mock_llm_service
                
                parser = UniversalLLMParser()
                result = parser.parse_statement(mock_pdf_text, "Federal Bank")
                
                # Verify traditional parser was used
                mock_traditional_parser.assert_called_once()
                
                # Verify LLM parsing was not attempted
                mock_llm_service.parse_bank_statement.assert_not_called()
                
                # Verify categorization still works
                mock_llm_service.categorize_transaction.assert_called_once()

    def test_bank_parser_mapping(self):
        """Test correct parser selection for different banks."""
        parser = UniversalLLMParser()
        
        # Test parser mapping
        test_cases = [
            ("Federal Bank", "federal_bank_parser", "extract_federal_bank_savings"),
            ("HDFC Bank", "hdfc_savings", "extract_hdfc_savings"),
            ("HDFC", "hdfc_savings", "extract_hdfc_savings"),
            ("Unknown Bank", "generic", "extract_generic_transactions")
        ]
        
        for bank_name, expected_module, expected_function in test_cases:
            module, function = parser._get_fallback_parser(bank_name, "savings")
            assert module == expected_module
            assert function == expected_function

    def test_error_handling(self, mock_pdf_text):
        """Test comprehensive error handling."""
        with patch('parsers.universal_llm_parser.LLMService') as mock_llm_service_class:
            # Test LLM service initialization failure
            mock_llm_service_class.side_effect = Exception("LLM service init failed")
            
            with patch('parsers.universal_llm_parser.extract_federal_bank_savings') as mock_traditional_parser:
                mock_traditional_parser.return_value = []
                
                parser = UniversalLLMParser()
                result = parser.parse_statement(mock_pdf_text, "Federal Bank")
                
                # Should fallback gracefully
                assert isinstance(result, list)


class TestUniversalParserFunctions:
    """Test module-level functions."""

    @patch('parsers.universal_llm_parser.UniversalLLMParser')
    def test_parse_bank_statement_function(self, mock_parser_class):
        """Test the parse_bank_statement convenience function."""
        mock_parser = Mock()
        mock_parser.parse_statement.return_value = [{"test": "transaction"}]
        mock_parser_class.return_value = mock_parser
        
        result = parse_bank_statement("test pdf text", "Federal Bank", enable_llm=True)
        
        # Verify parser was created and called
        mock_parser_class.assert_called_once()
        mock_parser.parse_statement.assert_called_once_with("test pdf text", "Federal Bank")
        
        assert result == [{"test": "transaction"}]

    @patch('parsers.universal_llm_parser.UniversalLLMParser')
    def test_parse_bank_statement_with_llm_disabled(self, mock_parser_class):
        """Test parse_bank_statement with LLM disabled."""
        mock_parser = Mock()
        mock_parser.parse_statement.return_value = [{"test": "transaction"}]
        mock_parser_class.return_value = mock_parser
        
        with patch.dict(os.environ, {'ENABLE_LLM_PARSING': 'false'}):
            result = parse_bank_statement("test pdf text", "Federal Bank", enable_llm=False)
            
            # Should still work but with LLM disabled
            assert result == [{"test": "transaction"}]

    def test_factory_functions(self):
        """Test backward compatibility factory functions."""
        from parsers.universal_llm_parser import (
            parse_federal_bank_statement_llm,
            parse_hdfc_statement_llm
        )
        
        with patch('parsers.universal_llm_parser.parse_bank_statement') as mock_parse:
            mock_parse.return_value = [{"test": "transaction"}]
            
            # Test Federal Bank factory function
            result = parse_federal_bank_statement_llm("test pdf text")
            mock_parse.assert_called_with("test pdf text", "Federal Bank", enable_llm=True)
            assert result == [{"test": "transaction"}]
            
            # Test HDFC factory function
            result = parse_hdfc_statement_llm("test pdf text", account_type="savings")
            mock_parse.assert_called_with("test pdf text", "HDFC Bank", enable_llm=True)
            assert result == [{"test": "transaction"}]


class TestIntegrationScenarios:
    """Test real-world integration scenarios."""

    @patch('parsers.universal_llm_parser.LLMService')
    def test_mixed_success_failure_scenario(self, mock_llm_service_class, mock_pdf_text):
        """Test scenario where LLM parsing succeeds but some categorizations fail."""
        mock_llm_service = Mock()
        mock_llm_service_class.return_value = mock_llm_service
        
        # LLM parsing succeeds
        mock_llm_service.parse_bank_statement.return_value = {
            "transactions": [
                {
                    "date": "01/05/2024",
                    "description": "SALARY PAYMENT",
                    "amount": 50000.00,
                    "transaction_type": "credit"
                },
                {
                    "date": "02/05/2024",
                    "description": "STARBUCKS COFFEE",
                    "amount": -450.00,
                    "transaction_type": "debit"
                }
            ]
        }
        
        # Mixed categorization results
        mock_llm_service.categorize_transaction.side_effect = [
            "Income",  # Success
            LLMServiceError("Categorization failed")  # Failure
        ]
        
        parser = UniversalLLMParser()
        result = parser.parse_statement(mock_pdf_text, "Federal Bank")
        
        assert len(result) == 2
        assert result[0]["category"] == "Income"
        assert result[1]["category"] == "Other"  # Fallback category

    def test_performance_logging(self, mock_pdf_text):
        """Test that performance metrics are logged."""
        with patch('parsers.universal_llm_parser.LLMService') as mock_llm_service_class:
            mock_llm_service = Mock()
            mock_llm_service.parse_bank_statement.return_value = {"transactions": []}
            mock_llm_service_class.return_value = mock_llm_service
            
            parser = UniversalLLMParser()
            
            # Capture log messages
            with patch.object(parser.logger, 'info') as mock_log:
                result = parser.parse_statement(mock_pdf_text, "Federal Bank")
                
                # Verify performance logging occurred
                log_calls = [call.args[0] for call in mock_log.call_args_list]
                performance_logs = [log for log in log_calls if "duration" in log.lower()]
                assert len(performance_logs) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 