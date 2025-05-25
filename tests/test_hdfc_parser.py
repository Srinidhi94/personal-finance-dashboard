#!/usr/bin/env python3
"""
HDFC Bank Statement Parser Test

This script tests the HDFC parser implementations to verify they correctly
parse transactions and properly identify deposits and withdrawals based on
reference numbers and balance changes.
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

from parsers.hdfc_savings import (
    detect_hdfc_savings,
    extract_hdfc_savings,
    parse_date,
    extract_statement_metadata
)

def test_detect_hdfc_savings():
    """Test statement detection"""
    with patch('fitz.open') as mock_open:
        # Set up mock for valid statement
        mock_doc = MagicMock()
        mock_page = MagicMock()
        mock_page.get_text.return_value = """
        HDFC BANK
        Statement of account
        Account No: 50100123456789
        000008308912572
        """
        mock_doc.__getitem__.return_value = mock_page
        mock_open.return_value = mock_doc
        
        assert detect_hdfc_savings("valid.pdf") == True
        
        # Test with invalid statement
        mock_page.get_text.return_value = "Not an HDFC Bank statement"
        assert detect_hdfc_savings("invalid.pdf") == False
        
        # Test with file error
        mock_open.side_effect = Exception("File error")
        assert detect_hdfc_savings("error.pdf") == False

def test_parse_date():
    """Test date parsing function"""
    # Test DD/MM/YY format
    assert parse_date("01/05/25") == "01/05/2025"
    
    # Test invalid date
    assert parse_date("invalid") is None

def test_extract_statement_metadata(mock_hdfc_doc):
    """Test metadata extraction"""
    metadata = extract_statement_metadata(mock_hdfc_doc)
    
    assert isinstance(metadata, dict)
    assert metadata["account_holder"] == "SRINIDH R"  # Match the mock data
    assert metadata["account_num"] == "50100123456789"
    assert metadata["branch"] == "HENNUR ROAD"
    assert metadata["opening_balance"] == 10000.00
    assert metadata["closing_balance"] == None  # Opening/closing balances are now handled differently

def test_extract_transactions(mock_hdfc_doc):
    """Test transaction extraction"""
    with patch('fitz.open', return_value=mock_hdfc_doc):
        transactions = extract_hdfc_savings("test.pdf")
        
        assert isinstance(transactions, list)
        assert len(transactions) == 9  # Opening balance + 8 transactions
        
        # Check opening balance
        assert transactions[0]["type"] == "balance"
        assert transactions[0]["balance"] == 10000.00
        assert transactions[0]["amount"] == 0
        
        # Check first transaction
        assert transactions[1]["date"] == "10/05/2025"
        assert transactions[1]["reference"] == "000008308912572"
        assert transactions[1]["description"] == "ACH D-ZERODHA BROKING"
        assert transactions[1]["amount"] == 4500.00
        assert transactions[1]["balance"] == 14500.00
        assert transactions[1]["type"] == "credit"
        
        # Check last transaction
        assert transactions[-1]["date"] == "12/05/2025"
        assert transactions[-1]["reference"] == "000008308258310"
        assert transactions[-1]["description"] == "ACH D-ZERODHA BROKING"
        assert transactions[-1]["amount"] == 6500.00
        assert transactions[-1]["balance"] == 82693.00
        assert transactions[-1]["type"] == "credit"

@pytest.fixture
def mock_hdfc_doc(mock_hdfc_text):
    """Mock HDFC PDF document"""
    mock_doc = MagicMock()
    mock_page = MagicMock()
    mock_page.get_text.return_value = mock_hdfc_text
    mock_doc.__getitem__.return_value = mock_page
    mock_doc.__len__.return_value = 1
    return mock_doc
