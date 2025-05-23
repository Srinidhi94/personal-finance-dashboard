# Contributing to Expense Tracker

Thank you for considering contributing to Expense Tracker! This document outlines the process for contributing to this project.

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment for everyone.

## How Can I Contribute?

### Reporting Bugs

- Check if the bug has already been reported in the Issues
- If not, create a new issue with a clear title and description
- Include steps to reproduce, expected behavior, and actual behavior
- Include screenshots if applicable

### Suggesting Enhancements

- First, check if your idea has already been suggested in the Issues
- If not, create a new issue with a clear title and description
- Explain why this enhancement would be useful to most users

### Pull Requests

1. Fork the repository
2. Create a new branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add or update tests as necessary
5. Update documentation if needed
6. Run tests to ensure your changes don't break existing functionality
7. Commit your changes (`git commit -m 'Add some amazing feature'`)
8. Push to your branch (`git push origin feature/amazing-feature`)
9. Open a Pull Request

## Development Process

### Setting Up Development Environment

1. Clone the repository
2. Create a virtual environment and activate it
3. Install dependencies: `pip install -r requirements.txt`
4. Run tests to make sure everything is working: `make test`

### Coding Guidelines

- Follow PEP 8 style guidelines for Python code
- Write docstrings for all functions, classes, and modules
- Include type hints where appropriate
- Write tests for new functionality

### Testing

- Run all tests before submitting a PR: `make test`
- Add tests for new features or bug fixes
- Ensure all tests pass

## Adding Support for New Banks

The expense tracker is designed to be extensible. To add support for a new bank:

1. Create a new parser module in the `parsers/` directory
2. Implement the extraction function following the pattern in other parsers
3. Update `data/account_config.json` with the new parser details
4. Add tests for the new parser

## Thank You!

Your contributions help make this project better for everyone!
