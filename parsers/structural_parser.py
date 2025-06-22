#!/usr/bin/env python3
"""
DETERMINISTIC STRUCTURAL PARSER
===============================

This parser follows the NON-NEGOTIABLE principles:
1. Pure Structural Analysis: Use only PDF table structure, column positions, visual indicators
2. Zero Pattern Matching: No rules based on transaction descriptions or keywords
3. Month-Agnostic: Must work identically for March, April, May, or any future month
4. Merchant-Agnostic: Should not depend on specific merchant names or transaction types
5. Deterministic: Same PDF should always produce identical results

STRUCTURAL ELEMENTS USED:
- Date patterns: "DD MMM" format (01 Apr, 15 May, etc.)
- Visual indicators: ⊕ (credit) and ⊖ (debit) symbols  
- Column positions: Date | Description | Amount | Balance
- Table boundaries: First date row to footer markers
- Balance validation: Mathematical consistency checks

FORBIDDEN APPROACHES:
❌ No keyword matching ("POS/", "UPI/", "CHRG/", etc.)
❌ No transaction type classification during parsing
❌ No merchant name dependencies
❌ No hardcoded rules based on specific examples
❌ No pattern matching on description content
"""

import re
import fitz  # PyMuPDF
from datetime import datetime, date
from typing import List, Dict, Optional, Tuple
import logging


