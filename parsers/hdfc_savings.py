"""
HDFC Bank Parser

This parser extracts transactions from HDFC Bank statements using a table-based approach.
It identifies transactions based on the date column and uses transaction patterns to determine
transaction type (credit/debit).
"""

import re
from datetime import datetime

import fitz  # PyMuPDF


def detect_hdfc_savings(pdf_path):
    """
    Detect if a PDF is an HDFC savings account statement

    Args:
        pdf_path (str): Path to the PDF file

    Returns:
        bool: True if it's an HDFC savings statement, False otherwise
    """
    try:
        doc = fitz.open(pdf_path)
        first_page_text = doc[0].get_text()
        doc.close()

        # Check for HDFC specific patterns
        hdfc_patterns = [
            r"HDFC BANK",
            r"SAVINGS ACCOUNT",
            r"SAVINGS ACCOUNT STATEMENT",
            r"Account Number",
            r"Statement Period",
            r"Opening Balance",
            r"Closing Balance",
        ]

        # Count how many patterns match
        matches = 0
        for pattern in hdfc_patterns:
            if re.search(pattern, first_page_text, re.IGNORECASE):
                matches += 1

        # If we have HDFC BANK and SAVINGS ACCOUNT, that's distinctive enough
        if re.search(r"HDFC BANK", first_page_text, re.IGNORECASE) and re.search(
            r"SAVINGS ACCOUNT", first_page_text, re.IGNORECASE
        ):
            return True

        # Otherwise, need at least 2 matches
        return matches >= 2

    except Exception as e:
        print(f"Error detecting HDFC statement: {str(e)}")
        return False


