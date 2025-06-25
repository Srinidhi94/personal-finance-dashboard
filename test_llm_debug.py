#!/usr/bin/env python3
"""
Debug script to test LLM JSON parsing issues.
"""

import sys
import os
sys.path.insert(0, '/app')

from llm_services.llm_service import LLMService
from utils.pdf_utils import extract_text_from_pdf
from pathlib import Path

def test_llm_json_parsing():
    """Test LLM JSON parsing with real PDF"""
    print("=== Testing LLM JSON Parsing ===")
    
    # Initialize LLM service
    llm_service = LLMService()
    
    # Get a sample PDF
    pdf_path = Path("/app/uploads/Account_Statements/Acc_Statement_Federal_Bank_March_decrypted.pdf")
    
    if not pdf_path.exists():
        print(f"❌ PDF not found: {pdf_path}")
        return
    
    print(f"📄 Testing with: {pdf_path.name}")
    
    # Extract text
    try:
        text = extract_text_from_pdf(str(pdf_path))
        print(f"✅ Extracted {len(text)} characters")
        
        # Use a smaller sample for testing
        sample_text = text[:2000]
        print(f"📝 Using first 2000 characters for testing")
        
        # Test LLM parsing
        print("🤖 Calling LLM service...")
        transactions = llm_service.parse_bank_statement(sample_text, "Federal Bank")
        
        print(f"✅ LLM returned {len(transactions)} transactions")
        print(f"   Type: {type(transactions)}")
        
        # Validate structure
        for i, txn in enumerate(transactions[:3]):
            print(f"   Transaction {i+1}: {type(txn)}")
            if isinstance(txn, dict):
                print(f"      Keys: {list(txn.keys())}")
                print(f"      Date: {txn.get('date', 'N/A')}")
                print(f"      Amount: {txn.get('amount', 'N/A')}")
                print(f"      Type: {txn.get('type', 'N/A')}")
                print(f"      Description: {txn.get('description', 'N/A')[:50]}...")
            else:
                print(f"      Value: {txn}")
        
        print("✅ LLM JSON parsing test completed successfully")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

def test_simple_llm_call():
    """Test a simple LLM call to see raw response"""
    print("\n=== Testing Simple LLM Call ===")
    
    llm_service = LLMService()
    
    prompt = '''Extract transactions from this bank statement text and return ONLY a JSON array:

Sample text:
2025-03-01 ATM Withdrawal 2000.50 Dr
2025-03-02 Salary Credit 50000.00 Cr

Return format:
[{"date": "2025-03-01", "description": "ATM Withdrawal", "amount": 2000.50, "type": "debit"}]'''
    
    try:
        print("🤖 Making simple LLM call...")
        response = llm_service._call_llm(prompt, timeout=30)
        
        print(f"✅ Raw LLM response ({len(response)} chars):")
        print("=" * 50)
        print(response[:500] + ("..." if len(response) > 500 else ""))
        print("=" * 50)
        
        # Try to parse JSON
        import json
        try:
            # Try direct parsing
            parsed = json.loads(response)
            print(f"✅ Direct JSON parse successful: {type(parsed)}")
        except json.JSONDecodeError as e:
            print(f"❌ Direct JSON parse failed: {e}")
            
            # Try sanitization
            sanitized = llm_service._sanitize_json_string(response)
            print(f"🧹 Sanitized response ({len(sanitized)} chars):")
            print("=" * 30)
            print(sanitized[:300] + ("..." if len(sanitized) > 300 else ""))
            print("=" * 30)
            
            try:
                parsed = json.loads(sanitized)
                print(f"✅ Sanitized JSON parse successful: {type(parsed)}")
            except json.JSONDecodeError as e2:
                print(f"❌ Sanitized JSON parse also failed: {e2}")
        
    except Exception as e:
        print(f"❌ LLM call failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_simple_llm_call()
    test_llm_json_parsing() 