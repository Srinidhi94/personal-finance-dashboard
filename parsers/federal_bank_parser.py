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
    current_date = None
    current_description = None
    
    # Get opening balance from first page
    first_page_text = doc[0].get_text()
    print("First page text:", first_page_text)  # Debug output
    
    # Try different opening balance patterns
    opening_match = None
    opening_patterns = [
        r'Opening Balance\s*\non[^₹]*₹\s*([0-9,]+\.[0-9]{2})',  # Standard format
        r'Opening Balance\s*\non[^₹]*₹\s*([0-9,]+)',  # Without decimals
        r'Opening Balance\s*\non.*?\n.*?₹\s*([\d,]+\.\d{2})',  # Multi-line format
        r'Opening Balance\s*\non.*?\n.*?₹([0-9,]+\.[0-9]{2})',  # No space after ₹
        r'Opening Balance\s*\non.*?₹\s*([0-9,]+\.[0-9]{2})',  # Single line with ₹
        r'Opening Balance\s*\non.*?(\d{1,3}(?:,\d{3})*\.\d{2})',  # Just the number
        r'Opening Balance\s*\non.*?₹\s*(\d{1,3}(?:,\d{3})*\.\d{2})',  # ₹ with number
        r'Opening Balance\s*\non.*?·\s*([0-9,]+\.[0-9]{2})',  # PDF dot format
        r'Opening Balance\s*\non.*?·([0-9,]+\.[0-9]{2})',  # PDF dot no space
        r'Opening Balance\s*\non.*?[₹·]\s*([0-9,]+\.[0-9]{2})',  # Any currency symbol
        r'Opening Balance\s*\non.*?[₹·]([0-9,]+\.[0-9]{2})',  # Any currency symbol no space
        r'Opening Balance\s*\non.*?[₹·]?\s*([0-9,]+\.[0-9]{2})',  # Optional currency symbol
        r'Opening Balance\s*\non.*?[₹·]?\s*(\d{1,3}(?:,\d{3})*\.\d{2})',  # Optional symbol with commas
        r'Opening Balance\s*\non.*?[₹·]?\s*(\d+(?:,\d{3})*\.\d{2})',  # Optional symbol with any number
        r'Opening Balance\s*\non.*?[₹·]?\s*(\d+(?:[,\.]\d+)*)',  # Most flexible pattern
        r'Opening Balance\s*\non.*?[₹·]?\s*(\d+(?:[,\.]\d+)*)\s*(?:\n|$)'  # End of line or newline
    ]
    
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
    
    print("Opening balance match:", opening_match)  # Debug output
    if opening_match:
        print("Opening balance value:", opening_match.group(1))  # Debug output
    
    opening_balance = float(opening_match.group(1).replace(',', '')) if opening_match else None
    print("Opening balance:", opening_balance)  # Debug output
    
    # Add opening balance as first transaction if found
    if opening_balance is not None:
        opening_date_match = re.search(r'Opening Balance\s*\non\s*(\d{1,2}\s+[A-Z][a-z]{2})', first_page_text, re.IGNORECASE)
        print("Opening date match:", opening_date_match)  # Debug output
        if opening_date_match:
            print("Opening date value:", opening_date_match.group(1))  # Debug output
        
        opening_date = parse_date(opening_date_match.group(1), statement_year) if opening_date_match else None
        print("Opening date:", opening_date)  # Debug output
        
        if opening_date:
            transactions.append({
                "date": opening_date,
                "description": "Opening Balance",
                "amount": 0,  # Don't count in totals
                "type": "balance",  # Special type for opening balance
                "category": "Opening Balance",
                "account": "Federal Bank Savings",
                "account_type": "savings",
                "bank": "Federal Bank",
                "account_name": "Federal Bank Savings Account",
                "is_debit": False,
                "transaction_id": "opening_balance",
                "balance": opening_balance,
                "sort_key": (0, opening_balance)  # Default priority for opening balance
            })
    
    # Process each page
    for page_num in range(len(doc)):
        page_text = doc[page_num].get_text()
        lines = page_text.split('\n')
        
        # Process each line
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Skip empty lines and headers/footers
            if not line or any(marker in line for marker in ["PAGE", "CONTACT US", "5AM - 6PM", "6PM - 5AM", "ISSUED BY", "Comment •", "Transaction Details", "Day/Night", "Amount", "Balance", "Statement Period"]):
                i += 1
                continue
            
            # Check for date line (e.g., "02 May")
            date_match = re.match(r'^(\d{1,2}\s+[A-Z][a-z]{2})$', line)
            if date_match:
                current_date = parse_date(date_match.group(1), statement_year)
                current_description = None  # Reset description for new date
                i += 1
                continue
            
            if not current_date:
                i += 1
                continue
            
            # Look for transaction description
            # Common patterns: POS/, TO INTL, CHRG/, UPI IN/, ForexMarkupRefund/, Visa Other, TO ECM
            if any(pattern in line for pattern in ["POS/", "TO INTL", "CHRG/", "UPI IN/", "ForexMarkupRefund/", "Visa Other", "UPI/", "IMPS/", "NEFT/", "TO ECM/"]):
                # Get amount and balance from next lines
                amount = None
                balance = None
                
                # Look for amount in next few lines
                for j in range(1, 4):  # Look up to 3 lines ahead
                    if i + j < len(lines):
                        amount_line = lines[i + j].strip()
                        if re.match(r'^[\d,]+\.\d{2}$', amount_line):
                            try:
                                # Remove commas and convert to float
                                amount = float(amount_line.replace(',', ''))
                                # Look for balance in next line
                                if i + j + 1 < len(lines):
                                    balance_line = lines[i + j + 1].strip()
                                    if re.match(r'^[\d,]+\.\d{2}$', balance_line):
                                        balance = float(balance_line.replace(',', ''))
                                        i = i + j + 2  # Skip processed lines
                                        break
                            except ValueError:
                                pass
                
                if amount is not None and balance is not None:
                    # Determine if credit or debit
                    is_credit = False
                    
                    # Check for credit indicators
                    if any(indicator in line for indicator in ["ForexMarkupRefund/", "UPI IN/", "UPI/CR/", "IMPS/CR/", "NEFT/CR/"]):
                        is_credit = True
                    # Check for debit indicators
                    elif any(indicator in line for indicator in ["POS/", "TO INTL", "CHRG/", "Visa Other", "UPI/DR/", "IMPS/DR/", "NEFT/DR/", "TO ECM/"]):
                        is_credit = False
                    # If still unsure, use balance change
                    else:
                        # Compare with previous transaction's balance
                        if transactions:
                            prev_balance = transactions[-1].get('balance', 0)
                            is_credit = balance > prev_balance
                    
                    # Determine transaction type for sorting
                    txn_type = 0  # Default priority
                    if "TO INTL" in line:
                        txn_type = 2  # International fee comes after main transaction
                    elif "TO ECM" in line:
                        txn_type = 1  # Main transaction comes first
                    
                    # Create transaction dictionary
                    transaction = {
                        "date": current_date,
                        "description": line,
                        "amount": amount if is_credit else -amount,
                        "type": "credit" if is_credit else "debit",
                        "category": "Uncategorized",
                        "account": "Federal Bank Savings",
                        "account_type": "savings",
                        "bank": "Federal Bank",
                        "account_name": "Federal Bank Savings Account",
                        "is_debit": not is_credit,
                        "transaction_id": f"{current_date}_{amount}_{len(transactions)}",
                        "balance": balance,
                        "sort_key": (txn_type, balance)  # Sort by type first, then balance
                    }
                    
                    transactions.append(transaction)
                    continue
            
            # Look for Visa Other Charges lines
            visa_match = re.match(r'^Visa Other Chrgs (\d{2}/\d{2}/\d{4})\s+(.+)$', line)
            if visa_match:
                # Get amount and balance from next lines
                amount = None
                balance = None
                
                # Look for amount in next few lines
                for j in range(1, 4):  # Look up to 3 lines ahead
                    if i + j < len(lines):
                        amount_line = lines[i + j].strip()
                        if re.match(r'^[\d,]+\.\d{2}$', amount_line):
                            try:
                                # Remove commas and convert to float
                                amount = float(amount_line.replace(',', ''))
                                # Look for balance in next line
                                if i + j + 1 < len(lines):
                                    balance_line = lines[i + j + 1].strip()
                                    if re.match(r'^[\d,]+\.\d{2}$', balance_line):
                                        balance = float(balance_line.replace(',', ''))
                                        i = i + j + 2  # Skip processed lines
                                        break
                            except ValueError:
                                pass
                
                if amount is not None and balance is not None:
                    # Create transaction dictionary for Visa charge
                    transaction = {
                        "date": current_date,
                        "description": f"Visa Other Charges - {visa_match.group(2)}",
                        "amount": -amount,  # Always debit
                        "type": "debit",
                        "category": "Bank Charges",
                        "account": "Federal Bank Savings",
                        "account_type": "savings",
                        "bank": "Federal Bank",
                        "account_name": "Federal Bank Savings Account",
                        "is_debit": True,
                        "transaction_id": f"{current_date}_{amount}_{len(transactions)}",
                        "balance": balance,
                        "sort_key": (0, balance)  # Default priority for Visa charges
                    }
                    
                    transactions.append(transaction)
                    continue
            
            i += 1
    
    # Sort transactions by date and sort key
    transactions.sort(key=lambda x: (x["date"], x.get("sort_key", (0, 0))))
    
    print(f"Extracted {len(transactions)} transactions")
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
        
        # Sort transactions by date
        transactions.sort(key=lambda x: x["date"])
        
    except Exception as e:
        print(f"Error processing Federal Bank statement: {str(e)}")
        return []
    
    finally:
        # Close the PDF document
        if 'doc' in locals() and doc:
            doc.close()
    
    return transactions
