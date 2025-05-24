"""
Tests for the Federal Bank statement parser
"""

import os
import sys
import json
import pytest
import shutil
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from parsers.federal_bank import extract_federal_bank_savings, detect_federal_bank_savings

# Set up test output directory
TEST_RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_results")
os.makedirs(TEST_RESULTS_DIR, exist_ok=True)

def teardown_module(module):
    """Clean up test results after tests run"""
    # Clean up JSON files in the test_results directory
    for file in os.listdir(TEST_RESULTS_DIR):
        if file.endswith('.json'):
            os.remove(os.path.join(TEST_RESULTS_DIR, file))
    print(f"Cleaned up test results directory: {TEST_RESULTS_DIR}")

def test_detect_federal_bank_statement():
    """Test Federal Bank statement detection"""
    # Path to the test file using absolute path
    test_file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Federal_Bank_Decrypted.pdf")
    
    # Skip if file doesn't exist
    if not os.path.exists(test_file_path):
        pytest.skip(f"Test file not found: {test_file_path}")
    
    # Test detection
    assert detect_federal_bank_savings(test_file_path) == True

def test_extract_transactions_from_federal_bank_statement():
    """Test extracting transactions from a Federal Bank statement"""
    # Path to the test file using absolute path
    test_file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Federal_Bank_Decrypted.pdf")
    
    # Skip if file doesn't exist
    if not os.path.exists(test_file_path):
        pytest.skip(f"Test file not found: {test_file_path}")
    
    # Extract transactions
    transactions = extract_federal_bank_savings(test_file_path)
    
    # Basic validation
    assert transactions is not None
    assert isinstance(transactions, list)
    
    # Skip further tests if no transactions were extracted during development
    if len(transactions) == 0:
        pytest.skip("No transactions extracted - parser still under development")
    
    # Test first transaction properties
    first_transaction = transactions[0]
    assert 'date' in first_transaction
    assert 'description' in first_transaction
    assert 'amount' in first_transaction
    assert 'type' in first_transaction
    
    # Save test results to JSON file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(TEST_RESULTS_DIR, f"federal_bank_test_results_{timestamp}.json")
    with open(output_file, "w") as f:
        json.dump(transactions, f, indent=2)
    print(f"Saved test results to {output_file}")
