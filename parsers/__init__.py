from .hdfc_credit_card import extract_hdfc_credit_card, detect_hdfc_credit_card
from .hdfc_savings import extract_hdfc_savings, detect_hdfc_savings 
from .generic import extract_generic_transactions
from .federal_bank import extract_federal_bank_savings, detect_federal_bank_savings

# Main function to determine parser and extract transactions
def extract_transactions_from_file(file_path, bank=None, account_type=None, account_name=None):
    """
    Extract transactions from a file based on bank and account type
    
    Args:
        file_path (str): Path to the bank statement file
        bank (str, optional): Bank identifier
        account_type (str, optional): Type of account (savings, credit_card, etc.)
        account_name (str, optional): Name for the account
    
    Returns:
        list: Extracted transactions
    """
    file_ext = file_path.rsplit('.', 1)[1].lower()
    
    if file_ext == 'csv':
        # Process CSV file
        import csv
        transactions = []
        try:
            with open(file_path, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    transaction = {
                        'date': row['date'],
                        'description': row['description'],
                        'amount': -abs(float(row['amount'])),  # IMPORTANT: Force all transactions to be negative (expenses)
                        'bank': row.get('bank', bank or 'Unknown'),
                        'account_type': row.get('account_type', account_type or 'Unknown'),
                        'account_name': row.get('account_name', account_name or 'Unknown'),
                        'category': 'Miscellaneous',
                        'subcategory': '',
                        'is_debit': True,  # Always mark as debit since all are expenses
                        'reference': '',
                        'source': 'CSV Import'
                    }
                    transactions.append(transaction)
            return transactions
        except Exception as e:
            print(f"Error processing CSV: {e}")
            return []
    
    elif file_ext == 'pdf':
        # Auto-detect statement type if not specified
        if not bank or not account_type:
            # Check for HDFC Credit Card
            if detect_hdfc_credit_card(file_path):
                bank = "HDFC"
                account_type = "credit_card"
                account_name = "HDFC Credit Card"
                print(f"Auto-detected statement type: HDFC Credit Card")
            # Check for HDFC Savings Account
            elif detect_hdfc_savings(file_path):
                bank = "HDFC"
                account_type = "savings"
                account_name = "HDFC Savings Account"
                print(f"Auto-detected statement type: HDFC Savings Account")
            # Check for Federal Bank Savings Account
            elif detect_federal_bank_savings(file_path):
                bank = "Federal Bank"
                account_type = "savings"
                account_name = "Federal Bank Savings Account"
                print(f"Auto-detected statement type: Federal Bank Savings Account")
            # Add more detectors here for additional banks and account types
        
        # Use the appropriate parser based on bank and account type
        if bank == "HDFC" and account_type == "credit_card":
            print(f"Using HDFC Credit Card parser")
            return extract_hdfc_credit_card(file_path)
        elif bank == "HDFC" and account_type == "savings":
            print(f"Using HDFC Savings parser")
            return extract_hdfc_savings(file_path)
        elif bank == "Federal Bank" and account_type == "savings":
            print(f"Using Federal Bank Savings parser")
            return extract_federal_bank_savings(file_path)
        else:
            # Generic PDF extraction as fallback
            print(f"Using generic PDF parser as fallback")
            return extract_generic_transactions(file_path)
    
    return []