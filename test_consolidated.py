#!/usr/bin/env python3
"""
Consolidated test script for Personal Finance Dashboard.
Tests all key functionality and provides debugging information.
"""

import requests
import json
import time
from pathlib import Path

def test_health():
    """Test application health"""
    print("=== Application Health Check ===")
    try:
        response = requests.get("http://localhost:8080/health", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Application is healthy")
            print(f"   Status: {data.get('status')}")
            print(f"   Timestamp: {data.get('timestamp')}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

def test_simple_upload():
    """Test uploading a small, simple PDF"""
    print("\n=== Simple PDF Upload Test ===")
    
    # Find the smallest PDF (Federal Bank March - 2082 characters)
    uploads_dir = Path("/Users/srinidhr/Sri/Personal/Finance/Finance App/personal-finance-dashboard-1/uploads/Account_Statements")
    pdf_files = list(uploads_dir.glob("*Federal_Bank_March*.pdf"))
    
    if not pdf_files:
        print("❌ No Federal Bank March PDF found")
        return False, []
    
    pdf_file = pdf_files[0]
    print(f"📄 Testing with: {pdf_file.name}")
    
    try:
        with open(pdf_file, 'rb') as f:
            files = {'file': (pdf_file.name, f, 'application/pdf')}
            data = {'account_type': 'savings'}
            
            print("📤 Uploading...")
            start_time = time.time()
            response = requests.post(
                "http://localhost:8080/upload",
                files=files,
                data=data,
                timeout=120  # 2 minutes for small file
            )
            end_time = time.time()
            
            print(f"⏱️  Upload completed in {end_time - start_time:.2f}s")
            print(f"📊 Response status: {response.status_code}")
            
            if response.status_code == 200:
                print("✅ Upload successful")
                return True, []
            elif response.status_code == 422:
                error_data = response.json()
                print(f"⚠️  Parsing error: {error_data.get('error', 'Unknown error')}")
                print(f"   Error type: {error_data.get('error_type', 'unknown')}")
                return False, []
            else:
                print(f"❌ Upload failed")
                print(f"   Response: {response.text[:200]}...")
                return False, []
                
    except requests.Timeout:
        print("⚠️  Upload timed out")
        return False, []
    except Exception as e:
        print(f"❌ Upload error: {e}")
        return False, []

def test_pending_transactions():
    """Get pending transactions from session"""
    print("\n=== Pending Transactions Test ===")
    
    try:
        response = requests.get("http://localhost:8080/api/pending-transactions", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            transactions = data.get('transactions', [])
            print(f"✅ Found {len(transactions)} pending transactions")
            
            for i, txn in enumerate(transactions[:5]):  # Show first 5
                print(f"   {i+1}. {txn.get('date', 'N/A')} - {txn.get('description', 'N/A')[:50]}... - ₹{txn.get('amount', 'N/A')} ({txn.get('type', 'N/A')})")
            
            return transactions
        else:
            print(f"❌ Failed to get pending transactions: {response.status_code}")
            return []
            
    except Exception as e:
        print(f"❌ Error getting pending transactions: {e}")
        return []

def test_transaction_confirmation(transactions):
    """Test confirming transactions"""
    if not transactions:
        print("\n⚠️  No transactions to confirm")
        return False
        
    print(f"\n=== Transaction Confirmation Test ===")
    print(f"🔄 Confirming {len(transactions)} transactions...")
    
    try:
        response = requests.post(
            "http://localhost:8080/confirm_transactions",
            json={'transactions': transactions},
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            saved_count = result.get('saved', 0)
            print(f"✅ Successfully confirmed {saved_count} transactions")
            return True
        else:
            print(f"❌ Confirmation failed: {response.status_code}")
            print(f"   Response: {response.text[:200]}...")
            return False
            
    except Exception as e:
        print(f"❌ Confirmation error: {e}")
        return False

def test_dashboard_view():
    """Test viewing the dashboard"""
    print("\n=== Dashboard View Test ===")
    
    try:
        response = requests.get("http://localhost:8080/", timeout=10)
        
        if response.status_code == 200:
            content = response.text
            print("✅ Dashboard accessible")
            
            # Check for key elements
            if "Personal Finance Dashboard" in content:
                print("✅ Dashboard title found")
            if "Upload" in content or "upload" in content:
                print("✅ Upload functionality visible")
            if "Total" in content:
                print("✅ Summary information visible")
                
            return True
        else:
            print(f"❌ Dashboard not accessible: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Dashboard error: {e}")
        return False

def test_transactions_page():
    """Test the transactions page"""
    print("\n=== Transactions Page Test ===")
    
    try:
        response = requests.get("http://localhost:8080/transactions", timeout=10)
        
        if response.status_code == 200:
            content = response.text
            print("✅ Transactions page accessible")
            
            # Check for transaction data
            if "Total Income" in content or "Total Expense" in content:
                print("✅ Transaction summary visible")
            if "₹" in content:
                print("✅ Currency amounts visible")
                
            return True
        else:
            print(f"❌ Transactions page not accessible: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Transactions page error: {e}")
        return False

def main():
    """Run all tests and provide summary"""
    print("🚀 Personal Finance Dashboard - Consolidated Test Suite")
    print("=" * 70)
    
    results = {}
    
    # Test 1: Health Check
    results['health'] = test_health()
    
    # Test 2: Simple Upload
    upload_success, transactions = test_simple_upload()
    results['upload'] = upload_success
    
    # Test 3: Get Pending Transactions
    if upload_success:
        transactions = test_pending_transactions()
        results['pending'] = len(transactions) > 0
    else:
        results['pending'] = False
    
    # Test 4: Confirm Transactions
    if transactions:
        results['confirmation'] = test_transaction_confirmation(transactions)
    else:
        results['confirmation'] = False
    
    # Test 5: Dashboard View
    results['dashboard'] = test_dashboard_view()
    
    # Test 6: Transactions Page
    results['transactions_page'] = test_transactions_page()
    
    # Summary
    print("\n" + "=" * 70)
    print("🏁 Test Results Summary")
    print("=" * 70)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        test_display = test_name.replace('_', ' ').title()
        print(f"{status} {test_display}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 All tests passed! The application is working correctly.")
        print("\n📝 Application is ready for use:")
        print("   - Visit: http://localhost:8080")
        print("   - Upload bank statements via the web interface")
        print("   - Review and confirm transactions")
        print("   - View transaction summaries")
    else:
        print("⚠️  Some tests failed. Issues identified:")
        failed_tests = [name for name, result in results.items() if not result]
        for test in failed_tests:
            print(f"   - {test.replace('_', ' ').title()}")
        
        print("\n🔧 Recommended actions:")
        if not results['health']:
            print("   - Check if application is running: docker-compose up")
        if not results['upload']:
            print("   - Check LLM service connectivity")
            print("   - Review application logs: docker-compose logs app")
        if not results['pending']:
            print("   - Check session management and API endpoints")
        if not results['confirmation']:
            print("   - Check database connectivity and transaction processing")

if __name__ == "__main__":
    main() 