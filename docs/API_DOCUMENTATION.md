# API Documentation

## Overview

The Personal Finance Dashboard provides a RESTful API for managing financial transactions, accounts, and analytics.

## Base URL

- **Development**: `http://localhost:5000`
- **Production**: `https://your-domain.com`

## Authentication

Currently, the API uses session-based authentication. Future versions will support API key authentication.

## Endpoints

### Dashboard & Analytics

#### GET `/`
Main dashboard with financial overview

**Response:**
```json
{
  "summary": {
    "total_transactions": 150,
    "total_income": 50000.00,
    "total_expenses": 35000.00,
    "net_balance": 15000.00,
    "account_summary": [...],
    "category_summary": [...]
  },
  "recent_transactions": [...]
}
```

#### GET `/api/charts/monthly_trends`
Monthly income vs expenses data for charts

**Response:**
```json
{
  "labels": ["Jan", "Feb", "Mar"],
  "datasets": [
    {
      "label": "Income",
      "data": [45000, 50000, 48000],
      "backgroundColor": "rgba(75, 192, 192, 0.6)"
    },
    {
      "label": "Expenses",
      "data": [30000, 35000, 32000],
      "backgroundColor": "rgba(255, 99, 132, 0.6)"
    }
  ]
}
```

#### GET `/api/charts/category_distribution`
Category-wise expense distribution

**Response:**
```json
{
  "labels": ["Food", "Transport", "Entertainment"],
  "datasets": [{
    "data": [15000, 8000, 5000],
    "backgroundColor": ["#FF6384", "#36A2EB", "#FFCE56"]
  }]
}
```

### Transactions

#### GET `/transactions`
Transaction listing page with filters

**Query Parameters:**
- `page`: Page number (default: 1)
- `per_page`: Items per page (default: 50)
- `category`: Filter by category
- `account`: Filter by account
- `date_from`: Start date (YYYY-MM-DD)
- `date_to`: End date (YYYY-MM-DD)

#### GET `/api/transactions`
Get transactions as JSON

**Query Parameters:**
- `page`: Page number
- `limit`: Items per page
- `category`: Filter by category
- `account_id`: Filter by account ID
- `start_date`: Start date
- `end_date`: End date

**Response:**
```json
{
  "transactions": [
    {
      "id": 1,
      "date": "2024-01-15",
      "description": "Grocery Store",
      "amount": -75.50,
      "category": "Food",
      "account": "Federal Bank Savings",
      "is_debit": true,
      "tags": {
        "categories": ["Food"],
        "account_type": ["Savings Account"]
      }
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 50,
    "total": 150,
    "pages": 3
  }
}
```

#### POST `/api/transactions`
Create a new transaction

**Request Body:**
```json
{
  "bank": "Federal Bank",
  "account_type": "Savings Account",
  "date": "2024-01-15",
  "description": "Coffee Shop",
  "amount": 25.00,
  "category": "Food",
  "transaction_type": "expense",
  "is_debit": true
}
```

**Response:**
```json
{
  "success": true,
  "transaction": {
    "id": 151,
    "date": "2024-01-15",
    "description": "Coffee Shop",
    "amount": -25.00,
    "category": "Food"
  }
}
```

#### PUT `/api/transactions/{id}`
Update an existing transaction

**Request Body:**
```json
{
  "description": "Updated description",
  "category": "Entertainment",
  "amount": 30.00
}
```

#### DELETE `/api/transactions/{id}`
Delete a transaction

**Response:**
```json
{
  "success": true,
  "message": "Transaction deleted successfully"
}
```

### File Upload & Processing

#### POST `/upload`
Upload and process bank statement

**Request:**
- `Content-Type`: `multipart/form-data`
- `file`: PDF/CSV/Excel file
- `bank`: Bank name
- `account_type`: Account type

**Response:**
```json
{
  "success": true,
  "redirect_url": "/review_upload/abc123",
  "message": "File uploaded successfully"
}
```

#### GET `/review_upload/{upload_id}`
Review extracted transactions before saving

**Response:**
```json
{
  "upload_id": "abc123",
  "transactions": [
    {
      "date": "2024-01-15",
      "description": "ATM Withdrawal",
      "amount": -500.00,
      "category": "Cash",
      "suggested_category": "ATM"
    }
  ],
  "summary": {
    "total_transactions": 25,
    "total_amount": -15000.00
  }
}
```

#### POST `/confirm_upload/{upload_id}`
Confirm and save extracted transactions

**Request Body:**
```json
{
  "transactions": [
    {
      "date": "2024-01-15",
      "description": "ATM Withdrawal",
      "amount": -500.00,
      "category": "Cash",
      "include": true
    }
  ]
}
```

