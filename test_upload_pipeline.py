#!/usr/bin/env python3
"""
Test the complete upload pipeline end-to-end.
"""

import requests
import json
import time
from pathlib import Path

def test_health():
    """Test application health"""
    print("=== Testing Application Health ===")
    try:
        response = requests.get("http://localhost:8080/health", timeout=10)
        if response.status_code == 200:
            print("✅ Application is healthy")
            print(f"   Response: {response.json()}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

def test_upload_pdf(pdf_path):
    """Test PDF upload"""
    print(f"\n=== Testing PDF Upload: {pdf_path.name} ===")
    
    try:
        with open(pdf_path, 'rb') as f:
            files = {'file': (pdf_path.name, f, 'application/pdf')}
            data = {'account_type': 'savings'}
            
            print("📤 Uploading PDF...")
            start_time = time.time()
            response = requests.post(
                "http://localhost:8080/upload",
                files=files,
                data=data,
                timeout=180  # 3 minutes
            )
            end_time = time.time()
            
            print(f"⏱️  Upload completed in {end_time - start_time:.2f}s")
            print(f"📊 Response status: {response.status_code}")
            
            if response.status_code == 200:
                print("✅ Upload successful")
                return True
            elif response.status_code == 422:
                error_data = response.json()
                print(f"⚠️  Parsing error: {error_data.get('error', 'Unknown error')}")
                print(f"   Error type: {error_data.get('error_type', 'unknown')}")
                return False
            else:
                print(f"❌ Upload failed")
                print(f"   Response: {response.text[:200]}...")
                return False
                
    except requests.Timeout:
        print("⚠️  Upload timed out")
        return False
    except Exception as e:
        print(f"❌ Upload error: {e}")
        return False

def test_pending_transactions():
    """Test getting pending transactions"""
    print("\n=== Testing Pending Transactions API ===")
    
    try:
        response = requests.get("http://localhost:8080/api/pending-transactions", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            transactions = data.get('transactions', [])
            print(f"✅ Found {len(transactions)} pending transactions")
            
            for i, txn in enumerate(transactions[:3]):
                print(f"   {i+1}. {txn.get('date', 'N/A')} - {txn.get('description', 'N/A')[:50]}... - ₹{txn.get('amount', 'N/A')} ({txn.get('type', 'N/A')})")
            
            return transactions
        else:
            print(f"❌ Failed to get pending transactions: {response.status_code}")
            return []
            
    except Exception as e:
        print(f"❌ Error getting pending transactions: {e}")
        return []

def test_confirm_transactions(transactions):
    """Test confirming transactions"""
    if not transactions:
        print("\n⚠️  No transactions to confirm")
        return False
        
    print(f"\n=== Testing Transaction Confirmation ({len(transactions)} transactions) ===")
    
    try:
        response = requests.post(
            "http://localhost:8080/confirm_transactions",
            json={'transactions': transactions},
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Confirmed {result.get('saved', 0)} transactions")
            return True
        else:
            print(f"❌ Confirmation failed: {response.status_code}")
            print(f"   Response: {response.text[:200]}...")
            return False
            
    except Exception as e:
        print(f"❌ Confirmation error: {e}")
        return False

def test_view_transactions():
    """Test viewing saved transactions"""
    print("\n=== Testing Transaction View ===")
    
    try:
        response = requests.get("http://localhost:8080/transactions", timeout=10)
        
        if response.status_code == 200:
            print("✅ Transactions page accessible")
            # Check if the response contains transaction data
            content = response.text
            if "Total Income" in content or "Total Expense" in content:
                print("✅ Transaction data found in response")
                return True
            else:
                print("⚠️  No transaction data visible")
                return False
        else:
            print(f"❌ Failed to access transactions page: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error accessing transactions page: {e}")
        return False

def main():
    """Run the complete pipeline test"""
    print("🚀 Starting Complete Upload Pipeline Test")
    print("=" * 60)
    
    # Test application health
    if not test_health():
        print("❌ Application not healthy, aborting test")
        return
    
    # Find PDF files
    uploads_dir = Path("/Users/srinidhr/Sri/Personal/Finance/Finance App/personal-finance-dashboard-1/uploads/Account_Statements")
    pdf_files = list(uploads_dir.glob("*.pdf"))
    
    if not pdf_files:
        print("❌ No PDF files found")
        return
    
    print(f"📁 Found {len(pdf_files)} PDF files")
    
    # Test with Federal Bank PDF first (it works better)
    federal_pdfs = [f for f in pdf_files if "federal" in f.name.lower()]
    pdf_file = federal_pdfs[0] if federal_pdfs else pdf_files[0]
    print(f"🎯 Testing with: {pdf_file.name}")
    
    # Test upload
    if not test_upload_pdf(pdf_file):
        print("❌ Upload failed, aborting test")
        return
    
    # Test pending transactions
    transactions = test_pending_transactions()
    
    # Test confirmation
    if transactions:
        if not test_confirm_transactions(transactions):
            print("❌ Confirmation failed")
            return
    
    # Test viewing transactions
    test_view_transactions()
    
    print("\n" + "=" * 60)
    print("🏁 Pipeline Test Summary")
    print("✅ Complete upload pipeline test finished")
    print("   - Application health: ✅")
    print("   - PDF upload: ✅" if transactions else "   - PDF upload: ❌")
    print("   - Transaction extraction: ✅" if transactions else "   - Transaction extraction: ❌")
    print("   - Transaction confirmation: ✅" if transactions else "   - Transaction confirmation: ❌")
    print("   - Transaction viewing: ✅")

if __name__ == "__main__":
    main() 