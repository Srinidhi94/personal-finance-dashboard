"""
Background Task Manager for File Upload Processing
Handles async file processing with progress tracking and thread safety
"""

import threading
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional, Callable, Any
from enum import Enum
import json
import os
import logging
import traceback
from flask import current_app
import fitz  # PyMuPDF
from collections import defaultdict

from services import DocumentProcessingService, TransactionService, TraceIDService, AuditService


class TaskStatus(Enum):
    """Task status enumeration"""
    PENDING = "pending"
    UPLOADED = "uploaded"
    EXTRACTING = "extracting"
    VALIDATING = "validating"
    COMPLETED = "completed"
    ERROR = "error"
    CANCELLED = "cancelled"


class ProgressTracker:
    """Thread-safe progress tracker for background tasks"""
    
    def __init__(self):
        self._tasks: Dict[str, Dict] = {}
        self._lock = threading.RLock()
        self._cleanup_interval = 3600  # 1 hour
        self._last_cleanup = time.time()
    
    def create_task(self, trace_id: str, user_id: str, filename: str, bank_type: str, account_id: str) -> Dict:
        """Create a new task and return its initial status"""
        with self._lock:
            task_data = {
                'trace_id': trace_id,
                'user_id': user_id,
                'filename': filename,
                'bank_type': bank_type,
                'account_id': account_id,
                'status': TaskStatus.PENDING.value,
                'progress': 0,
                'message': 'Task created, waiting to start processing',
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat(),
                'error': None,
                'results': None,
                'transactions': None,
                'metadata': {}
            }
            
            self._tasks[trace_id] = task_data
            self._cleanup_old_tasks()
            return task_data.copy()
    
    def update_task(self, trace_id: str, status: TaskStatus = None, progress: int = None, 
                   message: str = None, error: str = None, results: Dict = None, 
                   transactions: list = None, metadata: Dict = None) -> Optional[Dict]:
        """Update task status and return updated task data"""
        with self._lock:
            if trace_id not in self._tasks:
                return None
            
            task = self._tasks[trace_id]
            
            if status is not None:
                task['status'] = status.value
            if progress is not None:
                task['progress'] = min(100, max(0, progress))
            if message is not None:
                task['message'] = message
            if error is not None:
                task['error'] = error
                task['status'] = TaskStatus.ERROR.value
            if results is not None:
                task['results'] = results
            if transactions is not None:
                task['transactions'] = transactions
            if metadata is not None:
                task['metadata'].update(metadata)
            
            task['updated_at'] = datetime.now().isoformat()
            
            return task.copy()
    
    def get_task(self, trace_id: str) -> Optional[Dict]:
        """Get task status by trace ID"""
        with self._lock:
            task = self._tasks.get(trace_id)
            return task.copy() if task else None
    
    def delete_task(self, trace_id: str) -> bool:
        """Delete a task by trace ID"""
        with self._lock:
            if trace_id in self._tasks:
                del self._tasks[trace_id]
                return True
            return False
    
    def get_user_tasks(self, user_id: str) -> list:
        """Get all tasks for a specific user"""
        with self._lock:
            user_tasks = []
            for task in self._tasks.values():
                if task['user_id'] == user_id:
                    user_tasks.append(task.copy())
            return user_tasks
    
    def _cleanup_old_tasks(self):
        """Clean up tasks older than 24 hours"""
        current_time = time.time()
        
        # Only run cleanup once per hour
        if current_time - self._last_cleanup < self._cleanup_interval:
            return
        
        cutoff_time = datetime.now() - timedelta(hours=24)
        tasks_to_remove = []
        
        for trace_id, task in self._tasks.items():
            task_time = datetime.fromisoformat(task['created_at'])
            if task_time < cutoff_time:
                tasks_to_remove.append(trace_id)
        
        for trace_id in tasks_to_remove:
            del self._tasks[trace_id]
        
        self._last_cleanup = current_time