### Categories & Accounts

#### GET `/api/categories`
Get all categories

**Response:**
```json
{
  "income_categories": ["Salary", "Freelance", "Investment"],
  "expense_categories": ["Food", "Transport", "Entertainment", "Bills"]
}
```

#### GET `/api/accounts`
Get all accounts

**Response:**
```json
{
  "accounts": [
    {
      "id": 1,
      "name": "Federal Bank Savings",
      "bank": "Federal Bank",
      "account_type": "Savings Account",
      "is_active": true
    }
  ]
}
```

### Bulk Operations

#### POST `/api/transactions/bulk_update`
Update multiple transactions

**Request Body:**
```json
{
  "transaction_ids": [1, 2, 3],
  "updates": {
    "category": "Food"
  }
}
```

#### POST `/api/transactions/bulk_delete`
Delete multiple transactions

**Request Body:**
```json
{
  "transaction_ids": [1, 2, 3]
}
```

## Error Handling

### Error Response Format

```json
{
  "error": true,
  "message": "Error description",
  "code": "ERROR_CODE",
  "details": {
    "field": "Additional error details"
  }
}
```

### HTTP Status Codes

- `200 OK`: Success
- `201 Created`: Resource created
- `400 Bad Request`: Invalid request data
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Access denied
- `404 Not Found`: Resource not found
- `422 Unprocessable Entity`: Validation errors
- `500 Internal Server Error`: Server error

### Common Error Codes

- `INVALID_DATE_FORMAT`: Date format is incorrect
- `MISSING_REQUIRED_FIELD`: Required field is missing
- `TRANSACTION_NOT_FOUND`: Transaction doesn't exist
- `UPLOAD_FAILED`: File upload failed
- `PARSING_ERROR`: Statement parsing failed
- `LLM_SERVICE_ERROR`: LLM service unavailable

## Rate Limiting

- **General API**: 100 requests per minute
- **Upload endpoints**: 10 requests per minute
- **LLM operations**: 5 requests per minute

## Data Formats

### Date Format
All dates should be in ISO 8601 format: `YYYY-MM-DD`

### Amount Format
- Positive values for income
- Negative values for expenses
- Decimal precision: 2 places
- Currency: INR (₹)

### Category Names
Standard categories are predefined. Custom categories are supported but should follow naming conventions.

## Security

### HTTPS
All production API calls must use HTTPS.

### Input Validation
All inputs are validated and sanitized to prevent injection attacks.

### Data Encryption
Sensitive transaction data is encrypted at rest using field-level encryption.

## Usage Examples

### JavaScript (Fetch API)

```javascript
// Create a new transaction
const createTransaction = async (transactionData) => {
  const response = await fetch('/api/transactions', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(transactionData)
  });
  
  return await response.json();
};

// Get transactions with filters
const getTransactions = async (filters = {}) => {
  const params = new URLSearchParams(filters);
  const response = await fetch(`/api/transactions?${params}`);
  
  return await response.json();
};
```

### Python (requests)

```python
import requests

# Create a new transaction
def create_transaction(transaction_data):
    response = requests.post(
        'http://localhost:5000/api/transactions',
        json=transaction_data
    )
    return response.json()

# Upload a statement
def upload_statement(file_path, bank, account_type):
    with open(file_path, 'rb') as f:
        files = {'file': f}
        data = {'bank': bank, 'account_type': account_type}
        response = requests.post(
            'http://localhost:5000/upload',
            files=files,
            data=data
        )
    return response.json()
```

### cURL Examples

```bash
# Get transactions
curl -X GET "http://localhost:5000/api/transactions?category=Food&limit=10"

# Create transaction
curl -X POST "http://localhost:5000/api/transactions" \
  -H "Content-Type: application/json" \
  -d '{
    "bank": "Federal Bank",
    "account_type": "Savings Account",
    "date": "2024-01-15",
    "description": "Coffee",
    "amount": -25.00,
    "category": "Food"
  }'

# Upload statement
curl -X POST "http://localhost:5000/upload" \
  -F "file=@statement.pdf" \
  -F "bank=Federal Bank" \
  -F "account_type=Savings Account"
```

## Webhooks (Future Feature)

Planned webhook support for real-time notifications:

- `transaction.created`
- `transaction.updated`
- `transaction.deleted`
- `upload.completed`
- `parsing.failed`

## API Versioning

Current API version: `v1`

Future versions will be available at `/api/v2/` endpoints.

## Support

For API support:
- Check the error response for detailed information
- Review the application logs
- Ensure all required fields are provided
- Verify data formats match the specification 