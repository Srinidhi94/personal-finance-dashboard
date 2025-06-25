"""
PDF Utilities for text extraction and processing.
"""

import fitz  # PyMuPDF
import logging
from typing import Optional

logger = logging.getLogger(__name__)

def extract_text_from_pdf(pdf_path: str) -> Optional[str]:
    """
    Extract text from PDF file using PyMuPDF.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        Extracted text content or None if extraction fails
        
    Raises:
        Exception: If PDF extraction fails
    """
    try:
        doc = fitz.open(pdf_path)
        text = ""
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            text += page.get_text()
        
        doc.close()
        
        if not text.strip():
            raise Exception("PDF appears to contain no extractable text")
        
        return text
        
    except Exception as e:
        logger.error(f"Failed to extract text from PDF {pdf_path}: {e}")
        raise Exception(f"PDF text extraction failed: {e}")

def extract_pdf_metadata(pdf_path: str) -> dict:
    """
    Extract metadata from PDF file.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        Dictionary containing PDF metadata
    """
    try:
        doc = fitz.open(pdf_path)
        metadata = doc.metadata
        page_count = len(doc)
        doc.close()
        
        return {
            'page_count': page_count,
            'title': metadata.get('title', ''),
            'author': metadata.get('author', ''),
            'subject': metadata.get('subject', ''),
            'creator': metadata.get('creator', ''),
            'producer': metadata.get('producer', ''),
            'creation_date': metadata.get('creationDate', ''),
            'modification_date': metadata.get('modDate', '')
        }
        
    except Exception as e:
        logger.error(f"Failed to extract metadata from PDF {pdf_path}: {e}")
        return {'page_count': 0, 'error': str(e)}

def validate_pdf_file(pdf_path: str) -> bool:
    """
    Validate if file is a readable PDF.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        True if PDF is valid and readable, False otherwise
    """
    try:
        doc = fitz.open(pdf_path)
        page_count = len(doc)
        doc.close()
        return page_count > 0
    except Exception:
        return False 