# API Documentation

## Overview

The Personal Finance Dashboard API provides endpoints for managing bank statements, transactions, and user data. All endpoints require authentication unless specified otherwise.

## Base URL

```
https://api.finance-dashboard.com/v1
```

## Authentication

### Login

```http
POST /auth/login
Content-Type: application/json

{
    "username": "string",
    "password": "string"
}

Response:
{
    "access_token": "string",
    "token_type": "Bearer",
    "expires_in": 3600
}
```

### Refresh Token

```http
POST /auth/refresh
Authorization: Bearer <refresh_token>

Response:
{
    "access_token": "string",
    "token_type": "Bearer",
    "expires_in": 3600
}
```

## Statements

### Upload Statement

```http
POST /statements/upload
Content-Type: multipart/form-data
Authorization: Bearer <token>

Form Data:
- file: PDF file
- bank: string (federal|hdfc_savings|hdfc_credit)

Response:
{
    "statement_id": "string",
    "status": "processing",
    "task_id": "string"
}
```

### Get Statement Status

```http
GET /statements/{statement_id}/status
Authorization: Bearer <token>

Response:
{
    "statement_id": "string",
    "status": "completed|processing|failed",
    "error": "string|null",
    "progress": 0.85,
    "transactions_count": 50
}
```

### Get Statement Details

```http
GET /statements/{statement_id}
Authorization: Bearer <token>

Response:
{
    "statement_id": "string",
    "bank": "string",
    "period": {
        "start_date": "2024-04-01",
        "end_date": "2024-04-30"
    },
    "totals": {
        "credits": 50000.00,
        "debits": 30000.00,
        "net": 20000.00
    },
    "metadata": {
        "account_number": "string",
        "account_type": "string",
        "bank_name": "string"
    }
}
```

### List Statements

```http
GET /statements
Authorization: Bearer <token>

Query Parameters:
- page: integer (default: 1)
- per_page: integer (default: 10)
- bank: string
- start_date: string (YYYY-MM-DD)
- end_date: string (YYYY-MM-DD)

Response:
{
    "statements": [
        {
            "statement_id": "string",
            "bank": "string",
            "period": {
                "start_date": "2024-04-01",
                "end_date": "2024-04-30"
            },
            "totals": {
                "credits": 50000.00,
                "debits": 30000.00,
                "net": 20000.00
            }
        }
    ],
    "pagination": {
        "page": 1,
        "per_page": 10,
        "total_pages": 5,
        "total_items": 45
    }
}
```

## Transactions

### List Transactions

```http
GET /transactions
Authorization: Bearer <token>

Query Parameters:
- page: integer (default: 1)
- per_page: integer (default: 50)
- statement_id: string
- start_date: string (YYYY-MM-DD)
- end_date: string (YYYY-MM-DD)
- min_amount: number
- max_amount: number
- type: string (credit|debit)
- search: string

Response:
{
    "transactions": [
        {
            "transaction_id": "string",
            "date": "2024-04-01",
            "description": "string",
            "amount": 1000.00,
            "type": "credit|debit",
            "category": "string",
            "statement_id": "string",
            "metadata": {
                "bank": "string",
                "account_type": "string"
            }
        }
    ],
    "pagination": {
        "page": 1,
        "per_page": 50,
        "total_pages": 10,
        "total_items": 456
    }
}
```

### Get Transaction Details

```http
GET /transactions/{transaction_id}
Authorization: Bearer <token>

Response:
{
    "transaction_id": "string",
    "date": "2024-04-01",
    "description": "string",
    "amount": 1000.00,
    "type": "credit|debit",
    "category": "string",
    "statement_id": "string",
    "metadata": {
        "bank": "string",
        "account_type": "string",
        "original_description": "string",
        "balance_after": 5000.00
    }
}
```

### Update Transaction