class BackgroundTaskManager:
    """Manager for background file processing tasks"""
    
    def __init__(self):
        self.progress_tracker = ProgressTracker()
        self.doc_processing_service = DocumentProcessingService()
        self.trace_service = TraceIDService()
        self.audit_service = AuditService()
        self._active_threads = {}
        self._lock = threading.RLock()
    
    def start_file_processing(self, file_path: str, filename: str, user_id: str, 
                            account_id: str, bank_type: str) -> str:
        """Start background file processing and return trace_id"""
        
        # Generate trace ID
        trace_id = self.trace_service.generate_trace_id()
        
        # Create task in progress tracker
        self.progress_tracker.create_task(
            trace_id=trace_id,
            user_id=user_id,
            filename=filename,
            bank_type=bank_type,
            account_id=account_id
        )
        
        # Start background thread
        thread = threading.Thread(
            target=self._process_file_async,
            args=(trace_id, file_path, filename, user_id, account_id, bank_type),
            daemon=True
        )
        
        with self._lock:
            self._active_threads[trace_id] = thread
        
        thread.start()
        
        return trace_id
    
    def get_task_status(self, trace_id: str) -> Optional[Dict]:
        """Get task status by trace ID"""
        return self.progress_tracker.get_task(trace_id)
    
    def get_task_results(self, trace_id: str) -> Optional[Dict]:
        """Get task results for review"""
        task = self.progress_tracker.get_task(trace_id)
        if not task or task['status'] != TaskStatus.COMPLETED.value:
            return None
        
        return {
            'trace_id': trace_id,
            'status': task['status'],
            'transactions': task['transactions'],
            'metadata': task['metadata'],
            'filename': task['filename'],
            'bank_type': task['bank_type'],
            'account_id': task['account_id']
        }
    
    def confirm_transactions(self, trace_id: str, user_id: str, 
                           transaction_confirmations: list = None) -> Dict:
        """Confirm and save transactions to database"""
        try:
            task = self.progress_tracker.get_task(trace_id)
            if not task:
                raise ValueError("Task not found")
            
            if task['user_id'] != user_id:
                raise ValueError("Unauthorized access to task")
            
            if task['status'] != TaskStatus.COMPLETED.value:
                raise ValueError("Task not ready for confirmation")
            
            transactions = task.get('transactions', [])
            if not transactions:
                raise ValueError("No transactions to confirm")
            
            # If specific confirmations provided, filter transactions
            if transaction_confirmations:
                confirmed_transactions = []
                confirmation_map = {conf['index']: conf for conf in transaction_confirmations}
                
                for i, transaction in enumerate(transactions):
                    if i in confirmation_map and confirmation_map[i].get('confirmed', True):
                        # Apply any modifications from confirmation
                        conf = confirmation_map[i]
                        if 'category' in conf:
                            transaction['category'] = conf['category']
                        if 'description' in conf:
                            transaction['description'] = conf['description']
                        confirmed_transactions.append(transaction)
                
                transactions = confirmed_transactions
            
            # Save transactions using TransactionService
            saved_transactions = []
            for transaction_data in transactions:
                try:
                    # Ensure user_id is set
                    transaction_data['user_id'] = user_id
                    
                    # Create transaction using existing service
                    transaction = TransactionService.create_transaction(transaction_data)
                    saved_transactions.append(transaction)
                    
                except Exception as e:
                    # Log individual transaction errors but continue
                    self.audit_service.log_error(
                        trace_id=trace_id,
                        user_id=user_id,
                        action="transaction_save_failed",
                        error_message=str(e),
                        metadata={"transaction_data": transaction_data}
                    )
            
            # Log successful confirmation
            self.audit_service.log_action(
                trace_id=trace_id,
                user_id=user_id,
                action="transactions_confirmed",
                metadata={
                    "total_transactions": len(transactions),
                    "saved_transactions": len(saved_transactions),
                    "filename": task['filename']
                }
            )
            
            # Clean up task
            self.progress_tracker.delete_task(trace_id)
            
            return {
                "success": True,
                "message": f"Successfully saved {len(saved_transactions)} transactions",
                "saved_count": len(saved_transactions),
                "total_count": len(transactions),
                "trace_id": trace_id
            }
            
        except Exception as e:
            self.audit_service.log_error(
                trace_id=trace_id,
                user_id=user_id,
                action="transaction_confirmation_failed",
                error_message=str(e)
            )
            raise
    
    def cancel_task(self, trace_id: str, user_id: str) -> bool:
        """Cancel a running task"""
        task = self.progress_tracker.get_task(trace_id)
        if not task or task['user_id'] != user_id:
            return False
        
        # Update task status
        self.progress_tracker.update_task(
            trace_id, 
            status=TaskStatus.CANCELLED,
            message="Task cancelled by user"
        )
        
        return True
    
    def _process_file_async(self, trace_id: str, file_path: str, filename: str, 
                          user_id: str, account_id: str, bank_type: str):
        """Background file processing with progress updates using LLM service"""
        try:
            # Update status: uploaded
            self.progress_tracker.update_task(
                trace_id,
                status=TaskStatus.UPLOADED,
                progress=10,
                message="File uploaded successfully, starting processing"
            )
            
            # Use the new LLM processing function with task manager reference
            process_file_with_llm(file_path, bank_type, account_id, trace_id, self)
            
        except Exception as e:
            # Update status: error
            error_message = str(e)
            self.progress_tracker.update_task(
                trace_id,
                status=TaskStatus.ERROR,
                message=f"Processing failed: {error_message}",
                error=error_message
            )
            
            # Log error
            self.audit_service.log_error(
                trace_id=trace_id,
                user_id=user_id,
                action="background_file_processing_failed",
                error_message=error_message,
                metadata={"filename": filename, "bank_type": bank_type}
            )
        
        finally:
            # Clean up file
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                print(f"Warning: Could not clean up file {file_path}: {e}")
            
            # Remove from active threads
            with self._lock:
                self._active_threads.pop(trace_id, None)


