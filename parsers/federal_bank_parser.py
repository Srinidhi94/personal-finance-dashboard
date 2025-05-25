"""
Federal Bank Parser - Consolidated Version

This parser extracts transactions from Federal Bank statements using a table-based approach.
It identifies transactions based on the date column and uses the arrow next to the amount or
balance changes to determine whether a transaction is an income or expense.
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
        
        # Extract text from the first few pages
        full_text = ""
        for p in range(min(3, len(doc))):  # Check first 3 pages at most
            full_text += doc[p].get_text()
        
        # Close the document
        doc.close()
        
        # Check for structural elements common in Federal Bank statements
        has_account_number = re.search(r'Account\s+No\.\s*\d+', full_text) is not None
        has_statement_period = re.search(r'\d{1,2}\s+[A-Z][a-z]{2}\s+\d{4}\s+to\s+\d{1,2}\s+[A-Z][a-z]{2}\s+\d{4}', full_text) is not None
        has_transaction_section = re.search(r'(TRANSACTION DETAILS|STATEMENTS OF ACCOUNT)', full_text.upper()) is not None
        has_amount_format = len(re.findall(r'\d{1,3}(?:,\d{3})*\.\d{2}', full_text)) > 5  # Multiple currency amounts
        has_federal_bank_text = "FEDERAL BANK" in full_text.upper()
        
        # If it has most of the structural elements, consider it a valid statement
        score = sum([has_account_number, has_statement_period, has_transaction_section, has_amount_format, has_federal_bank_text])
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
                print(f"Statement period year: {metadata['statement_year']}")
            except:
                print("Could not extract year from statement period, using current year")
        
        # Extract account holder
        account_holder_match = re.search(r'Account\s+Holder:\s*([A-Za-z\s]+)', first_page_text)
        if not account_holder_match:
            # Try alternative pattern - look for a name at the top of the statement
            name_lines = first_page_text.split('\n')[:10]  # Check first 10 lines
            for line in name_lines:
                if re.match(r'^[A-Za-z\s]+$', line.strip()) and len(line.strip()) > 3:
                    metadata["account_holder"] = line.strip()
                    break
        else:
            metadata["account_holder"] = account_holder_match.group(1).strip()
            
        # Extract account number
        account_num_match = re.search(r'Account\s+No\.\s*(\d+)', first_page_text)
        if account_num_match:
            metadata["account_num"] = account_num_match.group(1)
        else:
            # Try alternative pattern - look for "SAVINGS A/C NO" or similar
            account_num_match = re.search(r'SAVINGS\s+A/C\s+NO\s*(\d+)', first_page_text.upper())
            if account_num_match:
                metadata["account_num"] = account_num_match.group(1)
            
        print(f"Account Holder: {metadata['account_holder']}, Account Number: {metadata['account_num']}")
        
    except Exception as e:
        print(f"Error extracting statement metadata: {str(e)}")
        
    return metadata


def find_transaction_tables(doc):
    """
    Find transaction tables in the document
    
    Args:
        doc: PyMuPDF document object
        
    Returns:
        list: List of (page_num, start_line, end_line) tuples for each transaction table
    """
    tables = []
    
    for page_num in range(len(doc)):
        page_text = doc[page_num].get_text()
        lines = page_text.split('\n')
        
        print(f"\nScanning page {page_num+1} for transaction tables...")
        print(f"Page has {len(lines)} lines")
        
        # Print some sample lines to help debug
        print("Sample lines from this page:")
        for i in range(min(20, len(lines))):
            print(f"Line {i}: {lines[i]}")
        
        # Find table headers - Federal Bank statements have a specific structure:
        # Date, Day/Night, Transaction Details, Amount, Balance on separate lines
        table_start = None
        
        # Look for the pattern of headers that indicates a transaction table
        for i in range(len(lines) - 6):  # Need at least 6 lines for the header pattern
            if (i + 6 < len(lines) and 
                "Date" in lines[i] and 
                "Day/Night" in lines[i+1] and 
                "Transaction Details" in lines[i+2] and 
                "Amount" in lines[i+4] and 
                "Balance" in lines[i+5]):
                
                table_start = i
                print(f"Found transaction table header pattern at line {i} on page {page_num+1}")
                break
        
        # Alternative detection for different statement formats
        if table_start is None:
            for i, line in enumerate(lines):
                if "Date" in line:
                    print(f"Found 'Date' at line {i}: {line}")
                    # Check surrounding lines for other headers
                    next_few_lines = " ".join(lines[i:i+10]).upper()
                    print(f"Surrounding context: {next_few_lines}")
                    
                    if (("TRANSACTION" in next_few_lines or "DESCRIPTION" in next_few_lines) and 
                        "AMOUNT" in next_few_lines and "BALANCE" in next_few_lines):
                        table_start = i
                        print(f"Found transaction table at line {i} on page {page_num+1}")
                        break
        
        if table_start is not None:
            # Find where the table ends (usually at the end of the page or at a footer)
            table_end = len(lines)
            for i in range(table_start + 6, len(lines)):
                if any(marker in lines[i] for marker in ["PAGE", "CONTACT US", "In Spent Saved", "5AM - 6PM", "ISSUED BY"]):
                    table_end = i
                    print(f"Table ends at line {i}")
                    break
            
            tables.append((page_num, table_start, table_end))
            print(f"Added table: page {page_num+1}, lines {table_start}-{table_end}")
        else:
            print(f"No transaction table found on page {page_num+1}")
    
    print(f"Total tables found: {len(tables)}")
    return tables


def parse_date(date_str, statement_year):
    """
    Parse a date string into a formatted date
    
    Args:
        date_str (str): Date string to parse
        statement_year (int): Year to use for dates without year
        
    Returns:
        str: Formatted date in YYYY-MM-DD format, or None if parsing fails
    """
    try:
        if '/' in date_str:  # DD/MM/YYYY format
            date_obj = datetime.strptime(date_str, "%d/%m/%Y")
            return date_obj.strftime("%Y-%m-%d")
        else:  # DD MMM format
            date_obj = datetime.strptime(f"{date_str} {statement_year}", "%d %b %Y")
            return date_obj.strftime("%Y-%m-%d")
    except ValueError:
        return None


def extract_transactions_from_table(lines, statement_year):
    """
    Extract transactions from a table of lines
    
    Args:
        lines (list): List of text lines from the table
        statement_year (int): Year of the statement
        
    Returns:
        list: List of transaction dictionaries
    """
    transactions = []
    current_date = None
    date_patterns = [
        r'^(\d{2}\s+[A-Z][a-z]{2})$',  # DD MMM at start of line (exact match)
        r'^(\d{2}/\d{2}/\d{4})$',  # DD/MM/YYYY at start of line (exact match)
        r'^(\d{1,2}\s+[A-Z][a-z]{2})$'  # D MMM (single digit day) at start of line
    ]
    
    # Specific pattern for monetary amounts (with decimal point and commas)
    # This will match Indian currency format like 1,234.56 or 1,23,456.78
    amount_pattern = r'((?:[\d,]+\.\d{0,2})|(?:₹[\d,]+(?:\.\d{0,2})?))'
    
    # Add more debug output
    print(f"Using amount pattern: {amount_pattern}")
    
    # Skip header lines
    start_idx = 0
    for i in range(len(lines)):
        if i + 6 < len(lines) and "Date" in lines[i] and "Amount" in lines[i+4] and "Balance" in lines[i+5]:
            start_idx = i + 6  # Skip the header lines
            break
    
    print(f"Starting transaction extraction from line {start_idx}")
    
    # Group lines by date
    date_groups = []
    current_group = []
    current_date_str = None
    
    for i in range(start_idx, len(lines)):
        line = lines[i].strip()
        
        # Skip empty lines and footer lines
        if not line or any(marker in line for marker in ["PAGE", "CONTACT US", "In Spent Saved", "5AM - 6PM", "ISSUED BY"]):
            continue
        
        # Check if this is a date line
        is_date_line = False
        for pattern in date_patterns:
            match = re.match(pattern, line)
            if match:
                is_date_line = True
                # If we have a current group, add it to date_groups
                if current_group and current_date_str:
                    date_groups.append((current_date_str, current_group))
                
                # Start a new group
                current_date_str = match.group(1)
                current_group = []
                break
        
        if not is_date_line and line:
            current_group.append(line)
    
    # Add the last group if it exists
    if current_group and current_date_str:
        date_groups.append((current_date_str, current_group))
    
    print(f"Found {len(date_groups)} date groups")
    
    # Process each date group
    for date_str, group_lines in date_groups:
        formatted_date = parse_date(date_str, statement_year)
        if not formatted_date:
            print(f"Failed to parse date: {date_str}")
            continue
        
        print(f"Processing transactions for date: {formatted_date}")
        
        # Process transactions by looking at pairs of lines
        # First, collect all lines with amounts
        amount_lines = []
        for i, line in enumerate(group_lines):
            print(f"Processing line in date group {formatted_date}: {line}")
            
            # Check if this line contains an amount
            amount_matches = list(re.finditer(amount_pattern, line))
            
            if amount_matches:
                print(f"Found {len(amount_matches)} amount matches in line: {line}")
                for idx, match in enumerate(amount_matches):
                    print(f"  Match {idx}: {match.group(1)} at position {match.start()}-{match.end()}")
                amount_lines.append((i, line, amount_matches))
        
        # Now process pairs of amount lines as transactions
        for j in range(len(amount_lines) - 1):
            current_idx, current_line, current_matches = amount_lines[j]
            next_idx, next_line, next_matches = amount_lines[j + 1]
            
            # If these are consecutive amount lines, they might be a transaction
            if next_idx - current_idx <= 2:  # Allow for one line in between
                # Get description from lines before the first amount line
                description_lines = []
                
                # Look for description in previous lines (up to 3 lines back)
                for k in range(max(0, current_idx - 3), current_idx):
                    if k < len(group_lines):
                        # Skip lines that are just amounts
                        if not re.match(r'^\s*[\d,]+\.\d{0,2}\s*$', group_lines[k]):
                            description_lines.append(group_lines[k])
                
                # Add any text before the amount in the current line
                if current_matches:
                    first_amount_pos = current_matches[0].start()
                    if first_amount_pos > 0:
                        current_line_desc = current_line[:first_amount_pos].strip()
                        # Don't add if it's just a number (likely part of another transaction)
                        if not re.match(r'^\s*[\d,]+\.\d{0,2}\s*$', current_line_desc):
                            description_lines.append(current_line_desc)
                
                description = " ".join(description_lines).strip()
                
                # Clean up description - remove any trailing amounts
                description = re.sub(r'\s+[\d,]+\.\d{0,2}\s*$', '', description)
                
                # Extract transaction amount and balance
                amount_str = current_matches[0].group(1).replace(',', '').replace('₹', '')
                balance_str = next_matches[0].group(1).replace(',', '').replace('₹', '')
                
                print(f"Extracted: Description='{description}', Amount={amount_str}, Balance={balance_str}")
                
                try:
                    amount = float(amount_str)
                    balance = float(balance_str)
                    
                    # Determine if credit or debit based on description and other indicators
                    is_credit = None
                    
                    # Check for specific transaction types that indicate credits
                    credit_indicators = ["ForexMarkupRefund", "CREDIT", "DEPOSIT", "INTEREST", "REFUND", "UPI IN"]
                    if any(indicator in description for indicator in credit_indicators):
                        is_credit = True
                        print(f"Credit transaction based on description indicators")
                    
                    # Check for specific transaction types that indicate debits
                    debit_indicators = ["POS/", "TO INTL", "CHRG/", "Visa Other Chrgs"]
                    if any(indicator in description for indicator in debit_indicators):
                        is_credit = False
                        print(f"Debit transaction based on description indicators")
                    
                    # If still undetermined, use balance change if we have previous transactions
                    if is_credit is None and transactions:
                        prev_transaction = transactions[-1]
                        if prev_transaction.get('date') == formatted_date:  # Only compare within same date
                            prev_balance = prev_transaction.get('balance')
                            if prev_balance is not None:
                                is_credit = balance > prev_balance
                                print(f"Credit determination based on balance change: {is_credit}")
                    
                    # If still undetermined, default to debit (most common)
                    if is_credit is None:
                        is_credit = False
                        print(f"Defaulting to debit transaction")
                    
                    # Set the signed amount
                    signed_amount = amount if is_credit else -amount
                    
                    # Create a unique ID for this transaction
                    tx_id = f"{formatted_date}_{signed_amount}_{len(transactions)}"
                    
                    # Create transaction dictionary
                    transaction = {
                        "date": formatted_date,
                        "description": description,
                        "amount": signed_amount,
                        "type": "credit" if is_credit else "debit",
                        "category": "Uncategorized",
                        "account": "Federal Bank Savings",
                        "account_type": "savings",
                        "bank": "Federal Bank",
                        "account_name": "Federal Bank Savings Account",
                        "is_debit": not is_credit,
                        "transaction_id": tx_id,
                        "balance": balance
                    }
                    
                    transactions.append(transaction)
                    print(f"Added transaction: {description}, Amount: {signed_amount}, Balance: {balance}")
                    
                except ValueError as e:
                    print(f"Error parsing amount or balance: {amount_str}, {balance_str}, Error: {str(e)}")
        
    
    print(f"Extracted {len(transactions)} transactions from table")
    return transactions


def deduplicate_transactions(transactions):
    """
    Deduplicate transactions based on date, amount, and description
    
    Args:
        transactions (list): List of transaction dictionaries
        
    Returns:
        list: Deduplicated list of transaction dictionaries
    """
    # First, filter out transactions with very similar descriptions and same date
    filtered_transactions = []
    seen_descriptions = {}
    
    for tx in transactions:
        date = tx['date']
        desc = tx['description']
        amount = tx['amount']
        
        # Skip transactions with very large amounts that are likely duplicates
        if abs(amount) > 50000 and "UPI IN" in desc:
            # Check if we've seen a similar transaction with a smaller amount
            similar_key = f"{date}_UPI IN"
            if similar_key in seen_descriptions:
                continue
            seen_descriptions[similar_key] = True
        
        # Skip transactions with duplicate descriptions on the same date
        # that are likely the same transaction
        desc_key = f"{date}_{desc}"
        if desc_key in seen_descriptions:
            continue
        seen_descriptions[desc_key] = True
        
        filtered_transactions.append(tx)
    
    # Now do a more thorough deduplication
    unique_transactions = {}
    
    for tx in filtered_transactions:
        # Create a deduplication key using date, amount and abbreviated description
        desc_part = tx['description'][:20] if tx['description'] else ""
        dedup_key = f"{tx['date']}_{tx['amount']}_{desc_part}"
        
        # If we haven't seen this transaction before, add it
        if dedup_key not in unique_transactions:
            unique_transactions[dedup_key] = tx
        # If we have seen it, prefer the one with a balance if available
        elif tx.get('balance') is not None and unique_transactions[dedup_key].get('balance') is None:
            unique_transactions[dedup_key] = tx
    
    # Convert back to list and sort by date
    result = list(unique_transactions.values())
    result.sort(key=lambda x: (x["date"], x.get("balance", 0)))
    
    return result


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
        print(f"Processing Federal Bank statement file with {len(doc)} pages")
        
        # Extract metadata
        metadata = extract_statement_metadata(doc)
        
        # Find transaction tables
        tables = find_transaction_tables(doc)
        
        # Process each table
        all_transactions = []
        
        for page_num, start_line, end_line in tables:
            page_text = doc[page_num].get_text()
            lines = page_text.split('\n')[start_line:end_line]
            
            # Extract transactions from this table
            table_transactions = extract_transactions_from_table(lines, metadata["statement_year"])
            all_transactions.extend(table_transactions)
            
            print(f"Extracted {len(table_transactions)} transactions from table on page {page_num+1}")
        
        # Deduplicate transactions
        transactions = deduplicate_transactions(all_transactions)
        
        print(f"Final count: {len(transactions)} unique transactions after deduplication")
        
        # Print some statistics to help verify the extraction quality
        if transactions:
            # Group by transaction type
            type_counts = {}
            for tx in transactions:
                tx_type = tx["type"]
                type_counts[tx_type] = type_counts.get(tx_type, 0) + 1
            
            print("\nTransactions by type:")
            for type_name, count in type_counts.items():
                print(f"{type_name}: {count}")
            
            # Get date range
            dates = sorted(set(tx["date"] for tx in transactions))
            if dates:
                print(f"\nDate range: {dates[0]} to {dates[-1]}")
                print(f"Number of unique dates: {len(dates)}")
        
    except Exception as e:
        print(f"Error processing Federal Bank statement: {str(e)}")
        import traceback
        traceback.print_exc()
        return []
    
    finally:
        # Close the PDF document
        if 'doc' in locals() and doc:
            doc.close()
    
    return transactions
