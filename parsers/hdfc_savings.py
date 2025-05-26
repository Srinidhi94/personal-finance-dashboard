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
        account_holder_match = re.search(r'MR\.\s*([A-Z\s]+?)(?:\n|$)', first_page_text)
        if account_holder_match:
            metadata["account_holder"] = account_holder_match.group(1).strip()
        else:
            # Try alternate format
            alt_match = re.search(r'(?:^|\n)([A-Z][A-Z\s]+R)(?:\n|$)', first_page_text)
            if alt_match:
                metadata["account_holder"] = alt_match.group(1).strip()
            
        # Extract account number
        account_num_match = re.search(r'Account No\s*:?\s*(\d+)', first_page_text)
        if account_num_match:
            metadata["account_num"] = account_num_match.group(1)
        
        # Extract branch
        branch_match = re.search(r'Branch\s*:?\s*([A-Z\s]+?)(?:\n|$)', first_page_text)
        if branch_match:
            metadata["branch"] = branch_match.group(1).strip()
        
        # Extract opening balance
        opening_match = re.search(r'Opening Balance\s*:?\s*([\d,]+\.\d{2})', first_page_text)
        if opening_match:
            try:
                metadata["opening_balance"] = float(opening_match.group(1).replace(',', ''))
            except ValueError:
                pass
        
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
    
    # Add opening balance as first transaction if available
    if metadata["opening_balance"] is not None:
        transactions.append({
            "date": None,  # Opening balance date not required
            "description": "Opening Balance",
            "amount": 0,  # Don't count in totals
            "type": "balance",  # Special type for opening balance
            "balance": metadata["opening_balance"]
        })
    
    # Process each page
    for page_num in range(len(doc)):
        page_text = doc[page_num].get_text()
        lines = page_text.split('\n')
        
        # Process each line
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Skip empty lines and headers
            if not line or any(marker in line for marker in ["Page No", "Statement of account", "Opening Balance:", "Closing Balance:", "Date", "Narration", "Chq./Ref.No.", "Value Dt", "Withdrawal Amt.", "Deposit Amt."]):
                i += 1
                continue
            
            # Look for transaction date (DD/MM/YY)
            date_match = re.match(r'(\d{2}/\d{2}/\d{2})', line)  # Removed $ anchor
            if date_match:
                date = parse_date(date_match.group(1))
                print(f"[DEBUG] Found date: {date}")
                
                # Look for reference number in next line
                if i + 1 < len(lines):
                    ref_line = lines[i + 1].strip()
                    ref_match = re.match(r'(\d{12}\d*)', ref_line)
                    if ref_match:
                        reference = ref_match.group(1)  # Keep the full reference number
                        print(f"[DEBUG] Found reference: {reference}")
                        
                        # Look for description in next line
                        if i + 2 < len(lines):
                            description = lines[i + 2].strip()
                            print(f"[DEBUG] Found description: {description}")
                            
                            # Look for amount and balance in next lines
                            if i + 3 < len(lines) and i + 4 < len(lines):
                                amount_str = lines[i + 3].strip().replace(',', '')
                                balance_str = lines[i + 4].strip().replace(',', '')
                                print(f"[DEBUG] Found amount: {amount_str}, balance: {balance_str}")
                                
                                try:
                                    amount = float(amount_str)
                                    balance = float(balance_str)
                                    
                                    # Determine if credit or debit based on balance change
                                    is_credit = True
                                    if len(transactions) > 0:
                                        prev_balance = transactions[-1]["balance"]
                                        is_credit = balance > prev_balance
                                    
                                    transactions.append({
                                        "date": date,
                                        "reference": reference,
                                        "description": description,
                                        "amount": amount if is_credit else -amount,
                                        "type": "credit" if is_credit else "debit",
                                        "balance": balance
                                    })
                                    print(f"[DEBUG] Added transaction: {transactions[-1]}")
                                    
                                    i += 4  # Skip processed lines
                                    continue
                                except ValueError:
                                    print(f"[DEBUG] Error parsing amount/balance: {amount_str}, {balance_str}")
                                    pass
            
            i += 1
    
    print(f"[DEBUG] Found {len(transactions)} transactions")
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
