# Personal Finance Dashboard - Technical Design Document

## Table of Contents

1. [System Architecture](architecture/README.md)
   - [Overview](architecture/overview.md)
   - [Component Design](architecture/components.md)
   - [Data Flow](architecture/data_flow.md)
   - [Storage Design](architecture/storage.md)

2. [Parser Design](parsers/README.md)
   - [Parser Architecture](parsers/architecture.md)
   - [Federal Bank Parser](parsers/federal_bank.md)
   - [HDFC Savings Parser](parsers/hdfc_savings.md)
   - [HDFC Credit Card Parser](parsers/hdfc_credit_card.md)
   - [Common Utilities](parsers/common_utils.md)

3. [API Design](api/README.md)
   - [REST API Endpoints](api/endpoints.md)
   - [Data Models](api/models.md)
   - [Error Handling](api/errors.md)

4. [Testing Strategy](testing/README.md)
   - [Unit Tests](testing/unit_tests.md)
   - [Integration Tests](testing/integration_tests.md)
   - [Test Data Management](testing/test_data.md)

5. [Development Guide](development/README.md)
   - [Setup Instructions](development/setup.md)
   - [Contributing Guidelines](development/contributing.md)
   - [Code Style Guide](development/style_guide.md)

## Document History

| Version | Date | Author | Description |
|---------|------|--------|-------------|
| 1.0 | 2024-05-25 | Initial | Initial technical design document |

## Introduction

This document provides a comprehensive technical design for the Personal Finance Dashboard application. The system is designed to process bank statements from multiple banks, extract transaction data, and provide analysis and visualization of personal financial data.

### Key Features

- Multi-bank statement parsing
- Transaction categorization
- Financial analysis and reporting
- RESTful API for data access
- Web-based dashboard interface

### Technology Stack

- **Backend**: Python, Flask
- **PDF Processing**: PyMuPDF, pdfplumber
- **Data Storage**: JSON-based file storage
- **Testing**: pytest
- **CI/CD**: GitHub Actions

### System Requirements

- Python 3.10+
- PDF processing libraries
- Web server capabilities
- File system access for data storage

## Quick Links

- [Architecture Diagrams](diagrams/)
- [API Documentation](api/endpoints.md)
- [Parser Documentation](parsers/README.md)
- [Development Setup](development/setup.md) 