#!/usr/bin/env python3
"""
HDFC Bank Statement Parser Test

This script tests the HDFC parser implementations to verify they correctly
parse transactions and properly identify deposits and withdrawals.
"""

import json
import sys
import os
import argparse
from datetime import datetime

# Add the parent directory to the path to import the parsers module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers import extract_transactions_from_file
from parsers.hdfc_savings import extract_hdfc_savings

def run_parser_test(pdf_path, output_file=None, verbose=False):
    """
    Test the HDFC Savings parser with the specified PDF file
    
    Args:
        pdf_path (str): Path to the PDF statement file
        output_file (str, optional): Path to save extracted transactions as JSON
        verbose (bool): Whether to print detailed information about transactions
        
    Returns:
        list: Extracted transactions
    """
    print(f"Testing bank statement parser...")
    print(f"Processing {pdf_path}...")

    # Extract transactions using the parser
    transactions = extract_hdfc_savings(pdf_path)

    # Count credits and debits
    credit_count = 0
    debit_count = 0
    for tx in transactions:
        if tx['amount'] > 0:
            credit_count += 1
            if verbose:
                print(f"CREDIT: {tx['date']} - {tx['description'][:40]} - Amount: {tx['amount']} - Balance: {tx['balance']}")
        else:
            debit_count += 1
            if verbose:
                print(f"DEBIT: {tx['date']} - {tx['description'][:40]} - Amount: {tx['amount']} - Balance: {tx['balance']}")

    # Show summary
    print(f"\nTotal transactions: {len(transactions)}")
    print(f"Credits (deposits): {credit_count}")
    print(f"Debits (withdrawals): {debit_count}")

    # Save to JSON if requested
    if output_file:
        with open(output_file, "w") as f:
            json.dump(transactions, f, indent=2)
        print(f"Saved transactions to {output_file}")
    
    return transactions

def update_transaction_database(transactions, output_file='data/transactions.json', backup=True):
    """
    Update the transaction database with new transactions
    
    Args:
        transactions (list): List of transactions to add to the database
        output_file (str): Path to the transaction database file
        backup (bool): Whether to create a backup before updating
    """
    # Create backup of existing transactions file
    if backup and os.path.exists(output_file):
        backup_file = f"{output_file}.backup"
        import shutil
        shutil.copy2(output_file, backup_file)
        print(f"Created backup of transaction database at {backup_file}")
    
    # Save transactions to output file
    with open(output_file, "w") as f:
        json.dump(transactions, f, indent=2)
    
    print(f"Updated transaction database at {output_file} with {len(transactions)} transactions")

def test_hdfc_parser():
    """
    Pytest compatible test for the HDFC parser
    """
    transactions = run_parser_test('uploads/Statement_Example.pdf', verbose=False)
    assert len(transactions) > 0
    # Check that we have both credits and debits
    credits = sum(1 for tx in transactions if tx['amount'] > 0)
    debits = sum(1 for tx in transactions if tx['amount'] < 0)
    assert credits > 0, "No credit transactions found"
    assert debits > 0, "No debit transactions found"
    
    
def main():
    """
    Main entry point for the parser test script
    """
    parser = argparse.ArgumentParser(description='Test bank statement parsers')
    parser.add_argument('pdf_file', help='Path to the bank statement PDF file to parse')
    parser.add_argument('--output', '-o', help='Path to save the parsed transactions as JSON')
    parser.add_argument('--update-db', '-u', action='store_true', help='Update the transaction database')
    parser.add_argument('--verbose', '-v', action='store_true', help='Print detailed transaction information')
    
    args = parser.parse_args()
    
    transactions = run_parser_test(args.pdf_file, args.output, args.verbose)
    
    if args.update_db:
        update_transaction_database(transactions)

if __name__ == "__main__":
    main()
