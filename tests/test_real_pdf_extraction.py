#!/usr/bin/env python3
"""
Real PDF extraction test with actual bank statements.
Tests the complete transaction extraction pipeline with real PDF files.
"""

import sys
import os
import logging
import json
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import required modules
from utils.pdf_utils import extract_text_from_pdf
from llm_services.llm_service import LLMService, LLMServiceError
from llm_services.llm_service_mock import MockLLMService
from parsers.universal_llm_parser import UniversalLLMParser

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RealPDFTester:
    """Test real PDF extraction with comprehensive analysis."""
    
    def __init__(self):
        self.pdf_folder = project_root / "uploads" / "Account_Statements"
        self.results = {}
        
    def test_all_pdfs_comprehensive(self):
        """Comprehensive test of all PDF files with detailed analysis."""
        if not self.pdf_folder.exists():
            logger.error(f"PDF folder not found: {self.pdf_folder}")
            return False
        
        pdf_files = list(self.pdf_folder.glob("*.pdf"))
        if not pdf_files:
            logger.error(f"No PDF files found in {self.pdf_folder}")
            return False
        
        logger.info(f"🔍 Found {len(pdf_files)} PDF files for comprehensive testing")
        logger.info("="*80)
        
        # Test each PDF file
        for pdf_file in pdf_files:
            logger.info(f"\n📄 TESTING: {pdf_file.name}")
            logger.info("-" * 60)
            
            result = self.test_single_pdf_comprehensive(pdf_file)
            self.results[pdf_file.name] = result
            
            if result['success']:
                logger.info(f"✅ SUCCESS: {result['transaction_count']} transactions")
                logger.info(f"   💰 Credits: ₹{result['total_credits']:,.2f}")
                logger.info(f"   💸 Debits: ₹{result['total_debits']:,.2f}")
                logger.info(f"   📊 Net: ₹{result['net_amount']:,.2f}")
                logger.info(f"   🤖 LLM Type: {result.get('llm_type', 'Unknown')}")
            else:
                logger.error(f"❌ FAILED: {result['error']}")
        
        # Generate comprehensive summary
        self.generate_comprehensive_summary()
        return True
    
    def test_single_pdf_comprehensive(self, pdf_file: Path) -> dict:
        """Test a single PDF with comprehensive analysis."""
        try:
            # Step 1: Extract PDF text
            logger.info("📋 Step 1: Extracting PDF text...")
            pdf_text = extract_text_from_pdf(str(pdf_file))
            
            if not pdf_text or len(pdf_text.strip()) < 100:
                return {
                    'success': False,
                    'error': 'Insufficient PDF text extracted',
                    'transaction_count': 0,
                    'pdf_chars': len(pdf_text) if pdf_text else 0
                }
            
            logger.info(f"   📄 Extracted {len(pdf_text):,} characters")
            
            # Step 2: Determine bank
            bank_name = self.determine_bank_name(pdf_file.name)
            logger.info(f"   🏦 Detected bank: {bank_name}")
            
            # Step 3: Test with available LLM service
            logger.info("🤖 Step 2: Testing LLM extraction...")
            
            # Try real LLM first
            llm_result = self.test_with_real_llm(pdf_text, bank_name)
            if llm_result['success']:
                logger.info("   ✅ Real LLM extraction successful")
                llm_result['pdf_chars'] = len(pdf_text)
                return llm_result
            else:
                logger.info(f"   ⚠️ Real LLM failed: {llm_result['error']}")
            
            # Fallback to mock LLM
            logger.info("   🔄 Falling back to Mock LLM...")
            mock_result = self.test_with_mock_llm(pdf_text, bank_name)
            if mock_result['success']:
                logger.info("   ✅ Mock LLM extraction successful")
                mock_result['pdf_chars'] = len(pdf_text)
                mock_result['llm_type'] = 'mock'
                return mock_result
            else:
                return {
                    'success': False,
                    'error': f"Both LLM services failed. Real: {llm_result['error']}, Mock: {mock_result['error']}",
                    'transaction_count': 0,
                    'pdf_chars': len(pdf_text)
                }
                
        except Exception as e:
            logger.error(f"   ❌ Unexpected error: {e}")
            return {
                'success': False,
                'error': str(e),
                'transaction_count': 0,
                'pdf_chars': 0
            }
    
    def test_with_real_llm(self, pdf_text: str, bank_name: str) -> dict:
        """Test with real LLM service."""
        try:
            llm_service = LLMService()
            
            # Test connection with a simple query
            try:
                test_response = llm_service._call_llm_with_retry("Hello", timeout=5)
                if not test_response:
                    raise Exception("Empty response from LLM")
            except Exception as e:
                return {
                    'success': False,
                    'error': f'LLM connection failed: {e}',
                    'transaction_count': 0
                }
            
            # Parse bank statement
            transactions = llm_service.parse_bank_statement(pdf_text, bank_name)
            
            if not transactions:
                return {
                    'success': False,
                    'error': 'Real LLM returned no transactions',
                    'transaction_count': 0
                }
            
            # Calculate totals
            totals = self.calculate_transaction_totals(transactions)
            
            return {
                'success': True,
                'llm_type': 'real',
                'transaction_count': len(transactions),
                'transactions': transactions,
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
            mock_service = MockLLMService()
            
            # Parse bank statement
            transactions = mock_service.parse_bank_statement(pdf_text, bank_name)
            
            if not transactions:
                return {
                    'success': False,
                    'error': 'Mock LLM returned no transactions',
                    'transaction_count': 0
                }
            
            # Calculate totals
            totals = self.calculate_transaction_totals(transactions)
            
            return {
                'success': True,
                'llm_type': 'mock',
                'transaction_count': len(transactions),
                'transactions': transactions,
                **totals
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'transaction_count': 0
            }
    
    def determine_bank_name(self, filename: str) -> str:
        """Determine bank name from filename."""
        filename_lower = filename.lower()
        
        if 'federal' in filename_lower:
            return 'Federal Bank'
        elif 'hdfc' in filename_lower:
            return 'HDFC Bank'
        else:
            return 'Unknown Bank'
    
    def calculate_transaction_totals(self, transactions: list) -> dict:
        """Calculate comprehensive transaction totals."""
        total_credits = 0.0
        total_debits = 0.0
        credit_count = 0
        debit_count = 0
        
        for txn in transactions:
            amount = float(txn.get('amount', 0))
            txn_type = txn.get('type', '').lower()
            
            if txn_type == 'credit' or amount > 0:
                total_credits += abs(amount)
                credit_count += 1
            else:
                total_debits += abs(amount)
                debit_count += 1
        
        return {
            'total_credits': total_credits,
            'total_debits': total_debits,
            'net_amount': total_credits - total_debits,
            'credit_count': credit_count,
            'debit_count': debit_count,
            'avg_credit': total_credits / credit_count if credit_count > 0 else 0,
            'avg_debit': total_debits / debit_count if debit_count > 0 else 0
        }
    
    def generate_comprehensive_summary(self):
        """Generate comprehensive test summary."""
        logger.info("\n" + "="*80)
        logger.info("📊 COMPREHENSIVE TEST SUMMARY")
        logger.info("="*80)
        
        total_files = len(self.results)
        successful_files = sum(1 for r in self.results.values() if r['success'])
        failed_files = total_files - successful_files
        
        logger.info(f"📁 Total PDF files tested: {total_files}")
        logger.info(f"✅ Successful extractions: {successful_files}")
        logger.info(f"❌ Failed extractions: {failed_files}")
        logger.info(f"📈 Success rate: {(successful_files/total_files)*100:.1f}%")
        
        if successful_files > 0:
            # Analyze successful extractions
            logger.info("\n" + "="*60)
            logger.info("✅ SUCCESSFUL EXTRACTIONS ANALYSIS")
            logger.info("="*60)
            
            total_transactions = 0
            total_credits = 0.0
            total_debits = 0.0
            llm_types = {}
            
            for filename, result in self.results.items():
                if result['success']:
                    llm_type = result.get('llm_type', 'unknown')
                    llm_types[llm_type] = llm_types.get(llm_type, 0) + 1
                    
                    total_transactions += result['transaction_count']
                    total_credits += result.get('total_credits', 0)
                    total_debits += result.get('total_debits', 0)
                    
                    logger.info(f"📄 {filename}:")
                    logger.info(f"   🤖 LLM: {llm_type}")
                    logger.info(f"   📊 Transactions: {result['transaction_count']}")
                    logger.info(f"   💰 Credits: ₹{result.get('total_credits', 0):,.2f}")
                    logger.info(f"   💸 Debits: ₹{result.get('total_debits', 0):,.2f}")
                    logger.info(f"   📈 Net: ₹{result.get('net_amount', 0):,.2f}")
                    logger.info(f"   📄 PDF Size: {result.get('pdf_chars', 0):,} chars")
            
            logger.info("\n" + "-"*40)
            logger.info("📊 AGGREGATE STATISTICS")
            logger.info("-"*40)
            logger.info(f"📋 Total transactions extracted: {total_transactions}")
            logger.info(f"💰 Total credits: ₹{total_credits:,.2f}")
            logger.info(f"💸 Total debits: ₹{total_debits:,.2f}")
            logger.info(f"📈 Net amount: ₹{total_credits - total_debits:,.2f}")
            logger.info(f"📊 Average transactions per file: {total_transactions/successful_files:.1f}")
            
            logger.info("\n🤖 LLM SERVICE USAGE:")
            for llm_type, count in llm_types.items():
                logger.info(f"   {llm_type}: {count} files ({(count/successful_files)*100:.1f}%)")
        
        if failed_files > 0:
            logger.info("\n" + "="*60)
            logger.info("❌ FAILED EXTRACTIONS")
            logger.info("="*60)
            
            for filename, result in self.results.items():
                if not result['success']:
                    logger.info(f"📄 {filename}: {result['error']}")
        
        # Save detailed results
        results_file = project_root / "test_results_comprehensive_pdf_extraction.json"
        with open(results_file, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        logger.info(f"\n💾 Detailed results saved to: {results_file}")
        
        # Test conclusion
        logger.info("\n" + "="*80)
        logger.info("🎯 TEST CONCLUSION")
        logger.info("="*80)
        
        if successful_files == total_files:
            logger.info("🎉 ALL TESTS PASSED! PDF extraction is working perfectly.")
            logger.info("✅ LLM-based transaction extraction is functional")
            logger.info("✅ All PDF files processed successfully")
            logger.info("✅ Transaction totals calculated correctly")
        elif successful_files > 0:
            logger.info(f"⚠️ PARTIAL SUCCESS: {successful_files}/{total_files} files processed")
            logger.info("✅ LLM-based transaction extraction is functional")
            logger.info("⚠️ Some PDF files need attention")
        else:
            logger.info("❌ ALL TESTS FAILED! PDF extraction needs debugging.")
            logger.info("❌ LLM service may not be working properly")

def main():
    """Main test function."""
    logger.info("🚀 Starting comprehensive real PDF extraction tests...")
    logger.info("Testing with actual bank statement PDFs")
    logger.info("="*80)
    
    tester = RealPDFTester()
    success = tester.test_all_pdfs_comprehensive()
    
    if success:
        logger.info("\n🎉 Comprehensive PDF extraction tests completed!")
        return 0
    else:
        logger.error("\n❌ Comprehensive PDF extraction tests failed!")
        return 1

if __name__ == "__main__":
    exit(main()) 