def process_file_with_llm(file_path, bank_type, account_id, trace_id, task_manager):
    """
    Process uploaded file using LLM with fallback to mock service.
    
    Args:
        file_path: Path to the uploaded file
        bank_type: Type of bank (e.g., "Federal Bank", "HDFC Bank")
        account_id: Account ID to associate transactions with
        trace_id: Unique trace ID for this processing session
        task_manager: Reference to the BackgroundTaskManager instance
    """
    from app import create_app
    
    # Create application context for database operations
    app = create_app()
    
    with app.app_context():
        logger = logging.getLogger(__name__)
        
        try:
            # Update status
            update_processing_status(trace_id, "extracting", 30, "Extracting content and processing with LLM", task_manager)
            
            # Extract text from PDF
            pdf_text = extract_pdf_text(file_path)
            if not pdf_text or len(pdf_text.strip()) < 100:
                raise Exception("Failed to extract meaningful text from PDF")
            
            logger.info(f"Extracted {len(pdf_text)} characters from PDF")
            
            # Try to use real LLM service first, fallback to mock if unavailable
            try:
                from llm_services.llm_service import LLMService
                llm_service = LLMService()
                
                # Test connection with a quick timeout
                import requests
                test_response = requests.get(
                    llm_service.endpoint.replace('/api/generate', '/api/version'),
                    timeout=5
                )
                
                if test_response.status_code == 200:
                    logger.info("Using real LLM service")
                    transactions = llm_service.parse_bank_statement(pdf_text, bank_type)
                else:
                    raise Exception("LLM service not responding")
                    
            except Exception as llm_error:
                logger.warning(f"Real LLM service unavailable ({llm_error}), using mock service")
                
                # Use mock service
                from llm_services.llm_service_mock import MockLLMService
                mock_service = MockLLMService()
                transactions = mock_service.parse_bank_statement(pdf_text, bank_type)
                
                # Add a note that this is mock data
                for txn in transactions:
                    txn['description'] = f"[MOCK] {txn['description']}"
            
            if not transactions:
                raise Exception("No transactions extracted from the statement")
            
            logger.info(f"Successfully parsed {len(transactions)} transactions")
            
            # Update status
            update_processing_status(trace_id, "storing", 70, f"Storing {len(transactions)} transactions in database", task_manager)
            
            # Store transactions in database
            stored_count = store_transactions_in_db(transactions, account_id, trace_id)
            
            # Update status to completed with results
            task_manager.progress_tracker.update_task(
                trace_id=trace_id,
                status=TaskStatus.COMPLETED,
                progress=100,
                message=f"Successfully processed {stored_count} transactions",
                transactions=transactions,
                metadata={
                    "bank_type": bank_type,
                    "account_id": account_id,
                    "transaction_count": len(transactions),
                    "stored_count": stored_count,
                    "pdf_length": len(pdf_text)
                }
            )
            
            logger.info(f"File processing completed successfully: {stored_count} transactions stored")
            
        except Exception as e:
            error_msg = f"LLM processing failed: {str(e)}"
            logger.error(f"File processing failed: {error_msg}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            
            # Update status to error
            update_processing_status(trace_id, "error", 30, f"Processing failed: {error_msg}", task_manager)
            
            # Log audit trail
            try:
                audit_action(
                    action="llm_processing_failed",
                    details={
                        "trace_id": trace_id,
                        "error": error_msg,
                        "file_path": file_path,
                        "bank_type": bank_type
                    }
                )
            except Exception as audit_error:
                logger.error(f"Failed to create audit error log for action: llm_processing_failed")
                logger.error(f"Audit error: {audit_error}")


def extract_pdf_text(file_path):
    """Extract text from PDF file."""
    try:
        doc = fitz.open(file_path)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text
    except Exception as e:
        raise Exception(f"Failed to extract PDF text: {e}")

def update_processing_status(trace_id, status, progress, message, task_manager):
    """Update processing status in the progress tracker."""
    try:
        # Convert status string to TaskStatus enum
        status_map = {
            "extracting": TaskStatus.EXTRACTING,
            "storing": TaskStatus.VALIDATING,
            "completed": TaskStatus.COMPLETED,
            "error": TaskStatus.ERROR
        }
        
        status_enum = status_map.get(status, TaskStatus.EXTRACTING)
        
        task_manager.progress_tracker.update_task(
            trace_id=trace_id,
            status=status_enum,
            progress=progress,
            message=message
        )
    except Exception as e:
        logging.getLogger(__name__).error(f"Failed to update status: {e}")

def store_transactions_in_db(transactions, account_id, trace_id):
    """Store transactions in the database."""
    try:
        stored_count = 0
        transaction_service = TransactionService()
        
        for txn in transactions:
            # Convert transaction to the format expected by the database
            transaction_data = {
                'account_id': account_id,
                'date': txn['date'],
                'description': txn['description'],
                'amount': txn['amount'],
                'transaction_type': txn['type'],
                'category': 'Uncategorized',  # Will be categorized later
                'trace_id': trace_id
            }
            
            # Store in database
            result = transaction_service.create_transaction(transaction_data)
            if result:
                stored_count += 1
        
        return stored_count
    except Exception as e:
        raise Exception(f"Failed to store transactions: {e}")

def audit_action(action, details):
    """Log audit action."""
    try:
        audit_service = AuditService()
        audit_service.log_action(
            user_id=details.get('user_id', 'system'),
            action=action,
            details=details
        )
    except Exception as e:
        logging.getLogger(__name__).error(f"Failed to log audit action: {e}")

# Global instance
task_manager = BackgroundTaskManager() 