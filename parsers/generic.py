import re
import pdfplumber
from datetime import datetime

def extract_generic_transactions(pdf_path):
    """Extract transactions from a generic PDF statement"""
    transactions = []
    
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            
            # Generic pattern: Date, Description, Amount
            # Try multiple date formats and amount patterns
            patterns = [
                # DD/MM/YYYY Description Amount
                r'(\d{2}/\d{2}/\d{4})\s+([A-Za-z0-9\s.,&\-]+?)\s+([-+]?\d+\.?\d*)',
                
                # DD-MM-YYYY Description Amount
                r'(\d{2}-\d{2}-\d{4})\s+([A-Za-z0-9\s.,&\-]+?)\s+([-+]?\d+\.?\d*)',
                
                # YYYY/MM/DD Description Amount
                r'(\d{4}/\d{2}/\d{2})\s+([A-Za-z0-9\s.,&\-]+?)\s+([-+]?\d+\.?\d*)',
            ]
            
            for pattern in patterns:
                matches = re.finditer(pattern, text)
                
                for match in matches:
                    date_str, description, amount_str = match.groups()
                    
                    # Convert date to standard format DD/MM/YYYY
                    try:
                        if '/' in date_str:
                            if date_str[2] == '/':  # DD/MM/YYYY
                                date = datetime.strptime(date_str, '%d/%m/%Y').strftime('%d/%m/%Y')
                            else:  # YYYY/MM/DD
                                date_obj = datetime.strptime(date_str, '%Y/%m/%d')
                                date = date_obj.strftime('%d/%m/%Y')
                        else:  # DD-MM-YYYY
                            date_obj = datetime.strptime(date_str, '%d-%m-%Y')
                            date = date_obj.strftime('%d/%m/%Y')
                    except ValueError:
                        # Skip if date format doesn't match
                        continue
                    
                    # Clean description and amount
                    description = description.strip()
                    
                    # Convert to float and make negative (all are expenses)
                    amount = -abs(float(amount_str))
                    
                    transactions.append({
                        'date': date,
                        'description': description,
                        'amount': amount,
                        'category': 'Uncategorized',
                        'subcategory': '',
                        'bank': 'Unknown',
                        'account_type': 'Unknown',
                        'account_name': 'Unknown',
                        'source': 'Generic PDF',
                        'notes': '',
                        'confidence': 'Low'
                    })
    
    return transactions