"""
Federal Bank Parser - Consolidated Version

This parser extracts transactions from Federal Bank statements using a table-based approach.
It identifies transactions based on the date column and uses the arrow next to the amount
(⊕ for credit/income, ⊖ for debit/expense) to determine transaction type.
"""

import fitz  # PyMuPDF
import re
from datetime import datetime


def detect_federal_bank_savings(pdf_path):
    """
    Detect if a PDF file is a Federal Bank savings account statement
    
    Args:
        pdf_path (str): Path to the PDF statement file
        
    Returns:
        bool: True if the file is a Federal Bank savings account statement
    """
    try:
        # Open PDF with PyMuPDF
        doc = fitz.open(pdf_path)
        
        # Extract text from the first page
        first_page_text = doc[0].get_text()
        
        # Close the document
        doc.close()
        
        # Check for structural elements common in Federal Bank statements
        has_account_number = "SAVINGS A/C NO" in first_page_text
        has_ifsc = "FDRL" in first_page_text  # Federal Bank IFSC code
        has_transaction_section = "Transaction Details" in first_page_text
        has_balance_section = "Opening Balance" in first_page_text and "Closing Balance" in first_page_text
        
        # If it has most of the structural elements, consider it a valid statement
        score = sum([has_account_number, has_ifsc, has_transaction_section, has_balance_section])
        return score >= 3
        
    except Exception as e:
        print(f"Error detecting Federal Bank statement: {str(e)}")
        return False


def extract_statement_metadata(doc):
    """
    Extract metadata from the statement such as statement period, account holder, etc.
    
    Args:
        doc: PyMuPDF document object
        
    Returns:
        dict: Dictionary containing statement metadata
    """
    metadata = {
        "statement_year": datetime.now().year,  # Default to current year
        "account_holder": "Unknown",
        "account_num": "Unknown"
    }
    
    try:
        # Extract text from the first page
        first_page_text = doc[0].get_text()
        
        # Extract statement period
        statement_period_match = re.search(r'(\d{1,2}\s+[A-Z][a-z]{2}\s+\d{4})\s+to\s+(\d{1,2}\s+[A-Z][a-z]{2}\s+\d{4})', first_page_text)
        if statement_period_match:
            try:
                end_date_str = statement_period_match.group(2)  # End date has format "DD MMM YYYY"
                metadata["statement_year"] = int(end_date_str.split()[-1])
            except:
                # Try to find year in closing balance date
                closing_match = re.search(r'Closing Balance\s*\non[^₹]*(\d{1,2}\s+[A-Z][a-z]{2}\s+\d{4})', first_page_text)
                if closing_match:
                    try:
                        closing_date = closing_match.group(1)
                        metadata["statement_year"] = int(closing_date.split()[-1])
                    except:
                        print("Could not extract year from closing balance date, using current year")
                else:
                    print("Could not extract year from statement period, using current year")
        
        # Extract account holder
        account_holder_match = re.search(r'Account\s+Holder:\s*([A-Za-z\s]+)', first_page_text)
        if account_holder_match:
            metadata["account_holder"] = account_holder_match.group(1).strip()
            
        # Extract account number
        account_num_match = re.search(r'SAVINGS A/C NO:\s*(\d+)', first_page_text)
        if account_num_match:
            metadata["account_num"] = account_num_match.group(1)
            
    except Exception as e:
        print(f"Error extracting statement metadata: {str(e)}")
        
    return metadata


def parse_date(date_str, statement_year):
    """
    Parse a date string into a formatted date
    
    Args:
        date_str (str): Date string to parse
        statement_year (int): Year to use for dates without year
        
    Returns:
        str: Formatted date in DD/MM/YYYY format, or None if parsing fails
    """
    try:
        if '/' in date_str:  # DD/MM/YYYY format
            date_obj = datetime.strptime(date_str, "%d/%m/%Y")
            return date_obj.strftime("%d/%m/%Y")
        else:  # DD MMM format
            date_obj = datetime.strptime(f"{date_str} {statement_year}", "%d %b %Y")
            return date_obj.strftime("%d/%m/%Y")
    except ValueError:
        print(f"Warning: Could not parse date format: {date_str}")
        return None


