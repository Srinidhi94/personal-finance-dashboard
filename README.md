# Personal Finance Dashboard

A web application for analyzing bank statements and tracking personal finances.

## Features

- Parse bank statements from multiple banks:
  - Federal Bank
  - HDFC Bank
- Extract transactions with metadata
- Categorize transactions
- Generate financial reports

## Development Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/personal-finance-dashboard.git
cd personal-finance-dashboard
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Install system dependencies:
- On Ubuntu/Debian:
  ```bash
  sudo apt-get update
  sudo apt-get install -y libmupdf-dev
  ```
- On macOS:
  ```bash
  brew install mupdf
  ```
- On Windows:
  - Download and install MuPDF from https://mupdf.com/releases/

## Running Tests

The project uses pytest for testing. To run tests:

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test files
python -m pytest tests/test_integration.py -v
python -m pytest tests/test_federal_bank_parser.py -v
python -m pytest tests/test_hdfc_parser.py -v
python -m pytest tests/test_app.py -v
```

### Test Structure

- `test_integration.py`: Integration tests using actual PDF files
- `test_federal_bank_parser.py`: Unit tests for Federal Bank parser
- `test_hdfc_parser.py`: Unit tests for HDFC parser
- `test_app.py`: Tests for the web application

Test results are saved in the `tests/test_results` directory and are automatically cleaned up after test execution.

## Contributing

1. Fork the repository
2. Create a feature branch:
```bash
git checkout -b feature/your-feature-name
```

3. Make your changes and commit:
```bash
git add .
git commit -m "Description of your changes"
```

4. Push to your fork:
```bash
git push origin feature/your-feature-name
```

5. Create a Pull Request

All PRs are automatically tested using GitHub Actions. The workflow:
- Runs on Ubuntu with Python 3.10
- Installs all dependencies
- Runs all tests
- Uploads test results as artifacts

## License

[Add your license here]
