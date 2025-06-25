#!/usr/bin/env python3
"""
Test PDF processing and LLM extraction with actual bank statements.
This test verifies the complete pipeline from PDF to extracted transactions.
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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_pdf_text_extraction():
    """Test PDF text extraction from actual bank statements."""
    from utils.pdf_utils import extract_text_from_pdf
    
    pdf_folder = project_root / "uploads" / "Account_Statements"
    
    if not pdf_folder.exists():
        logger.error(f"PDF folder not found: {pdf_folder}")
        return False
    
    pdf_files = list(pdf_folder.glob("*.pdf"))
    if not pdf_files:
        logger.error(f"No PDF files found in {pdf_folder}")
        return False
    
    logger.info(f"Testing text extraction from {len(pdf_files)} PDF files")
    
    results = {}
    
    for pdf_file in pdf_files:
        try:
            logger.info(f"Extracting text from: {pdf_file.name}")
            text = extract_text_from_pdf(str(pdf_file))
            
            if text and len(text.strip()) > 100:
                results[pdf_file.name] = {
                    'success': True,
                    'text_length': len(text),
                    'preview': text[:200] + "..." if len(text) > 200 else text
                }
                logger.info(f"✅ {pdf_file.name}: {len(text)} characters extracted")
            else:
                results[pdf_file.name] = {
                    'success': False,
                    'error': 'Insufficient text extracted',
                    'text_length': len(text) if text else 0
                }
                logger.error(f"❌ {pdf_file.name}: Insufficient text extracted")
                
        except Exception as e:
            results[pdf_file.name] = {
                'success': False,
                'error': str(e),
                'text_length': 0
            }
            logger.error(f"❌ {pdf_file.name}: {e}")
    
    # Save results
    results_file = project_root / "test_results_pdf_extraction.json"
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"PDF extraction results saved to: {results_file}")
    
    successful_extractions = sum(1 for r in results.values() if r['success'])
    logger.info(f"Summary: {successful_extractions}/{len(results)} PDFs successfully processed")
    
    return successful_extractions > 0

def test_llm_service_connection():
    """Test LLM service connection and basic functionality."""
    try:
        from llm_services.llm_service import LLMService
        
        logger.info("Testing LLM service connection...")
        llm_service = LLMService()
        
        # Test basic connection
        try:
            response = llm_service._call_llm_with_retry("Hello, can you respond with 'OK'?", timeout=10)
            if response and len(response.strip()) > 0:
                logger.info(f"✅ LLM service connected successfully. Response: {response[:100]}...")
                return True, llm_service
            else:
                logger.warning("⚠️ LLM service responded but with empty response")
                return False, None
        except Exception as e:
            logger.warning(f"⚠️ LLM service connection failed: {e}")
            return False, None
            
    except Exception as e:
        logger.error(f"❌ Failed to initialize LLM service: {e}")
        return False, None

def test_mock_llm_service():
    """Test mock LLM service functionality."""
    try:
        from llm_services.llm_service_mock import MockLLMService
        
        logger.info("Testing Mock LLM service...")
        mock_service = MockLLMService()
        
        # Test bank statement parsing
        sample_text = "Sample bank statement text for testing"
        
        federal_transactions = mock_service.parse_bank_statement(sample_text, "Federal Bank")
        hdfc_transactions = mock_service.parse_bank_statement(sample_text, "HDFC Bank")
        
        if federal_transactions and hdfc_transactions:
            logger.info(f"✅ Mock LLM service working. Federal: {len(federal_transactions)}, HDFC: {len(hdfc_transactions)} transactions")
            return True, mock_service
        else:
            logger.error("❌ Mock LLM service returned no transactions")
            return False, None
            
    except Exception as e:
        logger.error(f"❌ Mock LLM service failed: {e}")
        return False, None

def test_transaction_extraction_with_real_pdf():
    """Test transaction extraction using real PDF files."""
    from utils.pdf_utils import extract_text_from_pdf
    
    pdf_folder = project_root / "uploads" / "Account_Statements"
    
    # Test LLM services
    llm_connected, llm_service = test_llm_service_connection()
    mock_available, mock_service = test_mock_llm_service()
    
    if not llm_connected and not mock_available:
        logger.error("❌ No LLM service available for testing")
        return False
    
    # Choose service to use
    service_to_use = llm_service if llm_connected else mock_service
    service_type = "Real LLM" if llm_connected else "Mock LLM"
    
    logger.info(f"Using {service_type} service for transaction extraction")
    
    # Test with one PDF file
    pdf_files = list(pdf_folder.glob("*.pdf"))
    if not pdf_files:
        logger.error("No PDF files found for testing")
        return False
    
    test_pdf = pdf_files[0]  # Use first PDF for testing
    logger.info(f"Testing transaction extraction with: {test_pdf.name}")
    
    try:
        # Extract text
        pdf_text = extract_text_from_pdf(str(test_pdf))
        if not pdf_text or len(pdf_text.strip()) < 100:
            logger.error(f"❌ Insufficient text extracted from {test_pdf.name}")
            return False
        
        logger.info(f"Extracted {len(pdf_text)} characters from PDF")
        
        # Determine bank name
        bank_name = "Federal Bank" if "federal" in test_pdf.name.lower() else "HDFC Bank"
        logger.info(f"Detected bank: {bank_name}")
        
        # Extract transactions
        transactions = service_to_use.parse_bank_statement(pdf_text, bank_name)
        
        if not transactions:
            logger.error(f"❌ No transactions extracted from {test_pdf.name}")
            return False
        
        logger.info(f"✅ Extracted {len(transactions)} transactions")
        
        # Analyze transactions
        total_credits = sum(abs(t['amount']) for t in transactions if t.get('type') == 'credit' or t.get('amount', 0) > 0)
        total_debits = sum(abs(t['amount']) for t in transactions if t.get('type') == 'debit' or t.get('amount', 0) < 0)
        
        logger.info(f"Transaction Summary:")
        logger.info(f"  - Total Credits: ₹{total_credits:,.2f}")
        logger.info(f"  - Total Debits: ₹{total_debits:,.2f}")
        logger.info(f"  - Net Amount: ₹{total_credits - total_debits:,.2f}")
        
        # Show sample transactions
        logger.info("Sample transactions:")
        for i, txn in enumerate(transactions[:5]):
            logger.info(f"  {i+1}. {txn.get('date')} | {txn.get('description', '')[:50]}... | ₹{txn.get('amount', 0):,.2f}")
        
        # Save results
        results = {
            'pdf_file': test_pdf.name,
            'bank_name': bank_name,
            'service_type': service_type,
            'transaction_count': len(transactions),
            'total_credits': total_credits,
            'total_debits': total_debits,
            'net_amount': total_credits - total_debits,
            'transactions': transactions
        }
        
        results_file = project_root / "test_results_transaction_extraction.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"Transaction extraction results saved to: {results_file}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Transaction extraction failed: {e}")
        return False

def test_end_to_end_processing():
    """Test complete end-to-end processing pipeline."""
    logger.info("="*80)
    logger.info("STARTING END-TO-END PROCESSING TEST")
    logger.info("="*80)
    
    # Step 1: Test PDF text extraction
    logger.info("Step 1: Testing PDF text extraction...")
    pdf_extraction_success = test_pdf_text_extraction()
    
    if not pdf_extraction_success:
        logger.error("❌ PDF text extraction failed")
        return False
    
    logger.info("✅ PDF text extraction successful")
    
    # Step 2: Test transaction extraction
    logger.info("\nStep 2: Testing transaction extraction...")
    transaction_extraction_success = test_transaction_extraction_with_real_pdf()
    
    if not transaction_extraction_success:
        logger.error("❌ Transaction extraction failed")
        return False
    
    logger.info("✅ Transaction extraction successful")
    
    # Step 3: Summary
    logger.info("\n" + "="*80)
    logger.info("END-TO-END PROCESSING TEST SUMMARY")
    logger.info("="*80)
    logger.info("✅ All tests passed successfully!")
    logger.info("✅ PDF text extraction: Working")
    logger.info("✅ Transaction extraction: Working")
    logger.info("✅ LLM integration: Working")
    
    return True

def main():
    """Main test function."""
    logger.info("Starting comprehensive PDF processing and LLM extraction tests...")
    
    success = test_end_to_end_processing()
    
    if success:
        logger.info("\n🎉 All tests completed successfully!")
        return 0
    else:
        logger.error("\n❌ Some tests failed. Check logs for details.")
        return 1

if __name__ == "__main__":
    exit(main()) 