def extract_transactions(doc, statement_year):
    """
    Extract transactions from the document using a tabular approach
    
    Args:
        doc: PyMuPDF document object
        statement_year (int): Year of the statement
        
    Returns:
        list: List of transaction dictionaries
    """
    transactions = []
    
    # Get opening balance from first page
    first_page_text = doc[0].get_text()
    
    # Try different opening balance patterns
    opening_match = None
    opening_patterns = [
        r'Opening Balance\s*\non[^₹]*₹\s*([0-9,]+\.[0-9]{2})',  # With ₹ symbol
        r'Opening Balance\s*\non[^0-9]*([0-9,]+\.[0-9]{2})',  # Without ₹ symbol
        r'Opening Balance\s*\non.*?(\d{1,3}(?:,\d{3})*\.\d{2})',  # Just the number
        r'Opening Balance\s*\non.*?[₹·]?\s*(\d+(?:,\d{3})*\.\d{2})',  # Optional symbol with commas
        r'Opening Balance\s*\non.*?[₹·]?\s*(\d+(?:[,\.]\d+)*)',  # Most flexible pattern
    ]
    
    # First try exact patterns
    for pattern in opening_patterns:
        opening_match = re.search(pattern, first_page_text, re.DOTALL | re.IGNORECASE)
        if opening_match:
            try:
                value = opening_match.group(1).replace(',', '')
                if '.' not in value:
                    value += '.00'
                opening_balance = float(value)
                break
            except (ValueError, AttributeError):
                continue
    
    # If no match found, try line-by-line approach
    if not opening_match:
        lines = first_page_text.split('\n')
        for i, line in enumerate(lines):
            if "Opening Balance" in line and i + 2 < len(lines):
                # Skip the "on DD MMM YYYY" line
                balance_line = lines[i + 2].strip()
                # Try to extract number from the balance line
                balance_match = re.search(r'[₹·]?\s*([0-9,]+\.[0-9]{2})', balance_line)
                if balance_match:
                    try:
                        value = balance_match.group(1).replace(',', '')
                        opening_balance = float(value)
                        opening_match = balance_match
                        break
                    except (ValueError, AttributeError):
                        continue
    
    opening_balance = float(opening_match.group(1).replace(',', '')) if opening_match else None
    print(f"[DEBUG] Opening balance: {opening_balance}")
    
    # Add opening balance as first transaction if found
    if opening_balance is not None:
        opening_date_match = re.search(r'Opening Balance\s*\non\s*(\d{1,2}\s+[A-Z][a-z]{2})', first_page_text, re.IGNORECASE)
        opening_date = parse_date(opening_date_match.group(1), statement_year) if opening_date_match else None
        print(f"[DEBUG] Opening date: {opening_date}")
        
        transactions.append({
            "date": opening_date,
            "description": "Opening Balance",
            "amount": 0,  # Don't count in totals
            "type": "balance",  # Special type for opening balance
            "balance": opening_balance
        })
    
    # Process each line for transactions
    lines = first_page_text.split('\n')
    i = 0
    in_closing_balance = False
    
    while i < len(lines):
        line = lines[i].strip()
        
        # Skip empty lines and closing balance section
        if not line:
            i += 1
            continue
        
        if "Closing Balance" in line:
            in_closing_balance = True
            i += 1
            continue
        
        if in_closing_balance:
            i += 1
            continue
        
        # Look for date pattern (DD MMM)
        date_match = re.match(r'(\d{1,2}\s+[A-Z][a-z]{2})', line)
        if date_match:
            date = parse_date(date_match.group(1), statement_year)
            if date:
                # Look for transaction details in next line
                if i + 1 < len(lines):
                    description = lines[i + 1].strip()
                    
                    # Look for amount and balance in next lines
                    if i + 2 < len(lines) and i + 3 < len(lines):
                        amount_str = lines[i + 2].strip().replace(',', '')
                        balance_str = lines[i + 3].strip().replace(',', '')
                        
                        try:
                            amount = float(amount_str)
                            balance = float(balance_str)
                            
                            # Determine if credit or debit based on description and balance change
                            is_credit = True
                            if len(transactions) > 0:
                                prev_balance = transactions[-1]["balance"]
                                is_credit = balance > prev_balance
                            
                            # Override credit/debit based on description patterns
                            if any(pattern in description for pattern in ["POS/", "TO INTL", "CHRG/", "Visa Other", "UPI/DR/", "IMPS/DR/", "NEFT/DR/", "TO ECM/"]):
                                is_credit = False
                            elif any(pattern in description for pattern in ["UPI/CR/", "IMPS/CR/", "NEFT/CR/", "ForexMarkupRefund/"]):
                                is_credit = True
                            
                            transactions.append({
                                "date": date,
                                "description": description,
                                "amount": amount if is_credit else -amount,
                                "type": "credit" if is_credit else "debit",
                                "balance": balance
                            })
                            
                            i += 3  # Skip processed lines
                            continue
                        except ValueError:
                            pass
        
        i += 1
    
    print(f"[DEBUG] Found {len(transactions)} transactions")
    return transactions


def extract_federal_bank_savings(pdf_path):
    """
    Parse Federal Bank statements using a tabular structure approach
    
    Args:
        pdf_path (str): Path to the PDF statement file
        
    Returns:
        list: List of transaction dictionaries with transaction details
    """
    transactions = []
    
    try:
        # Open PDF with PyMuPDF
        doc = fitz.open(pdf_path)
        
        # Extract metadata
        metadata = extract_statement_metadata(doc)
        
        # Extract transactions
        transactions = extract_transactions(doc, metadata["statement_year"])
        
        print(f"Extracted {len(transactions)} transactions")
        
        # Sort transactions by date, keeping opening balance first
        if len(transactions) > 0:
            opening_balance = None
            if transactions[0]["type"] == "balance":
                opening_balance = transactions.pop(0)
            
            # Sort remaining transactions by date
            transactions.sort(key=lambda x: x["date"] or "")
            
            # Put opening balance back at the start
            if opening_balance:
                transactions.insert(0, opening_balance)
        
    except Exception as e:
        print(f"Error processing Federal Bank statement: {str(e)}")
        return []
    
    finally:
        # Close the PDF document
        if 'doc' in locals() and doc:
            doc.close()
    
    return transactions
