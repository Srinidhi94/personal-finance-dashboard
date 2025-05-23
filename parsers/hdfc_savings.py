"""
HDFC Savings Account Parser

This module provides functionality to parse HDFC Bank savings account statements.
It identifies both credit and debit transactions using a balance-based algorithm.
"""

import fitz  # PyMuPDF
import re
import json
from datetime import datetime

def extract_hdfc_savings(pdf_path):
    """
    Parse HDFC bank savings account statements to extract transactions
    
    Args:
        pdf_path (str): Path to the PDF statement file
        
    Returns:
        list: List of transaction dictionaries with complete transaction details
    """
    transactions = []
    
    try:
        # Open PDF with PyMuPDF
        doc = fitz.open(pdf_path)
        print(f"Processing statement file with {len(doc)} pages")
        
        # Extract text with proper structure
        first_page_text = doc[0].get_text()
        
        # Extract basic statement info
        account_holder_match = re.search(r'MR\s+([\w\s]+)', first_page_text)
        account_holder = account_holder_match.group(1).strip() if account_holder_match else "Unknown"
        
        date_range_match = re.search(r'From\s+:\s+(\d{2}/\d{2}/\d{4})\s+To\s+:\s+(\d{2}/\d{2}/\d{4})', first_page_text)
        statement_date_from = date_range_match.group(1) if date_range_match else None
        statement_date_to = date_range_match.group(2) if date_range_match else None
        
        # Get full text and clean it up
        full_text = ""
        for p in range(len(doc)):
            text = doc[p].get_text()
            # Remove header lines
            text = re.sub(r'Date\s+Narration\s+Chq\./Ref\.No\.\s+Value\s+Dt\s+Withdrawal\s+Amt\.\s+Deposit\s+Amt\.\s+Closing\s+Balance\s*\n', '', text)
            full_text += text
        
        # Clean up line breaks in the middle of transactions
        full_text = re.sub(r'\n(?!\d{2}/\d{2}/\d{2})', ' ', full_text)
        
        # Extract lines and group them by transaction
        lines = full_text.strip().split('\n')
        transactions_text = []
        
        # Group lines by transaction (looking for pairs of lines that start with the same date)
        i = 0
        while i < len(lines):
            # Skip empty lines
            if not lines[i].strip():
                i += 1
                continue
                
            # Check if this line starts with a date pattern
            date_match = re.match(r'^\d{2}/\d{2}/\d{2}', lines[i])
            if date_match:
                # This is the start of a transaction
                transaction_line1 = lines[i]
                
                # Look ahead for a line with the same date pattern (the amount and balance line)
                if i + 1 < len(lines) and re.match(r'^\d{2}/\d{2}/\d{2}', lines[i + 1]):
                    transaction_line2 = lines[i + 1]
                    transactions_text.append((transaction_line1, transaction_line2))
                    i += 2  # Skip both lines in the next iteration
                else:
                    # No matching second line, treat as a single line transaction
                    transactions_text.append((transaction_line1, ""))
                    i += 1
            else:
                # Not a transaction start, skip
                i += 1
        
        print(f"Found {len(transactions_text)} potential transactions to process")
        
        match_count = 0
        for line1, line2 in transactions_text:
            try:
                match_count += 1
                
                # Extract from line 1: Date, Narration, Ref No
                line1_parts = re.match(r'^(\d{2}/\d{2}/\d{2})\s+(.*?)(?:\s+([\w./-]{1,30}))?$', line1.strip())
                if not line1_parts:
                    print(f"Cannot parse transaction details from line: {line1}")
                    continue
                    
                date_str = line1_parts.group(1)
                narration = line1_parts.group(2).strip()
                ref_no_str = line1_parts.group(3) if line1_parts.group(3) else None
                
                # Extract from line 2: Amount and Balance
                # Format: DD/MM/YY Amount Balance Additional_Text
                if not line2:
                    print(f"Missing second line for transaction on {date_str}")
                    continue
                    
                line2_parts = re.match(r'^\d{2}/\d{2}/\d{2}\s+(\d[\d,]+\.\d{2})\s+(\d[\d,]+\.\d{2})', line2.strip())
                if not line2_parts:
                    print(f"Cannot parse amount details from line: {line2}")
                    continue
                    
                amount_str = line2_parts.group(1)
                balance_str = line2_parts.group(2)
                
                # Clean up narration
                narration = re.sub(r'\s+', ' ', narration)
                
                # Convert amount and balance to float
                amount_float = float(amount_str.replace(',', ''))
                balance_float = float(balance_str.replace(',', ''))
                
                # Determine if this is a deposit or withdrawal based on balance change
                # If we have a previous transaction, we can calculate whether this is a credit or debit
                is_debit = True  # Default to withdrawal/expense
                
                # Calculate the expected balance if this was a debit transaction
                if len(transactions) > 0:
                    prev_balance = transactions[-1]['balance']
                    expected_debit_balance = prev_balance - amount_float
                    expected_credit_balance = prev_balance + amount_float
                    
                    # Compare the actual balance with expected balances (with a small margin for rounding errors)
                    margin = 0.01  # 1 cent margin
                    if abs(balance_float - expected_credit_balance) < margin:
                        # This is a credit transaction (the balance increased by the amount)
                        is_debit = False
                    elif abs(balance_float - expected_debit_balance) < margin:
                        # This is a debit transaction (the balance decreased by the amount)
                        is_debit = True
                    else:
                        # If neither matches closely, fallback to simpler balance comparison
                        # If balance > previous balance, it's likely a credit
                        is_debit = balance_float <= prev_balance
                
                # Apply the correct sign to the amount
                amount = amount_float
                if is_debit:
                    amount = -amount
                
                # Convert date format (DD/MM/YY to DD/MM/YYYY)
                date_parts = date_str.split('/')
                day, month, short_year = date_parts
                year = f"20{short_year}"  # Assuming all dates are in the 21st century
                date = f"{day}/{month}/{year}"  # Use DD/MM/YYYY format
                
                # Create transaction object
                transaction = {
                    'date': date,
                    'description': narration,
                    'amount': amount,
                    'bank': 'HDFC',
                    'account_type': 'savings',
                    'account_name': 'HDFC Savings Account',
                    'statement_date_from': statement_date_from,
                    'statement_date_to': statement_date_to,
                    'account_holder': account_holder,
                    'is_debit': is_debit,
                    'source': 'HDFC Savings',
                    'confidence': 'High',
                    'reference': ref_no_str or '',
                    'notes': '',
                    'balance': balance_float
                }
                
                transactions.append(transaction)
                
            except Exception as e:
                print(f"Error processing transaction: {e}")
                import traceback
                traceback.print_exc()
                continue
            
    except Exception as e:
        print(f"Error processing PDF: {e}")
        import traceback
        traceback.print_exc()
    
    return transactions

def detect_hdfc_savings(pdf_path):
    """
    Detect if the provided PDF is an HDFC Savings Account statement
    
    Args:
        pdf_path (str): Path to the PDF file to analyze
        
    Returns:
        bool: True if the file is identified as an HDFC Savings statement, False otherwise
    """
    try:
        doc = fitz.open(pdf_path)
        for page in doc:
            text = page.get_text()
            # Check for identifying markers in HDFC savings statements
            if "HDFC BANK" in text and "Statement of account" in text and "Withdrawal Amt." in text and "Deposit Amt." in text:
                return True
        return False
    except Exception:
        return False