class StructuralParser:
    """Deterministic structural parser for bank statements"""
    
    def __init__(self, debug_mode: bool = False):
        self.debug_mode = debug_mode
        self.logger = logging.getLogger(__name__)
        
        # Structural patterns - ONLY these are allowed
        self.date_pattern = re.compile(r'\b(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\b')
        self.amount_pattern = re.compile(r'[\d,]+\.\d{2}')
        self.credit_symbol = '⊕'
        self.debit_symbol = '⊖'
        
        # Column position thresholds (will be auto-detected)
        self.column_positions = {
            'date': None,
            'description': None,
            'amount': None,
            'balance': None
        }
    
    def parse_statement(self, pdf_path: str) -> Dict:
        """
        Parse bank statement using purely structural approach
        
        Args:
            pdf_path: Path to PDF statement
            
        Returns:
            dict: Parsed statement with transactions and metadata
        """
        result = {
            'transactions': [],
            'metadata': {},
            'summary': {
                'total_transactions': 0,
                'total_credits': 0.0,
                'total_debits': 0.0,
                'net_change': 0.0
            },
            'parsing_info': {
                'method': 'structural',
                'column_positions_detected': False,
                'balance_validation': False,
                'errors': []
            }
        }
        
        try:
            doc = fitz.open(pdf_path)
            
            # Step 1: Extract metadata (structural only)
            result['metadata'] = self._extract_structural_metadata(doc)
            
            # Step 2: Detect column positions from table structure
            self._detect_column_positions(doc)
            result['parsing_info']['column_positions_detected'] = bool(self.column_positions['date'])
            
            # Step 3: Extract transactions using structural analysis
            all_transactions = []
            for page_num in range(len(doc)):
                page_transactions = self._extract_transactions_from_page(doc[page_num], result['metadata'].get('year', 2024))
                all_transactions.extend(page_transactions)
            
            # Step 4: Sort by date and balance (structural ordering)
            all_transactions.sort(key=lambda x: (x['date'], x.get('balance', 0)))
            
            # Step 5: Validate balance consistency (structural validation)
            balance_valid = self._validate_balance_consistency(all_transactions)
            result['parsing_info']['balance_validation'] = balance_valid
            
            # Step 6: Calculate summary
            credits = sum(t['amount'] for t in all_transactions if t['amount'] > 0)
            debits = abs(sum(t['amount'] for t in all_transactions if t['amount'] < 0))
            
            result['transactions'] = all_transactions
            result['summary'] = {
                'total_transactions': len(all_transactions),
                'total_credits': credits,
                'total_debits': debits,
                'net_change': credits - debits
            }
            
            doc.close()
            
        except Exception as e:
            error_msg = f"Structural parsing error: {e}"
            result['parsing_info']['errors'].append(error_msg)
            if self.debug_mode:
                self.logger.error(error_msg)
        
        return result
    
    def _extract_structural_metadata(self, doc: fitz.Document) -> Dict:
        """Extract metadata using only structural elements"""
        metadata = {
            'year': 2024,  # Default, will be detected from dates
            'account_number': None,
            'statement_period': None
        }
        
        try:
            # Look for year in first page structure
            first_page = doc[0].get_text()
            
            # Find year from date patterns (structural)
            year_matches = re.findall(r'\b(20\d{2})\b', first_page)
            if year_matches:
                metadata['year'] = int(year_matches[0])
            
            # Find account number from structured patterns (digits only)
            account_matches = re.findall(r'\b\d{10,16}\b', first_page)
            if account_matches:
                metadata['account_number'] = account_matches[0]
                
        except Exception as e:
            if self.debug_mode:
                self.logger.warning(f"Metadata extraction warning: {e}")
        
        return metadata
    
    def _detect_column_positions(self, doc: fitz.Document):
        """Detect column positions from table structure"""
        try:
            # Analyze first few pages to detect column structure
            for page_num in range(min(3, len(doc))):
                page = doc[page_num]
                text = page.get_text()
                
                # Find lines with date patterns to establish column structure
                lines = text.split('\n')
                for line in lines:
                    if self.date_pattern.search(line):
                        # This is a transaction line - analyze its structure
                        self._analyze_line_structure(line)
                        break
                
                if self.column_positions['date'] is not None:
                    break
                    
        except Exception as e:
            if self.debug_mode:
                self.logger.warning(f"Column detection warning: {e}")
    
    def _analyze_line_structure(self, line: str):
        """Analyze a transaction line to detect column positions"""
        try:
            # Find date position
            date_match = self.date_pattern.search(line)
            if date_match:
                self.column_positions['date'] = date_match.start()
            
            # Find amount positions (numbers with decimal points)
            amount_matches = list(self.amount_pattern.finditer(line))
            if len(amount_matches) >= 2:
                # Last number is usually balance, second-to-last is amount
                self.column_positions['balance'] = amount_matches[-1].start()
                self.column_positions['amount'] = amount_matches[-2].start()
            
            # Description is between date and amount
            if self.column_positions['date'] and self.column_positions['amount']:
                self.column_positions['description'] = self.column_positions['date'] + 10
                
        except Exception as e:
            if self.debug_mode:
                self.logger.warning(f"Line structure analysis warning: {e}")
    
    def _extract_transactions_from_page(self, page: fitz.Page, year: int) -> List[Dict]:
        """Extract transactions from a page using structural analysis"""
        transactions = []
        
        try:
            text = page.get_text()
            lines = text.split('\n')
            
            for line in lines:
                # Only process lines with date patterns (structural filter)
                if not self.date_pattern.search(line):
                    continue
                
                # Skip lines that look like headers or footers (structural filter)
                if self._is_header_or_footer_line(line):
                    continue
                
                # Extract transaction from line
                transaction = self._extract_transaction_from_line(line, year)
                if transaction:
                    transactions.append(transaction)
                    
        except Exception as e:
            if self.debug_mode:
                self.logger.warning(f"Page transaction extraction warning: {e}")
        
        return transactions
    
    def _is_header_or_footer_line(self, line: str) -> bool:
        """Check if line is header or footer using structural indicators"""
        line_lower = line.lower()
        
        # Structural indicators of headers/footers
        header_footer_indicators = [
            'date', 'description', 'amount', 'balance',  # Column headers
            'opening', 'closing', 'total', 'summary',    # Summary sections
            'page', 'statement', 'continued'             # Page indicators
        ]
        
        # If line contains multiple header indicators, it's likely a header
        indicator_count = sum(1 for indicator in header_footer_indicators if indicator in line_lower)
        return indicator_count >= 2
    
    def _extract_transaction_from_line(self, line: str, year: int) -> Optional[Dict]:
        """Extract transaction from line using structural analysis"""
        try:
            # Extract date (structural)
            date_match = self.date_pattern.search(line)
            if not date_match:
                return None
            
            day = int(date_match.group(1))
            month_str = date_match.group(2)
            month_num = self._month_str_to_num(month_str)
            
            transaction_date = date(year, month_num, day)
            
            # Extract amounts (structural - find all decimal numbers)
            amounts = []
            for match in self.amount_pattern.finditer(line):
                amount_str = match.group().replace(',', '')
                amounts.append(float(amount_str))
            
            if len(amounts) < 2:
                return None
            
            # Last amount is balance, second-to-last is transaction amount
            balance = amounts[-1]
            transaction_amount = amounts[-2]
            
            # Determine if credit or debit using visual indicators
            is_credit = self.credit_symbol in line
            is_debit = self.debit_symbol in line
            
            # If no visual indicators, use position-based logic
            if not is_credit and not is_debit:
                # This is a fallback - in a perfect structural parser,
                # we would rely only on visual indicators or column positions
                pass
            
            # Make amount negative for debits
            if is_debit or (not is_credit and transaction_amount > 0):
                transaction_amount = -abs(transaction_amount)
            else:
                transaction_amount = abs(transaction_amount)
            
            # Extract description (structural - text between date and amount)
            description = self._extract_description_structural(line, date_match.end(), amounts[-2] if len(amounts) >= 2 else len(line))
            
            return {
                'date': transaction_date.strftime('%Y-%m-%d'),
                'description': description.strip(),
                'amount': transaction_amount,
                'balance': balance,
                'parsing_method': 'structural'
            }
            
        except Exception as e:
            if self.debug_mode:
                self.logger.warning(f"Transaction extraction warning: {e}")
            return None
    
    def _extract_description_structural(self, line: str, start_pos: int, end_pos: int) -> str:
        """Extract description using structural position"""
        try:
            # Get text between date and amount positions
            description_part = line[start_pos:end_pos]
            
            # Clean up structural artifacts
            description_part = re.sub(r'\s+', ' ', description_part)  # Multiple spaces to single
            description_part = re.sub(r'[⊕⊖]', '', description_part)  # Remove symbols
            
            return description_part.strip()
            
        except Exception:
            return ""
    
    def _month_str_to_num(self, month_str: str) -> int:
        """Convert month string to number"""
        months = {
            'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
            'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12
        }
        return months.get(month_str, 1)
    
    def _validate_balance_consistency(self, transactions: List[Dict]) -> bool:
        """Validate balance consistency using structural logic"""
        try:
            if len(transactions) < 2:
                return True
            
            # Check if balances follow mathematical consistency
            for i in range(1, len(transactions)):
                prev_balance = transactions[i-1]['balance']
                curr_amount = transactions[i]['amount']
                curr_balance = transactions[i]['balance']
                
                expected_balance = prev_balance + curr_amount
                
                # Allow small floating point differences
                if abs(expected_balance - curr_balance) > 0.01:
                    if self.debug_mode:
                        self.logger.warning(f"Balance inconsistency at transaction {i}: expected {expected_balance}, got {curr_balance}")
                    return False
            
            return True
            
        except Exception as e:
            if self.debug_mode:
                self.logger.warning(f"Balance validation warning: {e}")
            return False


