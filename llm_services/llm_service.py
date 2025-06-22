"""
LLM Service for bank statement parsing, transaction categorization, and chat functionality.
"""

import logging
import requests
import json
import time
from typing import List, Dict, Optional
import os
from requests.exceptions import RequestException, Timeout, ConnectionError


class LLMServiceError(Exception):
    """Custom exception for LLM service errors."""
    pass


class LLMService:
    """
    Service class for interacting with LLM (Large Language Model) endpoints.
    Provides functionality for bank statement parsing, transaction categorization, and chat queries.
    """
    
    def __init__(self, endpoint: Optional[str] = None, model: Optional[str] = None, default_timeout: int = 60):
        """
        Initialize the LLM service.
        
        Args:
            endpoint: LLM API endpoint URL. If None, uses LLM_ENDPOINT from environment
            model: Model name to use. If None, uses LLM_MODEL from environment
            default_timeout: Default request timeout in seconds for complex operations
        """
        self.endpoint = endpoint or os.getenv('LLM_ENDPOINT', 'http://localhost:11434')
        self.model = model or os.getenv('LLM_MODEL', 'llama3.2:3b')
        self.default_timeout = default_timeout
        self.categorization_timeout = 15  # Shorter timeout for simple categorization
        self.max_retries = 2  # Maximum number of retries
        
        # Set up logging
        self.logger = logging.getLogger(__name__)
        
        # Ensure endpoint ends with proper path for Ollama API
        if not self.endpoint.endswith('/api/generate'):
            self.endpoint = self.endpoint.rstrip('/') + '/api/generate'
    
    def parse_bank_statement(self, pdf_text: str, bank_name: str) -> List[Dict]:
        """
        Parse bank statement text using LLM to extract transactions.
        
        Args:
            pdf_text: Raw text extracted from PDF
            bank_name: Name of the bank (e.g., "Federal Bank")
            
        Returns:
            List of transaction dictionaries with keys: date, description, amount, type
            
        Raises:
            LLMServiceError: If LLM parsing fails
        """
        prompt = f"""
        Extract transactions from this {bank_name} statement. Return only valid JSON, no explanations.
        
        JSON format: [{{"date": "YYYY-MM-DD", "description": "text", "amount": 0.0, "type": "credit|debit"}}]
        
        Statement text:
        {pdf_text[:5000]}
        
        JSON:
        """
        
        try:
            response = self._call_llm_with_retry(prompt, timeout=self.default_timeout)
            # Try to extract JSON from response
            transactions = json.loads(response)
            
            if not isinstance(transactions, list):
                raise ValueError("Response is not a list")
                
            # Validate transaction structure
            for transaction in transactions:
                required_keys = ['date', 'description', 'amount', 'type']
                if not all(key in transaction for key in required_keys):
                    raise ValueError(f"Transaction missing required keys: {transaction}")
                    
            self.logger.info(f"Successfully parsed {len(transactions)} transactions from {bank_name} statement")
            return transactions
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse LLM response as JSON: {e}")
            raise LLMServiceError(f"LLM returned invalid JSON: {e}")
        except ValueError as e:
            self.logger.error(f"Invalid transaction data: {e}")
            raise LLMServiceError(f"Invalid transaction data: {e}")
        except Exception as e:
            self.logger.error(f"Bank statement parsing failed: {e}")
            raise LLMServiceError(f"Bank statement parsing failed: {e}")
    
    def categorize_transaction(self, description: str, amount: float) -> str:
        """
        Categorize a transaction based on its description and amount.
        
        Args:
            description: Transaction description
            amount: Transaction amount
            
        Returns:
            Category string (e.g., "Food & Dining", "Transportation", "Shopping", etc.)
            
        Raises:
            LLMServiceError: If categorization fails
        """
        prompt = f"""
        Categorize this transaction. Return only the category name, nothing else.
        
        Categories: Food & Dining, Transportation, Shopping, Entertainment, Bills & Utilities, Healthcare, Education, Travel, Investment, Transfer, Income, Other
        
        Transaction: {description}
        Amount: ₹{amount}
        
        Category:
        """
        
        try:
            category = self._call_llm_with_retry(prompt, timeout=self.categorization_timeout).strip()
            
            # Validate category
            valid_categories = [
                "Food & Dining", "Transportation", "Shopping", "Entertainment",
                "Bills & Utilities", "Healthcare", "Education", "Travel",
                "Investment", "Transfer", "Income", "Other"
            ]
            
            if category not in valid_categories:
                self.logger.warning(f"LLM returned invalid category '{category}', defaulting to 'Other'")
                category = "Other"
                
            self.logger.debug(f"Categorized '{description}' as '{category}'")
            return category
            
        except Exception as e:
            self.logger.error(f"Transaction categorization failed: {e}")
            raise LLMServiceError(f"Transaction categorization failed: {e}")
    
    def chat_query(self, user_message: str, transaction_data: List[Dict]) -> str:
        """
        Process a chat query about financial data.
        
        Args:
            user_message: User's question or message
            transaction_data: List of transaction dictionaries for context
            
        Returns:
            LLM response string
            
        Raises:
            LLMServiceError: If chat query fails
        """
        # Summarize transaction data to avoid token limits
        total_transactions = len(transaction_data)
        total_credits = sum(t['amount'] for t in transaction_data if t.get('type') == 'credit')
        total_debits = sum(t['amount'] for t in transaction_data if t.get('type') == 'debit')
        
        # Get recent transactions for context
        recent_transactions = transaction_data[-10:] if transaction_data else []
        
        prompt = f"""
        You are a financial assistant. Answer the user's question based on their transaction data.
        
        Transaction Summary:
        - Total transactions: {total_transactions}
        - Total income: ₹{total_credits:,.2f}
        - Total expenses: ₹{total_debits:,.2f}
        
        Recent transactions:
        {json.dumps(recent_transactions, indent=2)}
        
        User question: {user_message}
        
        Provide a helpful, accurate response:
        """
        
        try:
            response = self._call_llm_with_retry(prompt, timeout=self.default_timeout)
            self.logger.info(f"Processed chat query: '{user_message[:50]}...'")
            return response
            
        except Exception as e:
            self.logger.error(f"Chat query failed: {e}")
            raise LLMServiceError(f"Chat query failed: {e}")
    
    def _call_llm_with_retry(self, prompt: str, timeout: Optional[int] = None) -> str:
        """
        Make HTTP request to LLM API endpoint with retry logic and exponential backoff.
        
        Args:
            prompt: Text prompt to send to LLM
            timeout: Custom timeout in seconds. If None, uses default_timeout
            
        Returns:
            LLM response text
            
        Raises:
            LLMServiceError: If LLM API call fails after all retries
        """
        timeout = timeout or self.default_timeout
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                if attempt > 0:
                    # Exponential backoff: 2^attempt seconds
                    backoff_time = 2 ** attempt
                    self.logger.info(f"Retrying LLM call in {backoff_time} seconds (attempt {attempt + 1}/{self.max_retries + 1})")
                    time.sleep(backoff_time)
                
                return self._call_llm(prompt, timeout=timeout)
                
            except (Timeout, ConnectionError) as e:
                last_exception = e
                self.logger.warning(f"LLM call attempt {attempt + 1} failed: {e}")
                
                if attempt == self.max_retries:
                    self.logger.error(f"All {self.max_retries + 1} LLM call attempts failed")
                    break
                    
            except Exception as e:
                # For non-retryable errors, fail immediately
                self.logger.error(f"Non-retryable error in LLM call: {e}")
                raise e
        
        # If we get here, all retries failed
        raise LLMServiceError(f"LLM API call failed after {self.max_retries + 1} attempts: {last_exception}")
    
    def _call_llm(self, prompt: str, timeout: Optional[int] = None) -> str:
        """
        Make HTTP request to LLM API endpoint.
        
        Args:
            prompt: Text prompt to send to LLM
            timeout: Custom timeout in seconds. If None, uses default_timeout
            
        Returns:
            LLM response text
            
        Raises:
            LLMServiceError: If LLM API call fails
        """
        timeout = timeout or self.default_timeout
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        try:
            self.logger.debug(f"Calling LLM API at {self.endpoint} with model {self.model}, timeout: {timeout}s")
            
            response = requests.post(
                self.endpoint,
                json=payload,
                headers=headers,
                timeout=timeout
            )
            
            response.raise_for_status()
            
            # Parse Ollama API response
            response_data = response.json()
            
            if 'response' not in response_data:
                raise LLMServiceError("Invalid response format from LLM API")
                
            llm_response = response_data['response'].strip()
            
            if not llm_response:
                raise LLMServiceError("Empty response from LLM")
                
            self.logger.debug(f"LLM API call successful, response length: {len(llm_response)}")
            return llm_response
            
        except ConnectionError as e:
            self.logger.error(f"Cannot connect to LLM endpoint {self.endpoint}: {e}")
            raise ConnectionError(f"Cannot connect to LLM endpoint: {e}")
            
        except Timeout as e:
            self.logger.error(f"LLM API call timed out after {timeout}s: {e}")
            raise Timeout(f"LLM API call timed out: {e}")
            
        except RequestException as e:
            self.logger.error(f"LLM API request failed: {e}")
            raise LLMServiceError(f"LLM API request failed: {e}")
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON response from LLM API: {e}")
            raise LLMServiceError(f"Invalid JSON response from LLM API: {e}")
            
        except Exception as e:
            self.logger.error(f"Unexpected error in LLM API call: {e}")
            raise LLMServiceError(f"Unexpected error in LLM API call: {e}") 