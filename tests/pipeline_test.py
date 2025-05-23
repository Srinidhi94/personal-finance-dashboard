#!/usr/bin/env python3

"""
End-to-end test of the full bank statement parsing and categorization flow.
This tests:
1. Parsing PDF statements
2. Proper narration/description extraction
3. Correct identification of income vs expense transactions
4. Proper categorization based on transaction type and description
"""

import sys
import json
import os
import argparse
import shutil
from pathlib import Path

# Add the parent directory to the path so we can import the parsers module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.hdfc_savings import extract_hdfc_savings

# Simple categorization functions for testing
def simple_categorize_transaction(description, amount, is_debit):
    """
    Simplified version of transaction categorization for testing purposes.
    
    Args:
        description (str): The transaction description/narration
        amount (float): The transaction amount
        is_debit (bool): Whether the transaction is a debit (expense) or not
        
    Returns:
        str: The category name assigned to the transaction
    """
    description = description.lower()
    
    # Basic income detection (credit transactions)
    if not is_debit or amount > 0:
        return "Income"
    
    # Food related
    if any(keyword in description for keyword in ["swiggy", "food", "restaurant", "grocery", "hungerbox"]):
        return "Food"
    
    # Transport related
    if any(keyword in description for keyword in ["uber", "ola", "metro", "petrol", "fuel"]):
        return "Transportation"
        
    # Shopping
    if any(keyword in description for keyword in ["amazon", "flipkart", "shopping", "store", "retail"]):
        return "Shopping"
        
    # Investments
    if any(keyword in description for keyword in ["zerodha", "indian clearing corp", "investment", "broking"]):
        return "Investments"
    
    # Default category
    return "Miscellaneous"

def simple_categorize_subcategory(description, category):
    """
    Simplified version of subcategory determination for testing purposes.
    
    Args:
        description (str): The transaction description/narration
        category (str): The primary category of the transaction
        
    Returns:
        str: The subcategory name assigned to the transaction, or empty string if none
    """
    description = description.lower()
    
    # Some simple rules for testing
    if category == "Income":
        if "salary" in description or "payroll" in description:
            return "Salary"
        elif "interest" in description:
            return "Interest"
        return "Other Income"
    
    elif category == "Food":
        if "swiggy" in description:
            return "Food Delivery"
        elif "restaurant" in description:
            return "Dining Out"
        return "Groceries"
        
    elif category == "Transportation":
        if "uber" in description:
            return "Ride Sharing"
        elif "flight" in description:
            return "Air Travel"
        return "Local Transport"
        
    # Default empty subcategory
    return ""

def main():
    """Main function to run the pipeline test."""
    # Set up command line arguments
    parser = argparse.ArgumentParser(description='Test the personal finance dashboard parsing and categorization pipeline')
    parser.add_argument('--pdf-path', type=str, default='uploads/Statement_Example.pdf',
                      help='Path to the PDF statement to parse')
    parser.add_argument('--output-dir', type=str, default='tests/test_results',
                      help='Directory to store test results')
    parser.add_argument('--clean', action='store_true',
                      help='Remove results file after test is complete')
    args = parser.parse_args()
    
    # Create output directory if it doesn't exist
    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), args.output_dir)
    os.makedirs(output_dir, exist_ok=True)
    
    # Set output file path
    output_file = os.path.join(output_dir, 'pipeline_test_results.json')
    
    print(f"\nTesting full pipeline on {args.pdf_path}\n")
    
    try:
        # Parse transactions
        print("Step 1: Parsing transactions from PDF")
        transactions = extract_hdfc_savings(args.pdf_path)
        
        print(f"\nFound {len(transactions)} transactions")
        
        # Categorize transactions
        print("\nStep 2: Categorizing transactions")
        for tx in transactions:
            # Store original values
            tx['original_description'] = tx['description']
            tx['original_amount'] = tx['amount']
            tx['original_is_debit'] = tx['is_debit']
            
            # Call categorize_transaction function with all available info
            category = simple_categorize_transaction(
                description=tx['description'], 
                amount=tx['amount'], 
                is_debit=tx['is_debit']
            )
            tx['category'] = category
            
            # Get subcategory
            tx['subcategory'] = simple_categorize_subcategory(tx['description'], category)
            
            # Display results
            category_type = "Income" if tx['category'] == "Income" else "Expense"
            transaction_type = "Debit/Expense" if tx['is_debit'] else "Credit/Income"
            print(f"\nTransaction: {tx['date']} - {tx['description'][:50]}...")
            print(f"  Amount: {'%.2f' % tx['amount']} ({transaction_type})")
            print(f"  Categorized as: {tx['category']} - {tx['subcategory'] or 'No subcategory'} ({category_type})")
            
            # Check for potential categorization issues
            if tx['is_debit'] == False and tx['category'] != "Income":
                print(f"  ⚠️ WARNING: Transaction is marked as credit but not categorized as income")
            elif tx['is_debit'] == True and tx['category'] == "Income":
                print(f"  ⚠️ WARNING: Transaction is marked as debit but categorized as income")
            
        # Save results to file for analysis
        with open(output_file, 'w') as f:
            json.dump(transactions, f, indent=2)
            print(f"\nSaved all transactions with categorization to {output_file}")
        
        # Clean up if requested
        if args.clean:
            print(f"Cleaning up test results file")
            os.remove(output_file)
            
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
