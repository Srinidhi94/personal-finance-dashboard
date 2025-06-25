"""
Centralized configuration for transaction categories
"""

# Expense categories
EXPENSE_CATEGORIES = [
    "Food",
    "Gifts", 
    "Health/medical",
    "Home",
    "Transportation",
    "Personal",
    "Pets",
    "Family",
    "Travel",
    "Debt",
    "Other",
    "Rent",
    "Credit Card",
    "Alcohol",
    "Consumables",
    "Investments",
]

# Income categories
INCOME_CATEGORIES = [
    "Savings",
    "Paycheck", 
    "Bonus",
    "Interest",
    "Splitwise",
    "RSU"
]

# All categories combined
ALL_CATEGORIES = EXPENSE_CATEGORIES + INCOME_CATEGORIES

# Account types
ACCOUNT_TYPES = [
    "Savings Account",
    "Credit Card"
]

# Supported banks
BANKS = [
    "HDFC Bank",
    "Federal Bank"
]

def get_expense_categories():
    """Get list of expense categories"""
    return EXPENSE_CATEGORIES.copy()

def get_income_categories():
    """Get list of income categories"""
    return INCOME_CATEGORIES.copy()

def get_all_categories():
    """Get list of all categories"""
    return ALL_CATEGORIES.copy()

def get_account_types():
    """Get list of account types"""
    return ACCOUNT_TYPES.copy()

def get_banks():
    """Get list of supported banks"""
    return BANKS.copy()

def is_expense_category(category):
    """Check if category is an expense category"""
    return category in EXPENSE_CATEGORIES

def is_income_category(category):
    """Check if category is an income category"""
    return category in INCOME_CATEGORIES