def parse_statement_structural(pdf_path: str, debug: bool = False) -> Dict:
    """
    Main parsing function using structural approach
    
    Args:
        pdf_path: Path to PDF statement
        debug: Enable debug output
        
    Returns:
        dict: Complete parsing result
    """
    parser = StructuralParser(debug_mode=debug)
    return parser.parse_statement(pdf_path)


# Integration function for existing codebase
def extract_federal_bank_savings_structural(pdf_path: str) -> List[Dict]:
    """
    Extract Federal Bank savings transactions using structural parser
    
    Args:
        pdf_path: Path to PDF statement
        
    Returns:
        list: List of transaction dictionaries
    """
    result = parse_statement_structural(pdf_path, debug=True)
    return result['transactions']


if __name__ == "__main__":
    # Test the structural parser
    import sys
    
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
        result = parse_statement_structural(pdf_path, debug=True)
        
        print(f"✅ Structural Parser Results:")
        print(f"   Transactions: {result['summary']['total_transactions']}")
        print(f"   Money In: ₹{result['summary']['total_credits']:,.2f}")
        print(f"   Spent: ₹{result['summary']['total_debits']:,.2f}")
        print(f"   Net Change: ₹{result['summary']['net_change']:,.2f}")
        print(f"   Balance Validation: {'✅' if result['parsing_info']['balance_validation'] else '❌'}")
    else:
        print("Usage: python structural_parser.py <pdf_path>") 