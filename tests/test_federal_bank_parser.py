"""
Test script for the Federal Bank parser

This test verifies that the parser correctly identifies transactions and their types
based on transaction patterns and balance changes.
"""

import os
import sys
import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Add parent directory to path to import parsers
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.federal_bank_parser import (
    detect_federal_bank_savings,
    extract_federal_bank_savings,
    parse_date,
    extract_statement_metadata
)

@pytest.fixture
def mock_pdf_text():
    """Mock PDF text content"""
    return """
    Statement Period: 01 May 2024 to 31 May 2024
    SAVINGS A/C NO: 12345678901
    IFSC: FDRL0123456
    Transaction Details
    Opening Balance
    on 01 May 2024
    ₹10,000.00
    
    01 May
    UPI/CR/123456789/CREDIT
    5,000.00
    15,000.00
    
    02 May
    POS/DEBIT CARD/AMAZON
    1,500.00
    13,500.00
    
    03 May
    NEFT/CR/SALARY/COMPANY
    50,000.00
    63,500.00
    
    Closing Balance
    on 31 May 2024
    ₹63,500.00
    """

@pytest.fixture
def mock_pdf_doc(mock_pdf_text):
    """Mock PDF document"""
    mock_doc = MagicMock()
    mock_page = MagicMock()
    mock_page.get_text.return_value = mock_pdf_text
    mock_doc.__getitem__.return_value = mock_page
    mock_doc.__len__.return_value = 1
    return mock_doc

def test_detect_federal_bank_savings():
    """Test statement detection"""
    with patch('fitz.open') as mock_open:
        # Set up mock for valid statement
        mock_doc = MagicMock()
        mock_page = MagicMock()
        mock_page.get_text.return_value = "SAVINGS A/C NO\nFDRL\nTransaction Details\nOpening Balance"
        mock_doc.__getitem__.return_value = mock_page
        mock_open.return_value = mock_doc
        
        assert detect_federal_bank_savings("valid.pdf") == True
        
        # Test with invalid statement
        mock_page.get_text.return_value = "Not a Federal Bank statement"
        assert detect_federal_bank_savings("invalid.pdf") == False
        
        # Test with file error
        mock_open.side_effect = Exception("File error")
        assert detect_federal_bank_savings("error.pdf") == False

def test_parse_date():
    """Test date parsing function"""
    # Test DD/MM/YYYY format
    assert parse_date("01/05/2024", 2024) == "01/05/2024"
    
    # Test DD MMM format
    assert parse_date("01 May", 2024) == "01/05/2024"
    
    # Test invalid date
    assert parse_date("invalid", 2024) is None

def test_extract_statement_metadata(mock_pdf_doc):
    """Test metadata extraction"""
    metadata = extract_statement_metadata(mock_pdf_doc)
    
    assert isinstance(metadata, dict)
    assert metadata["statement_year"] == 2024
    assert "account_holder" in metadata
    assert metadata["account_num"] == "12345678901"

def test_extract_transactions():
    """Test transaction extraction"""
    with patch('fitz.open') as mock_open:
        # Set up mock
        mock_doc = MagicMock()
        mock_page = MagicMock()
        mock_page.get_text.return_value = """
        Statement Period: 01 May 2024 to 31 May 2024
        
        Opening Balance
        on 01 May 2024
        ₹10,000.00
        
        01 May
        UPI/CR/123456789/CREDIT
        5,000.00
        15,000.00
        
        02 May
        POS/DEBIT CARD/AMAZON
        1,500.00
        13,500.00
        """
        mock_doc.__getitem__.return_value = mock_page
        mock_doc.__len__.return_value = 1
        mock_open.return_value = mock_doc
        
        transactions = extract_federal_bank_savings("test.pdf")
        
        assert isinstance(transactions, list)
        assert len(transactions) == 3  # Opening balance + 2 transactions
        
        # Check opening balance
        assert transactions[0]["type"] == "balance"
        assert transactions[0]["balance"] == 10000.00
        
        # Check credit transaction
        assert transactions[1]["type"] == "credit"
        assert transactions[1]["amount"] == 5000.00
        assert transactions[1]["balance"] == 15000.00
        
        # Check debit transaction
        assert transactions[2]["type"] == "debit"
        assert transactions[2]["amount"] == -1500.00
        assert transactions[2]["balance"] == 13500.00

def test_transaction_patterns():
    """Test recognition of different transaction patterns"""
    with patch('fitz.open') as mock_open:
        # Set up mock with various transaction types
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
        900.00
        
        01 May
        UPI/CR/123456/PAY
        200.00
        1100.00
        
        02 May
        NEFT/CR/SALARY
        5000.00
        6100.00
        
        02 May
        IMPS/DR/TRANSFER
        1000.00
        5100.00
        
        03 May
        TO INTL/PAYMENT
        500.00
        4600.00
        
        03 May
        Visa Other Chrgs
        50.00
        4550.00
        """
        mock_doc.__getitem__.return_value = mock_page
        mock_doc.__len__.return_value = 1
        mock_open.return_value = mock_doc
        
        transactions = extract_federal_bank_savings("test.pdf")
        
        # Count transaction types
        patterns = {
            "POS": 0,
            "UPI": 0,
            "NEFT": 0,
            "IMPS": 0,
            "INTL": 0,
            "VISA": 0
        }
        
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
            elif "TO INTL" in desc:
                patterns["INTL"] += 1
            elif "Visa Other" in desc:
                patterns["VISA"] += 1
        
        assert patterns["POS"] == 1
        assert patterns["UPI"] == 1
        assert patterns["NEFT"] == 1
        assert patterns["IMPS"] == 1
        assert patterns["INTL"] == 1
        assert patterns["VISA"] == 1

def test_error_handling():
    """Test error handling in parser"""
    # Test with file error
    with patch('fitz.open', side_effect=Exception("File error")):
        transactions = extract_federal_bank_savings("error.pdf")
        assert transactions == []
    
    # Test with invalid date
    assert parse_date("invalid_date", 2024) is None

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=parsers.federal_bank_parser"])
