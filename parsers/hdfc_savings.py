"""
HDFC Bank Parser

This parser extracts transactions from HDFC Bank statements using a table-based approach.
It identifies transactions based on the reference number pattern and determines transaction
type (credit/debit) based on balance changes.
"""

import fitz  # PyMuPDF
import re
from datetime import datetime

def detect_hdfc_savings(pdf_path):
    """
    Detect if a PDF file is an HDFC Bank savings account statement
    
    Args:
        pdf_path (str): Path to the PDF statement file
        
    Returns:
        bool: True if the file is an HDFC Bank savings account statement
    """
    try:
        print(f"[DEBUG] Attempting to detect HDFC savings statement: {pdf_path}")
        # Open PDF with PyMuPDF
        doc = fitz.open(pdf_path)
        
        # Extract text from the first page
        first_page_text = doc[0].get_text()
        print(f"[DEBUG] First page text:\n{first_page_text}")
        
        # Close the document
        doc.close()
        
        # Check for structural elements common in HDFC statements
        has_account_number = "Account No" in first_page_text
        has_hdfc = "HDFC BANK" in first_page_text
        has_transaction_section = "Statement of account" in first_page_text
        has_reference_pattern = bool(re.search(r'\d{12}', first_page_text))  # 12-digit reference numbers
        
        print(f"[DEBUG] Detection results:")
        print(f"[DEBUG] - Has account number: {has_account_number}")
        print(f"[DEBUG] - Has HDFC: {has_hdfc}")
        print(f"[DEBUG] - Has transaction section: {has_transaction_section}")
        print(f"[DEBUG] - Has reference pattern: {has_reference_pattern}")
        
        # If it has most of the structural elements, consider it a valid statement
        score = sum([has_account_number, has_hdfc, has_transaction_section, has_reference_pattern])
        is_valid = score >= 3
        print(f"[DEBUG] Detection score: {score}, Is valid: {is_valid}")
        return is_valid
        
    except Exception as e:
        print(f"[DEBUG] Error detecting HDFC statement: {str(e)}")
        return False

def parse_date(date_str):
    """
    Parse a date string into a formatted date
    
    Args:
        date_str (str): Date string to parse (DD/MM/YY format)
        
    Returns:
        str: Formatted date in DD/MM/YYYY format, or None if parsing fails
    """
    try:
        # Convert YY to YYYY
        if '/' in date_str:
            day, month, year = date_str.split('/')
            if len(year) == 2:
                # For HDFC statements, years like "25" mean "2025"
                year = '20' + year
            date_obj = datetime.strptime(f"{day}/{month}/{year}", "%d/%m/%Y")
            return date_obj.strftime("%d/%m/%Y")
        else:
            print(f"[DEBUG] Invalid date format: {date_str}")
            return None
    except ValueError as e:
        print(f"[DEBUG] Could not parse date format: {date_str}, error: {str(e)}")
        return None

def extract_statement_metadata(doc):
    """
    Extract metadata from the statement such as statement period, account holder, etc.
    
    Args:
        doc: PyMuPDF document object
        
    Returns:
        dict: Dictionary containing statement metadata
    """
    metadata = {
        "account_holder": "Unknown",
        "account_num": "Unknown",
        "branch": "Unknown",
        "opening_balance": None,
        "closing_balance": None
    }
    
    try:
        # Extract text from the first page
        first_page_text = doc[0].get_text()
        print(f"[DEBUG] Extracting metadata from:\n{first_page_text}")
        
        # Extract account holder
        account_holder_match = re.search(r'MR\s+([A-Z\s]+?)(?:\n|$)', first_page_text)
        if account_holder_match:
            metadata["account_holder"] = account_holder_match.group(1).strip()
            
        # Extract account number
        account_num_match = re.search(r'Account No\s*:?\s*(\d+)', first_page_text)
        if account_num_match:
            metadata["account_num"] = account_num_match.group(1)
        
        # Extract branch
        branch_match = re.search(r'Account Branch\s*:?\s*([A-Z\s]+?)(?:\n|$)', first_page_text)
        if branch_match:
            metadata["branch"] = branch_match.group(1).strip()
        
        # Try to get the first transaction's balance as opening balance
        lines = first_page_text.split('\n')
        for i, line in enumerate(lines):
            if re.match(r'^\d{2}/\d{2}/\d{2}$', line.strip()):
                # Look for balance in next few lines
                for j in range(i, min(i + 5, len(lines))):
                    balance_match = re.match(r'^[\d,]+\.\d{2}$', lines[j].strip())
                    if balance_match:
                        try:
                            metadata["opening_balance"] = float(balance_match.group(0).replace(',', ''))
                            break
                        except ValueError:
                            pass
                if metadata["opening_balance"] is not None:
                    break
        
        print(f"[DEBUG] Extracted metadata: {metadata}")
            
    except Exception as e:
        print(f"[DEBUG] Error extracting statement metadata: {str(e)}")
        
    return metadata