def parse_date(date_str, statement_year):
    """
    Parse a date string into a formatted date

    Args:
        date_str (str): Date string to parse (DD/MM/YY format)
        statement_year (int): Year to use for dates without year

    Returns:
        str: Formatted date in DD/MM/YYYY format, or None if parsing fails
    """
    try:
        # Convert YY to YYYY
        if "/" in date_str:
            day, month, year = date_str.split("/")
            if len(year) == 2:
                year = "20" + year
            date_obj = datetime.strptime(f"{day}/{month}/{year}", "%d/%m/%Y")
            return date_obj.strftime("%d/%m/%Y")
        else:
            return None
    except ValueError:
        print(f"Warning: Could not parse date format: {date_str}")
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
        "statement_year": datetime.now().year,  # Default to current year
        "account_holder": "Unknown",
        "account_num": "Unknown",
    }

    try:
        # Extract text from the first page
        first_page_text = doc[0].get_text()

        # Extract statement period
        statement_period_match = re.search(r"(\d{1,2}/\d{1,2}/\d{2})\s+to\s+(\d{1,2}/\d{1,2}/\d{2})", first_page_text)
        if statement_period_match:
            try:
                end_date_str = statement_period_match.group(2)  # End date has format "DD/MM/YY"
                day, month, year = end_date_str.split("/")
                metadata["statement_year"] = int("20" + year)
            except (ValueError, IndexError):
                print("Could not extract year from statement period, using current year")

        # Extract account holder
        account_holder_match = re.search(r"Account\s+Holder:\s*([A-Za-z\s]+)", first_page_text)
        if account_holder_match:
            metadata["account_holder"] = account_holder_match.group(1).strip()

        # Extract account number
        account_num_match = re.search(r"Account\s+No:\s*(\d+)", first_page_text)
        if account_num_match:
            metadata["account_num"] = account_num_match.group(1)

    except Exception as e:
        print(f"Error extracting statement metadata: {str(e)}")

    return metadata


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
        # Open PDF with PyMuPDF
        doc = fitz.open(pdf_path)
        print(f"Processing statement file with {len(doc)} pages")

        # Extract metadata
        metadata = extract_statement_metadata(doc)

        # Extract transactions
        transactions = extract_transactions(doc, metadata["statement_year"])
        print(f"Found {len(transactions)} potential transactions to process")

        # Sort transactions by date
        transactions.sort(key=lambda x: x["date"])

    except Exception as e:
        print(f"Error processing HDFC statement: {str(e)}")
        return []

    finally:
        # Close the PDF document
        if "doc" in locals() and doc:
            doc.close()

    return transactions


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

    # Process each page
    for page_num in range(len(doc)):
        page_text = doc[page_num].get_text()
        lines = page_text.split("\n")

        # Process each line
        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # Skip empty lines and headers/footers
            if not line or any(
                marker in line
                for marker in [
                    "PAGE",
                    "CONTACT US",
                    "5AM - 6PM",
                    "6PM - 5AM",
                    "ISSUED BY",
                    "Comment •",
                    "Transaction Details",
                    "Day/Night",
                    "Amount",
                    "Balance",
                ]
            ):
                i += 1
                continue

            # Check for date line (e.g., "02 May")
            date_match = re.match(r"^(\d{1,2}/\d{1,2}/\d{2})$", line)
            if date_match:
                current_date = parse_date(date_match.group(1), statement_year)
                i += 1
                continue

            if not current_date:
                i += 1
                continue

            # Look for transaction description
            if re.match(r"^[A-Z0-9/\s\-]+$", line):
                # Get amount and balance from next lines
                amount = None
                balance = None

                # Look for amount in next few lines
                for j in range(1, 4):  # Look up to 3 lines ahead
                    if i + j < len(lines):
                        amount_line = lines[i + j].strip()
                        if re.match(r"^[\d,]+\.\d{2}$", amount_line):
                            try:
                                # Remove commas and convert to float
                                amount = float(amount_line.replace(",", ""))
                                # Look for balance in next line
                                if i + j + 1 < len(lines):
                                    balance_line = lines[i + j + 1].strip()
                                    if re.match(r"^[\d,]+\.\d{2}$", balance_line):
                                        balance = float(balance_line.replace(",", ""))
                                        i = i + j + 2  # Skip processed lines
                                        break
                            except ValueError:
                                pass

                if amount is not None and balance is not None:
                    # Determine if credit or debit
                    is_credit = False

                    # Check for credit indicators
                    if any(indicator in line for indicator in ["CREDIT", "SALARY", "INTEREST", "REFUND"]):
                        is_credit = True
                    # Check for debit indicators
                    elif any(indicator in line for indicator in ["DEBIT", "ATM", "POS", "TRANSFER", "PAYMENT"]):
                        is_credit = False
                    # If still unsure, use balance change
                    else:
                        # Compare with previous transaction's balance
                        if transactions:
                            prev_balance = transactions[-1].get("balance", 0)
                            is_credit = balance > prev_balance

                    # Create transaction dictionary
                    transaction = {
                        "date": current_date,
                        "description": line,
                        "amount": amount if is_credit else -amount,
                        "type": "credit" if is_credit else "debit",
                        "category": "Uncategorized",
                        "account": "HDFC Savings",
                        "account_type": "savings",
                        "bank": "HDFC",
                        "account_name": "HDFC Savings Account",
                        "is_debit": not is_credit,
                        "transaction_id": f"{current_date}_{amount}_{len(transactions)}",
                        "balance": balance,
                        "sort_key": (0, balance),  # Default priority
                    }

                    transactions.append(transaction)
                    continue

            i += 1

    # Sort transactions by date and sort key
    transactions.sort(key=lambda x: (x["date"], x.get("sort_key", (0, 0))))

    return transactions


class HDFCSavingsParser:
    """
    HDFC Savings Account Parser class to match the expected interface
    """
    
    def __init__(self):
        self.bank_name = "HDFC Bank"
        self.account_type = "Savings"
    
    def detect(self, pdf_path):
        """
        Detect if a PDF is an HDFC savings account statement
        
        Args:
            pdf_path (str): Path to the PDF file
            
        Returns:
            bool: True if it's an HDFC savings statement, False otherwise
        """
        return detect_hdfc_savings(pdf_path)
    
    def parse(self, pdf_path):
        """
        Parse HDFC Bank statements
        
        Args:
            pdf_path (str): Path to the PDF statement file
            
        Returns:
            list: List of transaction dictionaries with transaction details
        """
        return extract_hdfc_savings(pdf_path)
