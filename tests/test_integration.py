"""
Integration tests for the personal finance dashboard

These tests simulate actual file uploads and processing, using real PDF files
from the uploads directory.
"""

import os
import sys
import json
import shutil
import pytest
from datetime import datetime

# Add parent directory to path to import parsers
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.federal_bank_parser import extract_federal_bank_savings, detect_federal_bank_savings
from parsers.hdfc_savings import extract_hdfc_savings, detect_hdfc_savings

# Constants
UPLOADS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
TEST_RESULTS_DIR = os.path.join(os.path.dirname(__file__), "test_results")

def setup_module():
    """Set up test environment before running tests"""
    # Create test_results directory if it doesn't exist
    os.makedirs(TEST_RESULTS_DIR, exist_ok=True)
    
    # Clean up old test results
    for file in os.listdir(TEST_RESULTS_DIR):
        if file != ".gitkeep":  # Keep the .gitkeep file
            os.remove(os.path.join(TEST_RESULTS_DIR, file))

def teardown_module():
    """Clean up after tests"""
    # Clean up test results
    for file in os.listdir(TEST_RESULTS_DIR):
        if file != ".gitkeep":  # Keep the .gitkeep file
            os.remove(os.path.join(TEST_RESULTS_DIR, file))

def save_test_results(filename, data):
    """Save test results to JSON file"""
    output_path = os.path.join(TEST_RESULTS_DIR, filename)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, default=str, ensure_ascii=False)
    return output_path

def test_federal_bank_statement():
    """Test processing a Federal Bank statement from uploads"""
    # Find Federal Bank statement in uploads
    federal_bank_file = None
    for file in os.listdir(UPLOADS_DIR):
        if file.startswith("Federal_Bank") and file.endswith(".pdf"):
            federal_bank_file = os.path.join(UPLOADS_DIR, file)
            break
    
    assert federal_bank_file is not None, "No Federal Bank statement found in uploads directory"
    
    # Test detection
    assert detect_federal_bank_savings(federal_bank_file), "Failed to detect Federal Bank statement"
    
    # Extract transactions
    transactions = extract_federal_bank_savings(federal_bank_file)
    assert len(transactions) > 0, "No transactions extracted from Federal Bank statement"
    
    # Validate transaction structure
    for tx in transactions:
        assert "date" in tx, "Transaction missing date"
        assert "description" in tx, "Transaction missing description"
        assert "amount" in tx, "Transaction missing amount"
        assert "type" in tx, "Transaction missing type"
        assert "balance" in tx, "Transaction missing balance"
    
    # Calculate totals
    credits = sum(tx["amount"] for tx in transactions if tx["type"] == "credit")
    debits = sum(-tx["amount"] for tx in transactions if tx["type"] == "debit")
    
    # Save results
    results = {
        "statement_type": "Federal Bank Savings",
        "file_name": os.path.basename(federal_bank_file),
        "transaction_count": len(transactions),
        "credit_total": credits,
        "debit_total": debits,
        "transactions": transactions,
        "test_timestamp": datetime.now().isoformat()
    }
    
    output_file = save_test_results("federal_bank_test_results.json", results)
    assert os.path.exists(output_file), "Failed to save test results"
    
    # Verify results were saved
    with open(output_file, 'r', encoding='utf-8') as f:
        saved_results = json.load(f)
        assert saved_results["transaction_count"] == len(transactions), "Saved results don't match"

def test_hdfc_statement():
    """Test processing an HDFC statement from uploads"""
    # Find HDFC statement in uploads
    hdfc_file = None
    for file in os.listdir(UPLOADS_DIR):
        if file.startswith("Statement_Example") and file.endswith(".pdf"):
            hdfc_file = os.path.join(UPLOADS_DIR, file)
            break
    
    assert hdfc_file is not None, "No HDFC statement found in uploads directory"
    
    # Test detection
    assert detect_hdfc_savings(hdfc_file), "Failed to detect HDFC statement"
    
    # Extract transactions
    transactions = extract_hdfc_savings(hdfc_file)
    assert len(transactions) > 0, "No transactions extracted from HDFC statement"
    
    # Validate transaction structure
    for tx in transactions:
        assert "date" in tx, "Transaction missing date"
        assert "description" in tx, "Transaction missing description"
        assert "amount" in tx, "Transaction missing amount"
        assert "type" in tx, "Transaction missing type"
        assert "balance" in tx, "Transaction missing balance"
    
    # Calculate totals
    credits = sum(tx["amount"] for tx in transactions if tx["type"] == "credit")
    debits = sum(-tx["amount"] for tx in transactions if tx["type"] == "debit")
    
    # Save results
    results = {
        "statement_type": "HDFC Savings",
        "file_name": os.path.basename(hdfc_file),
        "transaction_count": len(transactions),
        "credit_total": credits,
        "debit_total": debits,
        "transactions": transactions,
        "test_timestamp": datetime.now().isoformat()
    }
    
    output_file = save_test_results("hdfc_test_results.json", results)
    assert os.path.exists(output_file), "Failed to save test results"
    
    # Verify results were saved
    with open(output_file, 'r', encoding='utf-8') as f:
        saved_results = json.load(f)
        assert saved_results["transaction_count"] == len(transactions), "Saved results don't match"

if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 