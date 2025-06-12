import os
import pytest
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
def mock_pdf_text():
    """Mock PDF text content"""
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

@pytest.fixture
def mock_pdf_doc(mock_pdf_text):
    """Mock PDF document"""
    mock_doc = MagicMock()
    mock_page = MagicMock()
    mock_page.get_text.return_value = mock_pdf_text
    mock_doc.__getitem__.return_value = mock_page
    mock_doc.__len__.return_value = 1
    return mock_doc 