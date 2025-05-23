# Personal Finance Dashboard

A comprehensive dashboard for tracking your finances, automatically parsing bank statements, categorizing transactions, and analyzing spending patterns.

## Overview

This application helps you track your personal finances by:

1. Automatically extracting transactions from bank statements (PDF)
2. Intelligently categorizing transactions
3. Visualizing spending patterns
4. Providing insights into your financial habits

Currently supported bank statement formats:
- HDFC Bank Savings Account
- HDFC Credit Card

## Features

- **Automated Statement Parsing**: Upload bank statements in PDF format and automatically extract transaction details
- **Smart Categorization**: Automatically categorize transactions based on description patterns
- **Data Visualization**: View spending breakdowns by category, time period, and more
- **Transaction Management**: Edit, categorize, and annotate transactions
- **Multi-account Support**: Track multiple accounts in a single dashboard

## Setup

### Requirements

- Python 3.8+
- Required Python packages (see `requirements.txt`)

### Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/Srinidhi94/personal-finance-dashboard.git
   cd personal-finance-dashboard
   ```

2. Create a virtual environment and activate it:
   ```bash
   python -m venv venv
   source venv/bin/activate   # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure your accounts in `data/account_config.json` (see example in the file)

## Usage

### Running the Application

Start the web application:

```bash
make run
```

Or directly using Python:

```bash
python app.py
```

The application will be available at http://localhost:5000

### Parsing Bank Statements

1. Upload a statement through the web interface, or
2. Use the command line:
   ```bash
   make parse FILE=path/to/your/statement.pdf
   ```

### Testing

Run all tests:

```bash
make test
```

Test specific components:

```bash
make test-hdfc          # Test HDFC parser
make test-pipeline      # Test full parsing and categorization pipeline
make test-pipeline-clean # Test pipeline and clean up results after
```

## Development

### Project Structure

- `app.py`: Main Flask application
- `parsers/`: Bank statement parsing modules
  - `hdfc_savings.py`: HDFC savings account statement parser
  - `hdfc_credit_card.py`: HDFC credit card statement parser
- `data/`: Configuration and data storage
- `tests/`: Test scripts
- `static/`: CSS, JavaScript, and other static assets
- `templates/`: HTML templates
- `uploads/`: Temporary storage for uploaded statements

### Adding Support for New Banks

1. Create a new parser module in the `parsers/` directory
2. Implement the extraction function following existing patterns
3. Update `data/account_config.json` to include the new bank parser
4. Add tests in the `tests/` directory

## License

MIT

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Contact

For questions and support, please reach out to the project maintainer:
- GitHub: [@Srinidhi94](https://github.com/Srinidhi94)
