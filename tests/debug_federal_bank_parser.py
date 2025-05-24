#!/usr/bin/env python3
"""
Script to test and debug Federal Bank parser with actual statement
"""

import os
import sys
import json
from datetime import datetime
from pprint import pprint

# Add the parent directory to the path to import from the parsers package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from parsers.federal_bank import extract_federal_bank_savings, detect_federal_bank_savings

def main():
    """Main function to test the Federal Bank parser"""
    # Path to the Federal Bank statement PDF
    statement_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Federal_Bank_Decrypted.pdf")
    
    # Check if the file exists
    if not os.path.exists(statement_path):
        print(f"Error: File not found at {statement_path}")
        return
    
    # Test if the file is detected as a Federal Bank statement
    is_federal = detect_federal_bank_savings(statement_path)
    print(f"Is Federal Bank statement: {is_federal}")
    
    # Extract transactions
    print(f"Extracting transactions from {statement_path}...")
    transactions = extract_federal_bank_savings(statement_path)
    
    # Print the results
    print(f"Extracted {len(transactions)} transactions")
    
    if transactions:
        print("\nSample transactions:")
        for i, tx in enumerate(transactions[:5]):  # Show first 5 transactions
            print(f"\nTransaction {i+1}:")
            pprint(tx)
        
        # Save to a JSON file for inspection in test_results folder
        test_results_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_results")
        os.makedirs(test_results_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(test_results_dir, f"federal_bank_debug_{timestamp}.json")
        with open(output_path, 'w') as f:
            json.dump(transactions, f, indent=2)
        print(f"\nAll transactions saved to {output_path}")

if __name__ == "__main__":
    main()
