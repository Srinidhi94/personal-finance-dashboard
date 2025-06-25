"""
Custom exceptions for the parsers module
"""

class PDFParsingError(Exception):
    """Custom exception for PDF parsing errors"""
    def __init__(self, message: str, error_type: str = "parsing_error"):
        self.message = message
        self.error_type = error_type
        super().__init__(self.message) 