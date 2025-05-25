import os
import pytest
import fitz  # PyMuPDF
from unittest.mock import MagicMock

@pytest.fixture(scope="session")
def test_data_dir():
    """Return the path to the test data directory"""
    data_dir = os.path.join(os.path.dirname(__file__), "data")
    os.makedirs(data_dir, exist_ok=True)
    return data_dir

@pytest.fixture(scope="session")
def uploads_dir():
    """Create and return the uploads directory"""
    uploads_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
    os.makedirs(uploads_dir, exist_ok=True)
    return uploads_dir

@pytest.fixture(scope="session")
def mock_federal_bank_text_content():
    """Mock Federal Bank statement text content"""
    return """
    Statement Period: 01 May 2024 to 31 May 2024
    SAVINGS A/C NO: 12345678901
    IFSC: FDRL0123456
    Transaction Details
    Opening Balance
    on 01 May 2024
    ₹10,000.00
    
    01 May
    UPI/CR/123456789/CREDIT
    5,000.00
    15,000.00
    
    02 May
    POS/DEBIT CARD/AMAZON
    1,500.00
    13,500.00
    
    03 May
    NEFT/CR/SALARY/COMPANY
    50,000.00
    63,500.00
    
    Closing Balance
    on 31 May 2024
    ₹63,500.00
    """

@pytest.fixture(scope="session")
def mock_hdfc_text_content():
    """Mock HDFC Bank statement text content"""
    return """
    HDFC BANK
    Statement of account
    
    Account No: 50100123456789
    Branch: HENNUR ROAD
    
    MR. SRINIDH R
    #92 3RD MAIN, 2ND
    CROSS NEAR BRIGADE MILLENNIUM, BOB
    COLONY PUTTENAHALLI JP NAGAR 7PHAS
    BANGALORE 560078
    KARNATAKA INDIA
    
    Opening Balance: 10,000.00
    
    10/05/25
    000008308912572
    ACH D-ZERODHA BROKING
    4,500.00
    14,500.00
    
    10/05/25
    000008306663718
    ACH D-INDIAN CLEARING CORP 0000007TPVJ
    10,000.00
    24,500.00
    
    10/05/25
    000008308304566
    ACH D-ZERODHA BROKING
    4,693.00
    29,193.00
    
    11/05/25
    000008308258310
    ACH D-ZERODHA BROKING
    6,500.00
    35,693.00
    
    11/05/25
    000008308250875
    ACH D-ZERODHA BROKING LTD 5RL2KPW2L6
    6,000.00
    41,693.00
    
    11/05/25
    000008305921065
    ACH D-INDIAN CLEARING CORP 0000001D5YNE
    28,400.00
    70,093.00
    
    12/05/25
    000008305915068
    ACH D-INDIAN CLEARING CORP 0000001P5VFX
    6,100.00
    76,193.00
    
    12/05/25
    000008308258310
    ACH D-ZERODHA BROKING
    6,500.00
    82,693.00
    
    Closing Balance: 82,693.00
    """

@pytest.fixture(scope="session", autouse=True)
def setup_test_files(uploads_dir, mock_federal_bank_text_content, mock_hdfc_text_content):
    """Create sample test files in the uploads directory"""
    # Create Federal Bank sample
    federal_path = os.path.join(uploads_dir, "Federal_Bank_Statement.pdf")
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), mock_federal_bank_text_content)
    doc.save(federal_path)
    doc.close()
    
    # Create HDFC sample
    hdfc_path = os.path.join(uploads_dir, "Statement_Example.pdf")
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), mock_hdfc_text_content)
    doc.save(hdfc_path)
    doc.close()
    
    yield
    
    # Cleanup
    if os.path.exists(federal_path):
        os.remove(federal_path)
    if os.path.exists(hdfc_path):
        os.remove(hdfc_path)

@pytest.fixture
def mock_federal_bank_text(mock_federal_bank_text_content):
    """Return the mock Federal Bank text content for function-scoped tests"""
    return mock_federal_bank_text_content

@pytest.fixture
def mock_hdfc_text(mock_hdfc_text_content):
    """Return the mock HDFC text content for function-scoped tests"""
    return mock_hdfc_text_content

@pytest.fixture
def mock_pdf_text(mock_federal_bank_text):
    """Return the mock PDF text content for function-scoped tests"""
    return mock_federal_bank_text

@pytest.fixture
def mock_pdf_doc(mock_pdf_text):
    """Mock PDF document"""
    mock_doc = MagicMock()
    mock_page = MagicMock()
    mock_page.get_text.return_value = mock_pdf_text
    mock_doc.__getitem__.return_value = mock_page
    mock_doc.__len__.return_value = 1
    return mock_doc 