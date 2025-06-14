# Content from the hdfc-credit-card-parser artifact
import re
from datetime import datetime

import pdfplumber


def extract_hdfc_credit_card(pdf_path):
    """
    Specialized parser for HDFC Credit Card statements
    Returns a list of transaction dictionaries
    """
    transactions = []
    statement_date = None
    payment_due_date = None

    with pdfplumber.open(pdf_path) as pdf:
        # First pass: extract header information
        for page_num, page in enumerate(pdf.pages):
            text = page.extract_text()

            # Extract statement date
            statement_date_match = re.search(r"Statement Date:(\d{2}/\d{2}/\d{4})", text)
            if statement_date_match:
                statement_date = statement_date_match.group(1)

            # Extract payment due date
            payment_due_match = re.search(r"Payment Due Date\s+(\d{2}/\d{2}/\d{4})", text)
            if payment_due_match:
                payment_due_date = payment_due_match.group(1)

            # Look for the transactions section
            if "Domestic Transactions" in text:
                # Extract transaction table
                tables = page.extract_tables()

                for table in tables:
                    # Check if this looks like a transaction table
                    is_transaction_table = False
                    for row in table:
                        if len(row) >= 3 and any(
                            header in str(row) for header in ["Date", "Transaction Description", "Amount"]
                        ):
                            is_transaction_table = True
                            break

                    if not is_transaction_table:
                        continue

                    # Process the transaction table
                    header_row = None
                    date_col = None
                    desc_col = None
                    amount_col = None

                    # Identify column positions
                    for i, row in enumerate(table):
                        if row and any(
                            header in str(cell) for cell in row for header in ["Date", "Transaction Description", "Amount"]
                        ):
                            header_row = i
                            for j, cell in enumerate(row):
                                if cell and "Date" in str(cell):
                                    date_col = j
                                elif cell and "Transaction Description" in str(cell):
                                    desc_col = j
                                elif cell and "Amount" in str(cell):
                                    amount_col = j
                            break

                    # Skip if we couldn't identify the columns
                    if header_row is None or date_col is None or desc_col is None or amount_col is None:
                        continue

                    # Process transaction rows
                    for i in range(header_row + 1, len(table)):
                        row = table[i]

                        # Skip empty rows or rows with insufficient data
                        if not row or len(row) <= max(date_col, desc_col, amount_col) or not row[date_col]:
                            continue

                        try:
                            # Extract date
                            date_str = str(row[date_col]).strip()

                            # Handle date formats with time
                            if re.match(r"^\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2}$", date_str.strip()):
                                date_obj = datetime.strptime(date_str, "%d/%m/%Y %H:%M:%S")
                                # Format as DD/MM/YYYY
                                date = date_obj.strftime("%d/%m/%Y")
                            else:
                                # If it's already in DD/MM/YYYY format, use it directly
                                if re.match(r"^\d{2}/\d{2}/\d{4}$", date_str.strip()):
                                    date = date_str
                                else:
                                    # Parse and reformat for consistency
                                    date_obj = datetime.strptime(date_str, "%d/%m/%Y")
                                    date = date_obj.strftime("%d/%m/%Y")

                            # Extract description
                            description = str(row[desc_col]).strip()
                            if not description:
                                continue

                            # Extract amount
                            amount_str = str(row[amount_col]).strip()
                            # Remove non-numeric characters except decimal point
                            amount_str = re.sub(r"[^\d.-]", "", amount_str)

                            # Skip if we can't parse a proper amount
                            if not amount_str:
                                continue

                            # IMPORTANT: For credit card, always treat as expense (negative)
                            # Ignoring original sign - force all to negative
                            amount = -abs(float(amount_str))

                            # Create transaction record
                            transaction = {
                                "date": date,
                                "description": description,
                                "amount": amount,
                                "bank": "HDFC",
                                "account_type": "credit_card",
                                "account_name": "HDFC Credit Card",
                                "statement_date": statement_date,
                                "payment_due_date": payment_due_date,
                                "source": "HDFC Credit Card",
                                "notes": "",
                                "confidence": "High",  # Direct extraction from statement
                            }

                            transactions.append(transaction)
                        except (ValueError, TypeError) as e:
                            # Skip problematic rows
                            continue

            # Look for International Transactions section if it exists
            if "International Transactions" in text:
                # Similar extraction logic for international transactions...
                # This would be very similar to the domestic transactions logic
                pass

    return transactions


def detect_hdfc_credit_card(pdf_path):
    """
    Detect if this PDF is an HDFC Credit Card statement
    Returns True if it looks like an HDFC Credit Card statement
    """
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if "HDFC Bank Credit Card" in text and "Statement" in text:
                    return True
        return False
    except Exception:
        return False
