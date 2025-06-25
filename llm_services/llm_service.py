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
import re
from config import Config


class LLMServiceError(Exception):
    """Custom exception for LLM service errors."""
    pass


class LLMService:
    """
    Service class for interacting with LLM (Large Language Model) endpoints.
    Provides functionality for bank statement parsing, transaction categorization, and chat queries.
    """
    
    def __init__(self, endpoint: Optional[str] = None, model: Optional[str] = None, default_timeout: int = 120):
        """
        Initialize the LLM service.
        
        Args:
            endpoint: LLM API endpoint URL. If None, uses LLM_ENDPOINT from environment
            model: Model name to use. If None, uses LLM_MODEL from environment
            default_timeout: Default request timeout in seconds for complex operations
        """
        self.endpoint = endpoint or os.getenv('OLLAMA_BASE_URL') or os.getenv('LLM_ENDPOINT', 'http://192.168.0.118:11434')
        self.model = model or os.getenv('LLM_MODEL', 'llama3.2:1b')
        self.default_timeout = default_timeout
        self.categorization_timeout = 30  # Longer timeout for categorization
        self.max_retries = 3  # Maximum number of retries
        
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
        # Use full PDF text, not just first 5000 characters
        # Split into chunks if too large to handle token limits
        max_chunk_size = 8000  # Smaller chunk size for better processing with llama3.2:1b
        
        if len(pdf_text) > max_chunk_size:
            # Process in chunks and combine results
            chunks = [pdf_text[i:i+max_chunk_size] for i in range(0, len(pdf_text), max_chunk_size)]
            all_transactions = []
            
            for i, chunk in enumerate(chunks):
                self.logger.info(f"Processing chunk {i+1}/{len(chunks)} ({len(chunk)} characters)")
                chunk_transactions = self._parse_chunk(chunk, bank_name, i+1, len(chunks))
                all_transactions.extend(chunk_transactions)
            
            # Remove duplicates and sort by date
            unique_transactions = self._deduplicate_transactions(all_transactions)
            self.logger.info(f"Successfully parsed {len(unique_transactions)} unique transactions from {bank_name} statement")
            return unique_transactions
        else:
            return self._parse_chunk(pdf_text, bank_name, 1, 1)
    
    def _sanitize_json_string(self, json_str: str) -> str:
        """
        Sanitize JSON string to handle special characters and common LLM formatting issues.
        
        Args:
            json_str: Raw JSON string from LLM
            
        Returns:
            Sanitized JSON string
        """
        try:
            # Remove any leading/trailing whitespace
            json_str = json_str.strip()
            
            # Remove markdown code block markers if present
            json_str = re.sub(r'^```json\s*', '', json_str)
            json_str = re.sub(r'^```\s*', '', json_str)
            json_str = re.sub(r'\s*```$', '', json_str)
            
            # Fix control characters within strings - replace newlines with spaces
            # This regex finds quoted strings and replaces control characters within them
            def fix_string_content(match):
                content = match.group(1)
                # Replace control characters with spaces
                content = re.sub(r'[\x00-\x1f\x7f-\x9f]', ' ', content)
                # Replace multiple spaces with single space
                content = re.sub(r'\s+', ' ', content)
                return f'"{content.strip()}"'
            
            # Apply the fix to quoted strings
            json_str = re.sub(r'"([^"]*)"', fix_string_content, json_str)
            
            # Fix common JSON issues
            # Replace single quotes with double quotes (but be careful with apostrophes in text)
            json_str = re.sub(r"(?<!\\)'([^']*)'(?=\s*[,:\]}])", r'"\1"', json_str)
            
            # Remove trailing commas before closing brackets/braces
            json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
            
            # Fix number formatting - handle all currency and comma issues
            # Remove currency symbols and quotes around numbers
            json_str = re.sub(r'"amount":\s*"?[₹$€£¥]?\s*([+-]?\d+(?:,\d{3})*(?:\.\d+)?)"?', r'"amount": \1', json_str)
            
            # Remove commas from numbers (e.g., 78,791.65 -> 78791.65)
            def fix_number_commas(match):
                number = match.group(1).replace(',', '')
                return f'"amount": {number}'
            json_str = re.sub(r'"amount":\s*([+-]?\d+(?:,\d{3})*(?:\.\d+)?)', fix_number_commas, json_str)
            
            # Handle malformed numbers with commas in JSON (specific case from error)
            json_str = re.sub(r'(\d+),(\d+)\.(\d+)', r'\1\2.\3', json_str)  # 78,791.65 -> 78791.65
            json_str = re.sub(r'(\d+),(\d+)(?!\d)', r'\1\2', json_str)      # 78,791 -> 78791
            
            # Fix minus signs that appear as separate tokens
            json_str = re.sub(r'"amount":\s*-\s*(\d+)', r'"amount": -\1', json_str)
            
            # Handle incomplete JSON - if it's cut off, try to close it properly
            if json_str.count('[') > json_str.count(']'):
                # Try to find the last complete transaction and close the array
                last_complete = json_str.rfind('}')
                if last_complete != -1:
                    json_str = json_str[:last_complete + 1] + ']'
            
            # Final cleanup - remove any remaining control characters
            json_str = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', json_str)
            
            return json_str
            
        except Exception as e:
            self.logger.warning(f"JSON sanitization failed: {e}")
            return json_str

    def _extract_json_array(self, response: str) -> str:
        """
        Extract JSON array from LLM response, handling various formats.
        
        Args:
            response: Raw LLM response
            
        Returns:
            JSON array string
        """
        response = response.strip()
        
        # Remove markdown code blocks if present
        if response.startswith('```'):
            lines = response.split('\n')
            # Find first line that doesn't start with ``` and isn't json/JSON
            start_line = 0
            for i, line in enumerate(lines):
                if not line.startswith('```') and line.lower() != 'json':
                    start_line = i
                    break
            
            # Find last line that doesn't start with ```
            end_line = len(lines)
            for i in range(len(lines) - 1, -1, -1):
                if not lines[i].startswith('```'):
                    end_line = i + 1
                    break
            
            response = '\n'.join(lines[start_line:end_line]).strip()
        
        # Try to find the first complete JSON array
        start_idx = response.find('[')
        if start_idx != -1:
            # Count brackets to find the matching closing bracket
            bracket_count = 0
            end_idx = -1
            
            for i in range(start_idx, len(response)):
                if response[i] == '[':
                    bracket_count += 1
                elif response[i] == ']':
                    bracket_count -= 1
                    if bracket_count == 0:
                        end_idx = i + 1
                        break
            
            if end_idx != -1:
                json_array = response[start_idx:end_idx]
                return json_array
        
        # Try to find JSON object and extract array from it
        obj_start = response.find('{')
        if obj_start != -1:
            # Count braces to find the matching closing brace
            brace_count = 0
            obj_end = -1
            
            for i in range(obj_start, len(response)):
                if response[i] == '{':
                    brace_count += 1
                elif response[i] == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        obj_end = i + 1
                        break
            
            if obj_end != -1:
                try:
                    obj_str = response[obj_start:obj_end]
                    obj_str = self._sanitize_json_string(obj_str)
                    obj = json.loads(obj_str)
                    
                    # Look for array in common keys
                    for key in ['transactions', 'data', 'results', 'items']:
                        if key in obj and isinstance(obj[key], list):
                            return json.dumps(obj[key])
                    
                    # If the object itself looks like a transaction, wrap it in an array
                    if all(k in obj for k in ['date', 'description', 'amount', 'type']):
                        return json.dumps([obj])
                        
                except json.JSONDecodeError:
                    pass
        
        # Last resort: try to extract multiple JSON objects and create an array
        import re
        json_objects = []
        
        # Look for individual transaction objects
        pattern = r'\{\s*"date"\s*:\s*"[^"]+"\s*,\s*"description"\s*:\s*"[^"]+"\s*,\s*"amount"\s*:\s*[^,}]+\s*,\s*"type"\s*:\s*"[^"]+"\s*\}'
        matches = re.findall(pattern, response)
        
        for match in matches:
            try:
                obj = json.loads(self._sanitize_json_string(match))
                json_objects.append(obj)
            except json.JSONDecodeError:
                continue
        
        if json_objects:
            return json.dumps(json_objects)
        
        # If nothing worked, return original response
        return response

    def _parse_chunk(self, chunk_text: str, bank_name: str, chunk_num: int, total_chunks: int) -> List[Dict]:
        """
        Parse a chunk of PDF text using LLM to extract transaction data.
        
        Args:
            chunk_text: Text content to parse
            bank_name: Name of the bank for context
            chunk_num: Current chunk number
            total_chunks: Total number of chunks
            
        Returns:
            List of transaction dictionaries
            
        Raises:
            LLMServiceError: If parsing fails
        """
        import json
        import re
        prompt = f"""Extract transactions from this {bank_name} bank statement.

CRITICAL: Return ONLY a JSON array of transaction objects. Do NOT return any other format.

REQUIRED FORMAT (copy this exactly):
[
  {{"date": "2025-03-01", "description": "ATM withdrawal", "amount": 2000.50, "type": "debit"}},
  {{"date": "2025-03-02", "description": "Salary credit", "amount": 50000.00, "type": "credit"}}
]

RULES:
- Each transaction must be a separate object in the array
- Use "credit" for money IN, "debit" for money OUT  
- Amount must be positive number (no minus signs)
- Date format: YYYY-MM-DD
- Description: clean text without symbols
- Return ONLY the JSON array, no other text or explanations

Bank statement text:
{chunk_text}

JSON array:"""
        
        try:
            response = self._call_llm_with_retry(prompt, timeout=self.default_timeout)
            
            # Clean the response - remove any non-JSON content
            response = response.strip()
            self.logger.debug(f"Raw LLM response: {response[:200]}...")
            
            # Extract JSON array from response
            json_str = self._extract_json_array(response)
            
            # Sanitize the JSON string
            json_str = self._sanitize_json_string(json_str)
            self.logger.debug(f"Sanitized JSON: {json_str[:200]}...")
            
            # Try to parse JSON
            try:
                transactions = json.loads(json_str)
            except json.JSONDecodeError as e:
                # If parsing fails, try to fix common issues and parse again
                self.logger.warning(f"Initial JSON parse failed: {e}")
                self.logger.warning(f"Attempting more aggressive JSON cleaning...")
                
                # Handle "Extra data" error - truncate at first complete JSON array/object
                if "Extra data" in str(e):
                    # Try to extract just the first valid JSON structure
                    try:
                        # Find the first complete JSON array or object
                        decoder = json.decoder.JSONDecoder()
                        transactions, idx = decoder.raw_decode(json_str)
                        self.logger.info(f"Successfully extracted JSON from position 0 to {idx}")
                    except json.JSONDecodeError:
                        # Fall back to more aggressive cleaning
                        json_str = self._extract_json_array(json_str)
                        try:
                            transactions = json.loads(json_str)
                        except json.JSONDecodeError:
                            transactions = self._extract_transactions_from_malformed_json(json_str)
                else:
                    # Try more aggressive cleaning for other JSON errors
                    json_str = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', json_str)  # Remove control characters
                    json_str = re.sub(r'[^\x20-\x7E\u00A0-\uFFFF]', '', json_str)  # Keep only printable chars
                    
                    # Handle truncated JSON by finding the last complete object
                    if json_str.count('{') > json_str.count('}'):
                        last_brace = json_str.rfind('}')
                        if last_brace != -1:
                            json_str = json_str[:last_brace + 1] + ']'
                    
                    # Try parsing again
                    try:
                        transactions = json.loads(json_str)
                    except json.JSONDecodeError:
                        # Last resort: try to extract individual transaction objects
                        self.logger.warning("Attempting to extract individual transaction objects...")
                        transactions = self._extract_transactions_from_malformed_json(json_str)
            
            if not isinstance(transactions, list):
                raise ValueError("Response is not a list")
                
            # Validate and clean transaction structure
            validated_transactions = []
            for transaction in transactions:
                if not isinstance(transaction, dict):
                    continue
                    
                required_keys = ['date', 'description', 'amount', 'type']
                if not all(key in transaction for key in required_keys):
                    self.logger.warning(f"Transaction missing required keys: {transaction}")
                    continue
                
                # Validate and normalize data
                try:
                    # Normalize date format
                    date_str = str(transaction['date'])
                    if '/' in date_str:
                        # Convert DD/MM/YYYY to YYYY-MM-DD
                        parts = date_str.split('/')
                        if len(parts) == 3:
                            if len(parts[2]) == 4:  # DD/MM/YYYY
                                transaction['date'] = f"{parts[2]}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"
                            else:  # YYYY/MM/DD
                                transaction['date'] = date_str.replace('/', '-')
                    
                    # Ensure amount is float and handle string amounts
                    amount_str = str(transaction['amount']).replace(',', '').replace('₹', '').replace('+', '').replace('-', '').strip()
                    transaction['amount'] = float(amount_str)
                    
                    # Normalize type
                    transaction['type'] = str(transaction['type']).lower()
                    if transaction['type'] not in ['credit', 'debit']:
                        # Determine type from amount
                        if transaction['amount'] >= 0:
                            transaction['type'] = 'credit'
                        else:
                            transaction['type'] = 'debit'
                    
                    # Ensure description is string and clean it
                    transaction['description'] = str(transaction['description']).strip()
                    # Remove currency symbols from description
                    transaction['description'] = re.sub(r'[₹$€£¥]', '', transaction['description']).strip()
                    
                    validated_transactions.append(transaction)
                    
                except (ValueError, TypeError) as e:
                    self.logger.warning(f"Invalid transaction data: {transaction}, error: {e}")
                    continue
                    
            self.logger.info(f"Chunk {chunk_num}: extracted {len(validated_transactions)} transactions")
            return validated_transactions
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse LLM response as JSON: {e}")
            self.logger.error(f"Raw response: {response[:500]}...")
            self.logger.error(f"Sanitized JSON: {json_str[:500]}...")
            raise LLMServiceError(f"LLM returned invalid JSON: {e}")
        except ValueError as e:
            self.logger.error(f"Invalid transaction data: {e}")
            raise LLMServiceError(f"Invalid transaction data: {e}")
        except Exception as e:
            self.logger.error(f"Bank statement parsing failed: {e}")
            raise LLMServiceError(f"Bank statement parsing failed: {e}")

    def _extract_transactions_from_malformed_json(self, json_str: str) -> List[Dict]:
        """
        Try to extract transaction data from malformed JSON as a last resort.
        
        Args:
            json_str: Malformed JSON string
            
        Returns:
            List of transaction dictionaries
        """
        transactions = []
        
        try:
            # Try to find individual transaction objects
            import re
            
            # Look for patterns like {"date": "...", "description": "...", "amount": ..., "type": "..."}
            pattern = r'\{\s*"date"\s*:\s*"([^"]+)"\s*,\s*"description"\s*:\s*"([^"]+)"\s*,\s*"amount"\s*:\s*([^,}]+)\s*,\s*"type"\s*:\s*"([^"]+)"\s*\}'
            
            matches = re.findall(pattern, json_str)
            
            for match in matches:
                date, description, amount, txn_type = match
                try:
                    amount_clean = str(amount).replace(',', '').replace('₹', '').replace('+', '').replace('-', '').strip()
                    transactions.append({
                        'date': date.strip(),
                        'description': description.strip(),
                        'amount': float(amount_clean),
                        'type': txn_type.strip().lower()
                    })
                except ValueError:
                    continue
                    
            self.logger.info(f"Extracted {len(transactions)} transactions from malformed JSON")
            
        except Exception as e:
            self.logger.warning(f"Failed to extract transactions from malformed JSON: {e}")
            
        return transactions
    
    def _deduplicate_transactions(self, transactions: List[Dict]) -> List[Dict]:
        """Remove duplicate transactions and sort by date."""
        seen = set()
        unique_transactions = []
        
        for txn in transactions:
            # Create a unique key based on date, description, and amount
            key = (txn['date'], txn['description'], txn['amount'])
            if key not in seen:
                seen.add(key)
                unique_transactions.append(txn)
        
        # Sort by date
        try:
            unique_transactions.sort(key=lambda x: x['date'])
        except:
            pass  # If date sorting fails, return unsorted
        
        return unique_transactions
    
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
            "stream": False,
            "options": {
                "temperature": 0.1,
                "top_p": 0.9,
                "num_predict": 2048,  # Limit response length
                "stop": ["<|end|>", "###", "---"]  # Stop tokens to prevent rambling
            }
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