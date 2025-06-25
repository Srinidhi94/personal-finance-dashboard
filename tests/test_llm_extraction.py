#!/usr/bin/env python3
"""
Comprehensive test for LLM-based transaction extraction using actual PDF files.
Tests the complete pipeline from PDF text extraction to LLM parsing.
"""

import sys
import os
import logging
import json
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import required modules
from parsers.universal_llm_parser import UniversalLLMParser
from llm_services.llm_service import LLMService
from llm_services.llm_service_mock import MockLLMService
from utils.pdf_utils import extract_text_from_pdf

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class LLMExtractionTester:
    """Test LLM extraction with actual PDF files."""
    
    def __init__(self):
        self.pdf_folder = project_root / "uploads" / "Account_Statements"
        self.results = {}
        
    def test_all_pdfs(self):
        """Test LLM extraction with all PDF files."""
        if not self.pdf_folder.exists():
            logger.error(f"PDF folder not found: {self.pdf_folder}")
            return
        
        pdf_files = list(self.pdf_folder.glob("*.pdf"))
        if not pdf_files:
            logger.error(f"No PDF files found in {self.pdf_folder}")
            return
        
        logger.info(f"Found {len(pdf_files)} PDF files to test")
        
        for pdf_file in pdf_files:
            logger.info(f"\n{'='*80}")
            logger.info(f"Testing: {pdf_file.name}")
            logger.info(f"{'='*80}")
            
            try:
                result = self.test_single_pdf(pdf_file)
                self.results[pdf_file.name] = result
                
                # Log summary
                if result['success']:
                    logger.info(f"✅ {pdf_file.name}: {result['transaction_count']} transactions extracted")
                    logger.info(f"   Total Credits: ₹{result['total_credits']:,.2f}")
                    logger.info(f"   Total Debits: ₹{result['total_debits']:,.2f}")
                    logger.info(f"   Net Amount: ₹{result['net_amount']:,.2f}")
                else:
                    logger.error(f"❌ {pdf_file.name}: {result['error']}")
                    
            except Exception as e:
                logger.error(f"❌ {pdf_file.name}: Unexpected error - {e}")
                self.results[pdf_file.name] = {
                    'success': False,
                    'error': str(e),
                    'transaction_count': 0
                }
        
        # Print final summary
        self.print_summary()
    
    def test_single_pdf(self, pdf_file: Path) -> dict:
        """Test LLM extraction with a single PDF file."""
        try:
            # Step 1: Extract text from PDF
            logger.info("Step 1: Extracting text from PDF...")
            pdf_text = extract_text_from_pdf(str(pdf_file))
            
            if not pdf_text or len(pdf_text.strip()) < 100:
                return {
                    'success': False,
                    'error': 'PDF text extraction failed or insufficient text',
                    'transaction_count': 0
                }
            
            logger.info(f"Extracted {len(pdf_text)} characters from PDF")
            
            # Step 2: Determine bank name from filename
            bank_name = self.determine_bank_name(pdf_file.name)
            logger.info(f"Detected bank: {bank_name}")
            
            # Step 3: Test with real LLM service first
            logger.info("Step 2: Testing with real LLM service...")
            llm_result = self.test_with_real_llm(pdf_text, bank_name)
            
            if llm_result['success']:
                logger.info("✅ Real LLM service worked!")
                return llm_result
            else:
                logger.warning(f"⚠️ Real LLM failed: {llm_result['error']}")
                
            # Step 4: Fallback to mock LLM service
            logger.info("Step 3: Falling back to mock LLM service...")
            mock_result = self.test_with_mock_llm(pdf_text, bank_name)
            
            if mock_result['success']:
                logger.info("✅ Mock LLM service worked!")
                mock_result['llm_type'] = 'mock'
                return mock_result
            else:
                return {
                    'success': False,
                    'error': f"Both real and mock LLM failed. Real: {llm_result['error']}, Mock: {mock_result['error']}",
                    'transaction_count': 0
                }
                
        except Exception as e:
            logger.error(f"Error testing {pdf_file.name}: {e}")
            return {
                'success': False,
                'error': str(e),
                'transaction_count': 0
            }
    
    def test_with_real_llm(self, pdf_text: str, bank_name: str) -> dict:
        """Test with real LLM service."""
        try:
            # Initialize real LLM service
            llm_service = LLMService()
            
            # Test connection
            if not self.test_llm_connection(llm_service):
                return {
                    'success': False,
                    'error': 'LLM service connection failed',
                    'transaction_count': 0
                }
            
            # Parse with LLM
            transactions = llm_service.parse_bank_statement(pdf_text, bank_name)
            
            if not transactions:
                return {
                    'success': False,
                    'error': 'LLM returned no transactions',
                    'transaction_count': 0
                }
            
            # Calculate totals
            totals = self.calculate_totals(transactions)
            
            return {
                'success': True,
                'llm_type': 'real',
                'transaction_count': len(transactions),
                'transactions': transactions[:5],  # First 5 for logging
                'all_transactions': transactions,
                **totals
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'transaction_count': 0
            }
    
    def test_with_mock_llm(self, pdf_text: str, bank_name: str) -> dict:
        """Test with mock LLM service."""
        try:
            # Initialize mock LLM service
            mock_service = MockLLMService()
            
            # Parse with mock LLM
            transactions = mock_service.parse_bank_statement(pdf_text, bank_name)
            
            if not transactions:
                return {
                    'success': False,
                    'error': 'Mock LLM returned no transactions',
                    'transaction_count': 0
                }
            
            # Calculate totals
            totals = self.calculate_totals(transactions)
            
            return {
                'success': True,
                'llm_type': 'mock',
                'transaction_count': len(transactions),
                'transactions': transactions[:5],  # First 5 for logging
                'all_transactions': transactions,
                **totals
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'transaction_count': 0
            }
    
    def test_llm_connection(self, llm_service: LLMService) -> bool:
        """Test if LLM service is accessible."""
        try:
            # Try a simple health check
            test_response = llm_service._call_llm_with_retry("Test connection", timeout=5)
            return bool(test_response)
        except Exception as e:
            logger.warning(f"LLM connection test failed: {e}")
            return False
    
    def determine_bank_name(self, filename: str) -> str:
        """Determine bank name from filename."""
        filename_lower = filename.lower()
        
        if 'federal' in filename_lower:
            return 'Federal Bank'
        elif 'hdfc' in filename_lower:
            return 'HDFC Bank'
        else:
            return 'Unknown Bank'
    
    def calculate_totals(self, transactions: list) -> dict:
        """Calculate transaction totals."""
        total_credits = 0.0
        total_debits = 0.0
        
        for txn in transactions:
            amount = float(txn.get('amount', 0))
            txn_type = txn.get('type', '').lower()
            
            if txn_type == 'credit' or amount > 0:
                total_credits += abs(amount)
            else:
                total_debits += abs(amount)
        
        return {
            'total_credits': total_credits,
            'total_debits': total_debits,
            'net_amount': total_credits - total_debits
        }
    
    def print_summary(self):
        """Print test summary."""
        logger.info(f"\n{'='*80}")
        logger.info("TEST SUMMARY")
        logger.info(f"{'='*80}")
        
        total_files = len(self.results)
        successful_files = sum(1 for r in self.results.values() if r['success'])
        failed_files = total_files - successful_files
        
        logger.info(f"Total PDF files tested: {total_files}")
        logger.info(f"Successful extractions: {successful_files}")
        logger.info(f"Failed extractions: {failed_files}")
        
        if successful_files > 0:
            logger.info(f"\n{'='*40}")
            logger.info("SUCCESSFUL EXTRACTIONS:")
            logger.info(f"{'='*40}")
            
            for filename, result in self.results.items():
                if result['success']:
                    llm_type = result.get('llm_type', 'unknown')
                    logger.info(f"{filename} ({llm_type} LLM):")
                    logger.info(f"  - Transactions: {result['transaction_count']}")
                    logger.info(f"  - Credits: ₹{result.get('total_credits', 0):,.2f}")
                    logger.info(f"  - Debits: ₹{result.get('total_debits', 0):,.2f}")
                    logger.info(f"  - Net: ₹{result.get('net_amount', 0):,.2f}")
                    
                    # Show sample transactions
                    if 'transactions' in result:
                        logger.info("  - Sample transactions:")
                        for i, txn in enumerate(result['transactions'][:3]):
                            logger.info(f"    {i+1}. {txn.get('date')} | {txn.get('description', '')[:50]}... | ₹{txn.get('amount', 0):,.2f}")
        
        if failed_files > 0:
            logger.info(f"\n{'='*40}")
            logger.info("FAILED EXTRACTIONS:")
            logger.info(f"{'='*40}")
            
            for filename, result in self.results.items():
                if not result['success']:
                    logger.info(f"{filename}: {result['error']}")
        
        # Save detailed results to file
        results_file = project_root / "test_results_llm_extraction.json"
        with open(results_file, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        logger.info(f"\nDetailed results saved to: {results_file}")

def main():
    """Main test function."""
    logger.info("Starting LLM extraction tests with actual PDF files...")
    
    tester = LLMExtractionTester()
    tester.test_all_pdfs()
    
    logger.info("LLM extraction tests completed!")

if __name__ == "__main__":
    main() 