```http
PATCH /transactions/{transaction_id}
Content-Type: application/json
Authorization: Bearer <token>

Request:
{
    "category": "string",
    "description": "string",
    "metadata": {
        "tags": ["string"],
        "notes": "string"
    }
}

Response:
{
    "transaction_id": "string",
    "date": "2024-04-01",
    "description": "string",
    "amount": 1000.00,
    "type": "credit|debit",
    "category": "string",
    "metadata": {
        "tags": ["string"],
        "notes": "string"
    }
}
```

## Analytics

### Monthly Summary

```http
GET /analytics/monthly
Authorization: Bearer <token>

Query Parameters:
- year: integer
- month: integer
- bank: string

Response:
{
    "period": {
        "year": 2024,
        "month": 4
    },
    "totals": {
        "income": 50000.00,
        "expenses": 30000.00,
        "savings": 20000.00,
        "savings_rate": 0.4
    },
    "categories": {
        "income": [
            {
                "category": "Salary",
                "amount": 45000.00,
                "percentage": 0.9
            }
        ],
        "expenses": [
            {
                "category": "Groceries",
                "amount": 10000.00,
                "percentage": 0.33
            }
        ]
    },
    "trends": {
        "income": [
            {
                "date": "2024-04-01",
                "amount": 45000.00
            }
        ],
        "expenses": [
            {
                "date": "2024-04-15",
                "amount": 10000.00
            }
        ]
    }
}
```

### Category Analysis

```http
GET /analytics/categories
Authorization: Bearer <token>

Query Parameters:
- start_date: string (YYYY-MM-DD)
- end_date: string (YYYY-MM-DD)
- type: string (income|expense)

Response:
{
    "period": {
        "start_date": "2024-04-01",
        "end_date": "2024-04-30"
    },
    "categories": [
        {
            "category": "string",
            "total": 10000.00,
            "percentage": 0.33,
            "transaction_count": 15,
            "average": 666.67,
            "trend": [
                {
                    "date": "2024-04-01",
                    "amount": 1000.00
                }
            ]
        }
    ]
}
```

### Spending Insights

```http
GET /analytics/insights
Authorization: Bearer <token>

Query Parameters:
- period: string (daily|weekly|monthly)
- lookback: integer (default: 6)

Response:
{
    "insights": [
        {
            "type": "overspending",
            "category": "Dining",
            "message": "Dining expenses increased by 25% compared to last month",
            "data": {
                "current": 5000.00,
                "previous": 4000.00,
                "change": 0.25
            }
        }
    ],
    "recommendations": [
        {
            "type": "savings",
            "message": "Setting up automatic transfers could help increase savings",
            "potential_impact": 5000.00
        }
    ]
}
```

## Error Responses

### 400 Bad Request

```json
{
    "error": "validation_error",
    "message": "Invalid request parameters",
    "details": {
        "field": ["error message"]
    }
}
```

### 401 Unauthorized

```json
{
    "error": "unauthorized",
    "message": "Invalid or expired token"
}
```

### 403 Forbidden

```json
{
    "error": "forbidden",
    "message": "Insufficient permissions"
}
```

### 404 Not Found

```json
{
    "error": "not_found",
    "message": "Resource not found"
}
```

### 500 Internal Server Error

```json
{
    "error": "internal_error",
    "message": "An unexpected error occurred"
}
```

## Rate Limiting

- Rate limit: 100 requests per minute per user
- Rate limit headers included in all responses:
  * X-RateLimit-Limit
  * X-RateLimit-Remaining
  * X-RateLimit-Reset

## Webhooks

### Transaction Updates

```http
POST <webhook_url>
Content-Type: application/json
X-Webhook-Signature: string

{
    "event": "transaction.updated",
    "timestamp": "2024-04-01T12:00:00Z",
    "data": {
        "transaction_id": "string",
        "changes": {
            "category": {
                "old": "string",
                "new": "string"
            }
        }
    }
}
```

### Statement Processing

```http
POST <webhook_url>
Content-Type: application/json
X-Webhook-Signature: string

{
    "event": "statement.processed",
    "timestamp": "2024-04-01T12:00:00Z",
    "data": {
        "statement_id": "string",
        "status": "completed",
        "transactions_count": 50
    }
}
``` 