#!/usr/bin/env python3
"""
Comprehensive LLM debugging test to identify and fix timeout issues
"""
import os
import sys
import json
import time
import requests
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, '/app')

from llm_services.llm_service import LLMService
from utils.pdf_utils import extract_text_from_pdf
from parsers.exceptions import PDFParsingError

def test_ollama_connectivity():
    """Test basic Ollama connectivity"""
    print("=== Testing Ollama Connectivity ===")
    
    endpoint = "http://192.168.0.118:11434"
    
    # Test basic connection
    try:
        response = requests.get(f"{endpoint}/api/version", timeout=10)
        print(f"✅ Ollama connection successful: {response.status_code}")
        print(f"   Version: {response.json()}")
    except Exception as e:
        print(f"❌ Ollama connection failed: {e}")
        return False
    
    # Test model availability
    try:
        response = requests.get(f"{endpoint}/api/tags", timeout=10)
        models = response.json().get('models', [])
        print(f"✅ Available models: {len(models)}")
        for model in models:
            print(f"   - {model['name']}")
        
        # Check if our target model exists
        target_model = "llama3.2:1b"
        model_exists = any(model['name'] == target_model for model in models)
        if model_exists:
            print(f"✅ Target model '{target_model}' is available")
        else:
            print(f"❌ Target model '{target_model}' not found")
            return False
            
    except Exception as e:
        print(f"❌ Failed to check models: {e}")
        return False
    
    return True

def test_simple_llm_request():
    """Test a simple LLM request to check basic functionality"""
    print("\n=== Testing Simple LLM Request ===")
    
    endpoint = "http://192.168.0.118:11434/api/generate"
    model = "llama3.2:1b"
    
    simple_prompt = "Return just the number 42 as JSON: {\"result\": 42}"
    
    payload = {
        "model": model,
        "prompt": simple_prompt,
        "stream": False,
        "options": {
            "temperature": 0.1,
            "top_p": 0.9,
            "num_predict": 50
        }
    }
    
    try:
        start_time = time.time()
        response = requests.post(endpoint, json=payload, timeout=30)
        end_time = time.time()
        
        print(f"✅ Simple request successful in {end_time - start_time:.2f}s")
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"   Response: {result.get('response', '')[:200]}...")
            return True
        else:
            print(f"❌ Bad status code: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Simple request failed: {e}")
        return False

def test_pdf_extraction():
    """Test PDF text extraction from real files"""
    print("\n=== Testing PDF Text Extraction ===")
    
    uploads_dir = Path("/app/uploads/Account_Statements")
    pdf_files = list(uploads_dir.glob("*.pdf"))
    
    if not pdf_files:
        print("❌ No PDF files found in uploads directory")
        return False
    
    for pdf_file in pdf_files[:2]:  # Test first 2 files
        print(f"\n📄 Testing: {pdf_file.name}")
        try:
            text = extract_text_from_pdf(str(pdf_file))
            print(f"✅ Extracted {len(text)} characters")
            print(f"   First 200 chars: {text[:200]}...")
            
            # Check for common bank statement indicators
            indicators = ["account", "statement", "balance", "transaction", "date"]
            found_indicators = [ind for ind in indicators if ind.lower() in text.lower()]
            print(f"   Bank indicators found: {found_indicators}")
            
        except Exception as e:
            print(f"❌ PDF extraction failed: {e}")
            return False
    
    return True

def test_llm_service_with_timeout_handling():
    """Test LLM service with proper timeout handling"""
    print("\n=== Testing LLM Service with Timeout Handling ===")
    
    # Initialize LLM service
    llm_service = LLMService()
    
    # Test with a small text sample first
    sample_text = """
    Account Statement
    Date: 2025-03-01
    Transaction: Salary Credit - 50000.00
    Date: 2025-03-02  
    Transaction: ATM Withdrawal - 2000.00
    """
    
    print("🔄 Testing with sample text...")
    try:
        start_time = time.time()
        transactions = llm_service.parse_bank_statement(sample_text, "Generic Bank")
        end_time = time.time()
        
        print(f"✅ Sample parsing successful in {end_time - start_time:.2f}s")
        print(f"   Found {len(transactions)} transactions")
        for i, txn in enumerate(transactions[:3]):
            print(f"   {i+1}. {txn.get('date')} - {txn.get('description')[:50]}... - {txn.get('amount')}")
            
    except Exception as e:
        print(f"❌ Sample parsing failed: {e}")
        return False
    
    return True

def test_real_pdf_processing():
    """Test processing real PDF files with enhanced error handling"""
    print("\n=== Testing Real PDF Processing ===")
    
    uploads_dir = Path("/app/uploads/Account_Statements")
    pdf_files = list(uploads_dir.glob("*.pdf"))
    
    if not pdf_files:
        print("❌ No PDF files found")
        return False
    
    llm_service = LLMService()
    
    for pdf_file in pdf_files[:1]:  # Test just one file first
        print(f"\n📄 Processing: {pdf_file.name}")
        
        try:
            # Extract text
            text = extract_text_from_pdf(str(pdf_file))
            print(f"✅ Text extracted: {len(text)} characters")
            
            # Determine bank name from filename
            bank_name = "Generic Bank"
            if "federal" in pdf_file.name.lower():
                bank_name = "Federal Bank"
            elif "hdfc" in pdf_file.name.lower():
                bank_name = "HDFC Bank"
            
            print(f"🏦 Detected bank: {bank_name}")
            
            # Process with LLM
            print("🔄 Processing with LLM...")
            start_time = time.time()
            
            transactions = llm_service.parse_bank_statement(text, bank_name)
            
            end_time = time.time()
            print(f"✅ LLM processing successful in {end_time - start_time:.2f}s")
            print(f"   Found {len(transactions)} transactions")
            
            # Show sample transactions
            for i, txn in enumerate(transactions[:5]):
                print(f"   {i+1}. {txn.get('date')} - {txn.get('description')[:50]}... - ₹{txn.get('amount')}")
            
            return True
            
        except PDFParsingError as e:
            print(f"❌ PDF parsing error: {e}")
            print(f"   Error type: {e.error_type}")
            return False
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            return False
    
    return False

def main():
    """Run all debugging tests"""
    print("🚀 Starting LLM Debug Test Suite")
    print("=" * 50)
    
    tests = [
        ("Ollama Connectivity", test_ollama_connectivity),
        ("Simple LLM Request", test_simple_llm_request),
        ("PDF Text Extraction", test_pdf_extraction),
        ("LLM Service Timeout Handling", test_llm_service_with_timeout_handling),
        ("Real PDF Processing", test_real_pdf_processing)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ Test '{test_name}' crashed: {e}")
            results[test_name] = False
    
    # Summary
    print(f"\n{'='*50}")
    print("🏁 Test Summary:")
    print("=" * 50)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} {test_name}")
    
    total_tests = len(results)
    passed_tests = sum(results.values())
    print(f"\nOverall: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("🎉 All tests passed! LLM processing should work correctly.")
    else:
        print("⚠️  Some tests failed. Check the output above for debugging info.")

if __name__ == "__main__":
    main() 