def extract_transactions(doc, metadata):
    """
    Extract transactions from the document using a tabular approach
    
    Args:
        doc: PyMuPDF document object
        metadata: Dictionary containing statement metadata
        
    Returns:
        list: List of transaction dictionaries
    """
    transactions = []
    
    # Process each page
    for page_num in range(len(doc)):
        page_text = doc[page_num].get_text()
        lines = page_text.split('\n')
        
        # Process each line
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Skip empty lines and headers
            if not line or any(marker in line for marker in ["Page No", "Statement of account", "Opening Balance", "Closing Balance", "Date", "Narration", "Chq./Ref.No.", "Value Dt", "Withdrawal Amt.", "Deposit Amt."]):
                i += 1
                continue
            
            # Look for transaction date (DD/MM/YY)
            date_match = re.match(r'^(\d{2}/\d{2}/\d{2})$', line)
            if date_match:
                date = parse_date(date_match.group(1))
                
                # Look for description and reference number in next lines
                description = ""
                reference = None
                amount = None
                balance = None
                
                # Look ahead up to 5 lines for transaction details
                for j in range(1, 6):
                    if i + j >= len(lines):
                        break
                        
                    next_line = lines[i + j].strip()
                    
                    # Skip empty lines
                    if not next_line:
                        continue
                    
                    # Look for reference number (12+ digits)
                    if not reference:
                        ref_match = re.search(r'(\d{12}(?:\d+)?)', next_line)
                        if ref_match:
                            reference = ref_match.group(1)
                            # Add description text before reference
                            description += " " + next_line[:ref_match.start()].strip()
                            continue
                    
                    # Look for amount and balance
                    if re.match(r'^[\d,]+\.\d{2}$', next_line):
                        if amount is None:
                            amount = float(next_line.replace(',', ''))
                        elif balance is None:
                            balance = float(next_line.replace(',', ''))
                            break
                    else:
                        # If not a number, it's part of the description
                        description += " " + next_line
                
                if amount is not None and balance is not None:
                    # Clean up description
                    description = re.sub(r'\s+', ' ', description).strip()
                    description = re.sub(r'-+$', '', description).strip()  # Remove trailing dashes
                    
                    # If no description was found, use a default one based on the amount
                    if not description:
                        description = f"Transaction of {abs(amount)}"
                    
                    # Determine if credit or debit
                    prev_balance = transactions[-1]["balance"] if transactions else None
                    if prev_balance is None:
                        # If we don't have a previous balance, use the withdrawal/deposit columns
                        withdrawal_match = re.search(r'Withdrawal Amt\.\s*([\d,]+\.\d{2})', page_text)
                        deposit_match = re.search(r'Deposit Amt\.\s*([\d,]+\.\d{2})', page_text)
                        
                        if withdrawal_match:
                            is_credit = False
                        elif deposit_match:
                            is_credit = True
                        else:
                            # Default to debit if we can't determine
                            is_credit = False
                    else:
                        is_credit = balance > prev_balance
                    
                    # Create transaction
                    transaction = {
                        "date": date,
                        "description": description,  # No longer using reference as fallback
                        "amount": amount if is_credit else -amount,
                        "type": "credit" if is_credit else "debit",
                        "reference": reference,
                        "balance": balance,
                        "account": "HDFC Savings",
                        "account_type": "savings",
                        "bank": "HDFC",
                        "account_name": "HDFC Savings Account",
                        "account_number": metadata["account_num"],
                        "branch": metadata["branch"]
                    }
                    
                    transactions.append(transaction)
                    i += j + 1
                    continue
            
            i += 1
    
    # Sort transactions by date and balance
    transactions.sort(key=lambda x: (x["date"] or "", x["balance"]))
    
    return transactions

def extract_hdfc_savings(pdf_path):
    """
    Parse HDFC Bank statements using a tabular structure approach
    
    Args:
        pdf_path (str): Path to the PDF statement file
        
    Returns:
        list: List of transaction dictionaries with transaction details
    """
    transactions = []
    
    try:
        print(f"[DEBUG] Starting to extract transactions from: {pdf_path}")
        # Open PDF with PyMuPDF
        doc = fitz.open(pdf_path)
        print(f"[DEBUG] Processing statement file with {len(doc)} pages")
        
        # Extract metadata
        metadata = extract_statement_metadata(doc)
        print(f"[DEBUG] Extracted metadata: {metadata}")
        
        # Extract transactions
        transactions = extract_transactions(doc, metadata)
        print(f"[DEBUG] Found {len(transactions)} transactions")
        
    except Exception as e:
        print(f"[DEBUG] Error processing HDFC statement: {str(e)}")
        return []
    
    finally:
        # Close the PDF document
        if 'doc' in locals() and doc:
            doc.close()
    
    return transactions
