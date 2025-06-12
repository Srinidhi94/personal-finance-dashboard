#!/usr/bin/env python3

"""
Comprehensive parser tests for Personal Finance Dashboard
Tests all bank statement parsers for accuracy and reliability
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
import os
import sys

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.federal_bank_parser import (
    detect_federal_bank_savings,
    extract_federal_bank_savings,
    parse_date,
    extract_statement_metadata
)
from parsers.hdfc_savings import (
    detect_hdfc_savings,
    extract_hdfc_savings
)


@pytest.fixture
def mock_federal_bank_pdf():
    """Mock Federal Bank PDF document for testing."""
    mock_doc = MagicMock()
    mock_page = MagicMock()
    mock_page.get_text.return_value = """
    SAVINGS A/C NO: 12345678901
    FDRL
    Statement Period: 01 May 2024 to 31 May 2024
    
    Opening Balance
    on 01 May 2024
    ₹10,000.00
    
    01 May
    UPI/CR/123456/PAY
    5,000.00
    15,000.00
    
    02 May
    POS/DEBIT CARD/SHOP
    1,500.00
    13,500.00
    
    03 May
    NEFT/CR/SALARY
    50,000.00
    63,500.00
    """
    mock_doc.__getitem__.return_value = mock_page
    mock_doc.__len__.return_value = 1
    return mock_doc


@pytest.fixture
def mock_hdfc_pdf():
    """Mock HDFC PDF document for testing."""
    mock_doc = MagicMock()
    mock_page = MagicMock()
    mock_page.get_text.return_value = """
    HDFC BANK
    SAVINGS ACCOUNT STATEMENT
    Account Number: 12345678901
    
    Date        Description                     Debit       Credit      Balance
    01/05/2024  Opening Balance                                         10,000.00
    01/05/2024  UPI-PAYMENT                     500.00                  9,500.00
    02/05/2024  SALARY CREDIT                               50,000.00   59,500.00
    03/05/2024  ATM WITHDRAWAL                  2,000.00                57,500.00
    """
    mock_doc.__getitem__.return_value = mock_page
    mock_doc.__len__.return_value = 1
    return mock_doc


class TestFederalBankParser:
    """Test Federal Bank statement parser."""
    
    def test_detect_federal_bank_savings(self):
        """Test Federal Bank statement detection."""
        with patch('fitz.open') as mock_open:
            # Test valid statement
            mock_doc = MagicMock()
            mock_page = MagicMock()
            mock_page.get_text.return_value = "SAVINGS A/C NO\nFDRL\nTransaction Details\nOpening Balance"
            mock_doc.__getitem__.return_value = mock_page
            mock_open.return_value = mock_doc
            
            assert detect_federal_bank_savings("valid.pdf") == True
            
            # Test invalid statement
            mock_page.get_text.return_value = "Not a Federal Bank statement"
            assert detect_federal_bank_savings("invalid.pdf") == False
            
            # Test file error
            mock_open.side_effect = Exception("File error")
            assert detect_federal_bank_savings("error.pdf") == False
    
    def test_parse_date(self):
        """Test date parsing function."""
        # Test DD/MM/YYYY format
        assert parse_date("01/05/2024", 2024) == "01/05/2024"
        
        # Test DD MMM format
        assert parse_date("01 May", 2024) == "01/05/2024"
        
        # Test invalid date
        assert parse_date("invalid", 2024) is None
    
    def test_extract_statement_metadata(self, mock_federal_bank_pdf):
        """Test metadata extraction."""
        metadata = extract_statement_metadata(mock_federal_bank_pdf)
        
        assert isinstance(metadata, dict)
        assert metadata["statement_year"] == 2024
        assert "account_holder" in metadata
        assert metadata["account_num"] == "12345678901"
    
    def test_extract_federal_bank_transactions(self):
        """Test Federal Bank transaction extraction."""
        with patch('fitz.open') as mock_open:
            mock_doc = MagicMock()
            mock_page = MagicMock()
            mock_page.get_text.return_value = """
            SAVINGS A/C NO: 12345678901
            Statement Period: 01 May 2024 to 31 May 2024
            
            Opening Balance
            on 01 May 2024
            ₹10,000.00
            
            01 May
            UPI/CR/123456/PAY
            5,000.00
            15,000.00
            
            02 May
            POS/DEBIT CARD/SHOP
            1,500.00
            13,500.00
            
            03 May
            NEFT/CR/SALARY
            50,000.00
            63,500.00
            """
            mock_doc.__getitem__.return_value = mock_page
            mock_doc.__len__.return_value = 1
            mock_open.return_value = mock_doc
            
            transactions = extract_federal_bank_savings("test.pdf")
            
            assert isinstance(transactions, list)
            assert len(transactions) >= 3  # At least 3 transactions
            
            # Check transaction structure
            for tx in transactions:
                if tx["type"] != "balance":
                    assert "date" in tx
                    assert "description" in tx
                    assert "amount" in tx
                    assert "type" in tx
                    assert "balance" in tx
    
    def test_federal_bank_transaction_patterns(self):
        """Test recognition of different Federal Bank transaction patterns."""
        with patch('fitz.open') as mock_open:
            mock_doc = MagicMock()
            mock_page = MagicMock()
            mock_page.get_text.return_value = """
            Statement Period: 01 May 2024 to 31 May 2024
            
            Opening Balance
            on 01 May 2024
            ₹10,000.00
            
            01 May
            POS/DEBIT CARD/SHOP
            100.00
            9,900.00
            
            01 May
            UPI/CR/123456/PAY
            200.00
            10,100.00
            
            02 May
            NEFT/CR/SALARY
            5,000.00
            15,100.00
            
            02 May
            IMPS/DR/TRANSFER
            1,000.00
            14,100.00
            """
            mock_doc.__getitem__.return_value = mock_page
            mock_doc.__len__.return_value = 1
            mock_open.return_value = mock_doc
            
            transactions = extract_federal_bank_savings("test.pdf")
            
            # Count transaction types
            patterns = {"POS": 0, "UPI": 0, "NEFT": 0, "IMPS": 0}
            
            for tx in transactions:
                if tx["type"] == "balance":
                    continue
                desc = tx["description"]
                if "POS/" in desc:
                    patterns["POS"] += 1
                elif "UPI/" in desc:
                    patterns["UPI"] += 1
                elif "NEFT/" in desc:
                    patterns["NEFT"] += 1
                elif "IMPS/" in desc:
                    patterns["IMPS"] += 1
            
            assert patterns["POS"] >= 1
            assert patterns["UPI"] >= 1
            assert patterns["NEFT"] >= 1
            assert patterns["IMPS"] >= 1


class TestHDFCParser:
    """Test HDFC Bank statement parser."""
    
    def test_detect_hdfc_savings(self):
        """Test HDFC statement detection."""
        with patch('fitz.open') as mock_open:
            # Test valid statement
            mock_doc = MagicMock()
            mock_page = MagicMock()
            mock_page.get_text.return_value = "HDFC BANK\nSAVINGS ACCOUNT STATEMENT\nAccount Number"
            mock_doc.__getitem__.return_value = mock_page
            mock_open.return_value = mock_doc
            
            assert detect_hdfc_savings("valid.pdf") == True
            
            # Test invalid statement
            mock_page.get_text.return_value = "Not an HDFC statement"
            assert detect_hdfc_savings("invalid.pdf") == False
            
            # Test file error
            mock_open.side_effect = Exception("File error")
            assert detect_hdfc_savings("error.pdf") == False
    
    def test_extract_hdfc_transactions(self):
        """Test HDFC transaction extraction."""
        with patch('fitz.open') as mock_open:
            mock_doc = MagicMock()
            mock_page = MagicMock()
            mock_page.get_text.return_value = """
            HDFC BANK
            SAVINGS ACCOUNT STATEMENT
            Account Number: 12345678901
            
            Date        Description                     Debit       Credit      Balance
            01/05/2024  Opening Balance                                         10,000.00
            01/05/2024  UPI-PAYMENT                     500.00                  9,500.00
            02/05/2024  SALARY CREDIT                               50,000.00   59,500.00
            03/05/2024  ATM WITHDRAWAL                  2,000.00                57,500.00
            """
            mock_doc.__getitem__.return_value = mock_page
            mock_doc.__len__.return_value = 1
            mock_open.return_value = mock_doc
            
            transactions = extract_hdfc_savings("test.pdf")
            
            assert isinstance(transactions, list)
            assert len(transactions) >= 3  # At least 3 transactions
            
            # Check transaction structure
            for tx in transactions:
                assert "date" in tx
                assert "description" in tx
                assert "amount" in tx
                assert "type" in tx
                assert "balance" in tx
            
            # Check for both credits and debits
            credits = [tx for tx in transactions if tx['amount'] > 0]
            debits = [tx for tx in transactions if tx['amount'] < 0]
            
            assert len(credits) > 0, "No credit transactions found"
            assert len(debits) > 0, "No debit transactions found"
    
    def test_hdfc_transaction_patterns(self):
        """Test recognition of different HDFC transaction patterns."""
        with patch('fitz.open') as mock_open:
            mock_doc = MagicMock()
            mock_page = MagicMock()
            mock_page.get_text.return_value = """
            HDFC BANK
            SAVINGS ACCOUNT STATEMENT
            
            Date        Description                     Debit       Credit      Balance
            01/05/2024  UPI-PAYMENT                     500.00                  9,500.00
            01/05/2024  NEFT-SALARY                                 50,000.00   59,500.00
            02/05/2024  ATM WITHDRAWAL                  2,000.00                57,500.00
            02/05/2024  IMPS-TRANSFER                   1,000.00                56,500.00
            03/05/2024  POS-PURCHASE                    800.00                  55,700.00
            """
            mock_doc.__getitem__.return_value = mock_page
            mock_doc.__len__.return_value = 1
            mock_open.return_value = mock_doc
            
            transactions = extract_hdfc_savings("test.pdf")
            
            # Count transaction types
            patterns = {"UPI": 0, "NEFT": 0, "ATM": 0, "IMPS": 0, "POS": 0}
            
            for tx in transactions:
                desc = tx["description"].upper()
                if "UPI" in desc:
                    patterns["UPI"] += 1
                elif "NEFT" in desc:
                    patterns["NEFT"] += 1
                elif "ATM" in desc:
                    patterns["ATM"] += 1
                elif "IMPS" in desc:
                    patterns["IMPS"] += 1
                elif "POS" in desc:
                    patterns["POS"] += 1
            
            assert patterns["UPI"] >= 1
            assert patterns["NEFT"] >= 1
            assert patterns["ATM"] >= 1
            assert patterns["IMPS"] >= 1
            assert patterns["POS"] >= 1


class TestParserErrorHandling:
    """Test error handling in parsers."""
    
    def test_federal_bank_error_handling(self):
        """Test Federal Bank parser error handling."""
        # Test with file error
        with patch('fitz.open', side_effect=Exception("File error")):
            transactions = extract_federal_bank_savings("error.pdf")
            assert transactions == []
        
        # Test with invalid date
        assert parse_date("invalid_date", 2024) is None
    
    def test_hdfc_error_handling(self):
        """Test HDFC parser error handling."""
        # Test with file error
        with patch('fitz.open', side_effect=Exception("File error")):
            transactions = extract_hdfc_savings("error.pdf")
            assert transactions == []


class TestParserIntegration:
    """Test parser integration with the main application."""
    
    def test_parser_output_format(self):
        """Test that parser output matches expected format."""
        with patch('fitz.open') as mock_open:
            mock_doc = MagicMock()
            mock_page = MagicMock()
            mock_page.get_text.return_value = """
            HDFC BANK
            SAVINGS ACCOUNT STATEMENT
            
            Date        Description                     Debit       Credit      Balance
            01/05/2024  UPI-PAYMENT                     500.00                  9,500.00
            02/05/2024  SALARY CREDIT                               50,000.00   59,500.00
            """
            mock_doc.__getitem__.return_value = mock_page
            mock_doc.__len__.return_value = 1
            mock_open.return_value = mock_doc
            
            transactions = extract_hdfc_savings("test.pdf")
            
            # Check that output format matches what the app expects
            for tx in transactions:
                # Required fields for app integration
                assert isinstance(tx["date"], str)
                assert isinstance(tx["description"], str)
                assert isinstance(tx["amount"], (int, float))
                assert tx["type"] in ["credit", "debit"]
                assert isinstance(tx["balance"], (int, float))
    
    def test_parser_data_consistency(self):
        """Test that parser data is consistent and valid."""
        with patch('fitz.open') as mock_open:
            mock_doc = MagicMock()
            mock_page = MagicMock()
            mock_page.get_text.return_value = """
            SAVINGS A/C NO: 12345678901
            Statement Period: 01 May 2024 to 31 May 2024
            
            Opening Balance
            on 01 May 2024
            ₹10,000.00
            
            01 May
            UPI/CR/123456/PAY
            5,000.00
            15,000.00
            
            02 May
            POS/DEBIT CARD/SHOP
            1,500.00
            13,500.00
            """
            mock_doc.__getitem__.return_value = mock_page
            mock_doc.__len__.return_value = 1
            mock_open.return_value = mock_doc
            
            transactions = extract_federal_bank_savings("test.pdf")
            
            # Check balance consistency
            for i, tx in enumerate(transactions):
                if tx["type"] == "balance":
                    continue
                
                # Balance should be a valid number
                assert isinstance(tx["balance"], (int, float))
                assert tx["balance"] >= 0  # Assuming no negative balances in test data
                
                # Amount should be consistent with transaction type
                if tx["type"] == "credit":
                    assert tx["amount"] > 0
                elif tx["type"] == "debit":
                    assert tx["amount"] < 0


if __name__ == '__main__':
    pytest.main([__file__, '-v']) 