"""
Test script for the Federal Bank parser
"""

import os
import sys
import json
import argparse
from datetime import datetime

# Add parent directory to path to import parsers
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.federal_bank_parser import detect_federal_bank_savings, extract_federal_bank_savings

def test_parser(pdf_path, verbose=False, update_db=False):
    """
    Test the Federal Bank parser with a PDF statement
    
    Args:
        pdf_path (str): Path to the PDF statement file
        verbose (bool): Whether to print detailed output
        update_db (bool): Whether to update the transactions database
    """
    print(f"Testing Federal Bank parser with file: {pdf_path}")
    
    # First, check if this is a Federal Bank statement
    is_federal_bank = detect_federal_bank_savings(pdf_path)
    print(f"Is Federal Bank statement: {is_federal_bank}")
    
    if not is_federal_bank:
        print("This doesn't appear to be a Federal Bank statement.")
        return
    
    # Extract transactions
    print("Extracting transactions...")
    transactions = extract_federal_bank_savings(pdf_path)
    
    # Print summary
    print(f"\nExtracted {len(transactions)} transactions")
    
    if transactions:
        # Get date range
        dates = sorted(set(tx["date"] for tx in transactions))
        if dates:
            print(f"Date range: {dates[0]} to {dates[-1]}")
        
        # Count credits and debits
        credits = sum(1 for tx in transactions if tx["type"] == "credit")
        debits = sum(1 for tx in transactions if tx["type"] == "debit")
        print(f"Credits: {credits}, Debits: {debits}")
        
        # Calculate total amounts
        total_credits = sum(tx["amount"] for tx in transactions if tx["type"] == "credit")
        total_debits = sum(abs(tx["amount"]) for tx in transactions if tx["type"] == "debit")
        print(f"Total credits: {total_credits:.2f}, Total debits: {total_debits:.2f}")
        
        # Print sample transactions
        if verbose:
            print("\nSample transactions:")
            for i, tx in enumerate(transactions[:5]):
                print(f"{i+1}. {tx['date']} - {tx['description']} - {tx['amount']:.2f} - {tx['type']}")
            
            if len(transactions) > 5:
                print(f"... and {len(transactions) - 5} more transactions")
        
        # Save to JSON file for inspection
        output_file = "federal_bank_transactions.json"
        with open(output_file, "w") as f:
            json.dump(transactions, f, indent=2)
        print(f"\nSaved all transactions to {output_file}")
        
        # Update the main database if requested
        if update_db:
            db_file = "data/transactions.json"
            try:
                if os.path.exists(db_file):
                    with open(db_file, "r") as f:
                        existing_transactions = json.load(f)
                else:
                    existing_transactions = []
                
                # Add new transactions
                existing_transactions.extend(transactions)
                
                # Save updated database
                with open(db_file, "w") as f:
                    json.dump(existing_transactions, f, indent=2)
                
                print(f"Updated transactions database with {len(transactions)} new transactions")
            except Exception as e:
                print(f"Error updating database: {str(e)}")
    else:
        print("No transactions were extracted.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test the Federal Bank parser")
    parser.add_argument("pdf_path", help="Path to the PDF statement file")
    parser.add_argument("--verbose", "-v", action="store_true", help="Print detailed output")
    parser.add_argument("--update-db", "-u", action="store_true", help="Update the transactions database")
    
    args = parser.parse_args()
    test_parser(args.pdf_path, args.verbose, args.update_db)
