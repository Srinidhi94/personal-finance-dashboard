#!/usr/bin/env python3

"""
Test script that extracts transactions from a sample statement,
categorizes them, and displays the results in a nice format.
"""

import json
import os
from parsers import extract_transactions_from_file
from app import categorize_transaction, categorize_subcategory

def main():
    # Define colors for output
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'
    
    # Clear the screen
    print("\033c", end="")
    
    # Print header
    print(f"{BOLD}{BLUE}===== HDFC Statement Parser Tester ====={END}\n")
    
    # Sample statement path
    # Define the statement path
    sample_path = 'uploads/Statement_Example.pdf'
    print(f"{BOLD}Testing with:{END} {sample_path}\n")
    
    # Extract transactions
    print(f"{BOLD}{BLUE}Step 1: Extracting transactions...{END}")
    transactions = extract_transactions_from_file(sample_path, "HDFC", "savings", "HDFC Savings Account")
    
    print(f"\n{GREEN}Successfully extracted {len(transactions)} transactions.{END}\n")
    
    # Categorize transactions
    print(f"{BOLD}{BLUE}Step 2: Categorizing transactions...{END}\n")
    
    for i, tx in enumerate(transactions):
        # Add categorization
        tx['category'] = categorize_transaction(
            description=tx.get('description', ''), 
            amount=tx.get('amount'), 
            is_debit=tx.get('is_debit')
        )
        
        tx['subcategory'] = categorize_subcategory(tx.get('description', ''), tx['category'])
        
        # Format date and amount for display
        date = tx.get('date', 'Unknown date')
        
        amount = tx.get('amount', 0)
        amount_str = f"{amount:.2f}" if amount else "0.00"
        amount_color = GREEN if amount > 0 or tx['category'] == 'Income' else RED
        amount_sign = "" if amount > 0 or tx['category'] == 'Income' else "-"
        
        # Display transaction
        print(f"{BOLD}Transaction #{i+1}:{END}")
        print(f"  Date: {date}")
        print(f"  Description: {tx.get('description', 'No description')[:80]}")
        print(f"  Amount: {amount_color}{amount_sign}₹{abs(float(amount_str)):.2f}{END}")
        print(f"  Category: {YELLOW}{tx['category']}{END}")
        if tx['subcategory']:
            print(f"  Subcategory: {tx['subcategory']}")
        print(f"  Is Debit: {RED if tx.get('is_debit') else GREEN}{tx.get('is_debit')}{END}")
        print("")
    
    # Save results to file
    output_file = 'test_output.json'
    with open(output_file, 'w') as f:
        json.dump(transactions, f, indent=2)
    
    print(f"{BOLD}{GREEN}Results saved to {output_file}{END}")
    print(f"\n{BOLD}{BLUE}===== Test Complete ====={END}")

if __name__ == "__main__":
    main()
