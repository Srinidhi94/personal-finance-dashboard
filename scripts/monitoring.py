"""
Production Monitoring and Health Checks
Comprehensive monitoring, health checks, metrics collection, and structured logging.
"""

import os
import time
import json
import logging
import psutil
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import threading
import requests
from functools import wraps

from flask import Flask, current_app, g
from sqlalchemy import text
from models import db


@dataclass
class HealthCheckResult:
    """Health check result structure"""
    service: str
    status: str  # healthy, unhealthy, degraded
    response_time_ms: float
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


class HealthChecker:
    """Health check service for various system components"""
    
    def __init__(self, app: Optional[Flask] = None):
        self.app = app
        self.checks = {}
        self.timeout = 10  # seconds
        
        if app:
            self.init_app(app)
    
    def init_app(self, app: Flask):
        """Initialize health checker with Flask app"""
        self.app = app
        app.extensions['health_checker'] = self
        
        # Register default health checks
        self.register_check('database', self.check_database)
        self.register_check('ollama', self.check_ollama_service)
        self.register_check('filesystem', self.check_filesystem)
        self.register_check('memory', self.check_memory)
    
    def register_check(self, name: str, check_func):
        """Register a health check function"""
        self.checks[name] = check_func
    
    def check_database(self) -> HealthCheckResult:
        """Check database connectivity and performance"""
        start_time = time.time()
        
        try:
            # Test basic connectivity
            with db.engine.connect() as conn:
                result = conn.execute(text("SELECT 1")).fetchone()
                
            response_time = (time.time() - start_time) * 1000
            
            # Determine status based on response time
            if response_time > 1000:  # > 1 second
                status = "degraded"
                message = f"Database responding slowly ({response_time:.0f}ms)"
            else:
                status = "healthy"
                message = f"Database operational ({response_time:.0f}ms)"
            
            return HealthCheckResult(
                service="database",
                status=status,
                response_time_ms=response_time,
                message=message,
                details={"response_time_ms": response_time}
            )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                service="database",
                status="unhealthy",
                response_time_ms=response_time,
                message=f"Database connection failed: {str(e)}",
                details={"error_type": type(e).__name__}
            )
    
    def check_ollama_service(self) -> HealthCheckResult:
        """Check Ollama service availability"""
        start_time = time.time()
        
        try:
            ollama_url = current_app.config.get('OLLAMA_BASE_URL', 'http://localhost:11434')
            
            # Check service version endpoint
            response = requests.get(f"{ollama_url}/api/version", timeout=self.timeout)
            response_time = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                version_data = response.json()
                status = "healthy"
                message = "Ollama service operational"
                
                return HealthCheckResult(
                    service="ollama",
                    status=status,
                    response_time_ms=response_time,
                    message=message,
                    details={"version": version_data.get("version", "unknown")}
                )
            else:
                return HealthCheckResult(
                    service="ollama",
                    status="unhealthy",
                    response_time_ms=response_time,
                    message=f"Ollama service returned status {response.status_code}",
                    details={"status_code": response.status_code}
                )
                
        except requests.exceptions.ConnectionError:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                service="ollama",
                status="unhealthy",
                response_time_ms=response_time,
                message="Ollama service not reachable",
                details={"error": "Connection refused"}
            )
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                service="ollama",
                status="unhealthy",
                response_time_ms=response_time,
                message=f"Ollama service check failed: {str(e)}",
                details={"error_type": type(e).__name__}
            )
    
    def check_filesystem(self) -> HealthCheckResult:
        """Check filesystem access and permissions"""
        start_time = time.time()
        
        try:
            upload_folder = current_app.config.get('UPLOAD_FOLDER', '/app/uploads')
            
            # Check if directory exists and is writable
            if not os.path.exists(upload_folder):
                try:
                    os.makedirs(upload_folder, exist_ok=True)
                except Exception as e:
                    response_time = (time.time() - start_time) * 1000
                    return HealthCheckResult(
                        service="filesystem",
                        status="unhealthy",
                        response_time_ms=response_time,
                        message=f"Cannot create upload directory: {str(e)}",
                        details={"error_type": type(e).__name__}
                    )
            
            # Test write permission
            test_file = os.path.join(upload_folder, '.health_check_test')
            try:
                with open(test_file, 'w') as f:
                    f.write('health_check')
                os.remove(test_file)
            except Exception as e:
                response_time = (time.time() - start_time) * 1000
                return HealthCheckResult(
                    service="filesystem",
                    status="unhealthy",
                    response_time_ms=response_time,
                    message=f"Upload directory not writable: {str(e)}",
                    details={"error_type": type(e).__name__}
                )
            
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                service="filesystem",
                status="healthy",
                response_time_ms=response_time,
                message="Filesystem access operational",
                details={"upload_folder": upload_folder}
            )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                service="filesystem",
                status="unhealthy",
                response_time_ms=response_time,
                message=f"Filesystem check failed: {str(e)}",
                details={"error_type": type(e).__name__}
            )
    
    def check_memory(self) -> HealthCheckResult:
        """Check system memory usage"""
        start_time = time.time()
        
        try:
            memory = psutil.virtual_memory()
            response_time = (time.time() - start_time) * 1000
            
            memory_percent = memory.percent
            
            # Determine status based on memory usage
            if memory_percent > 90:
                status = "unhealthy"
                message = f"Critical memory usage: {memory_percent:.1f}%"
            elif memory_percent > 80:
                status = "degraded"
                message = f"High memory usage: {memory_percent:.1f}%"
            else:
                status = "healthy"
                message = f"Memory usage normal: {memory_percent:.1f}%"
            
            return HealthCheckResult(
                service="memory",
                status=status,
                response_time_ms=response_time,
                message=message,
                details={
                    "used_percent": memory_percent,
                    "available_gb": round(memory.available / (1024**3), 2)
                }
            )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                service="memory",
                status="unhealthy",
                response_time_ms=response_time,
                message=f"Memory check failed: {str(e)}",
                details={"error_type": type(e).__name__}
            )
    
    def run_all_checks(self) -> Dict[str, HealthCheckResult]:
        """Run all registered health checks"""
        results = {}
        
        for name, check_func in self.checks.items():
            try:
                results[name] = check_func()
            except Exception as e:
                results[name] = HealthCheckResult(
                    service=name,
                    status="unhealthy",
                    response_time_ms=0,
                    message=f"Health check failed: {str(e)}",
                    details={"error_type": type(e).__name__}
                )
        
        return results
    
    def get_overall_status(self, results: Dict[str, HealthCheckResult]) -> str:
        """Determine overall system status from individual checks"""
        if not results:
            return "unhealthy"
        
        statuses = [result.status for result in results.values()]
        
        if "unhealthy" in statuses:
            return "unhealthy"
        elif "degraded" in statuses:
            return "degraded"
        else:
            return "healthy"


class MetricsCollector:
    """Metrics collection and aggregation service"""
    
    def __init__(self, app: Optional[Flask] = None):
        self.app = app
        self.counters = defaultdict(int)
        self.gauges = defaultdict(float)
        self.histograms = defaultdict(list)
        self.lock = threading.Lock()
        
        if app:
            self.init_app(app)
    
    def init_app(self, app: Flask):
        """Initialize metrics collector with Flask app"""
        self.app = app
        app.extensions['metrics_collector'] = self
    
    def increment_counter(self, name: str, value: int = 1, tags: Optional[Dict[str, str]] = None):
        """Increment a counter metric"""
        with self.lock:
            key = f"{name}:{json.dumps(tags or {}, sort_keys=True)}"
            self.counters[key] += value
    
    def set_gauge(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Set a gauge metric value"""
        with self.lock:
            key = f"{name}:{json.dumps(tags or {}, sort_keys=True)}"
            self.gauges[key] = value
    
    def record_histogram(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Record a histogram value"""
        with self.lock:
            key = f"{name}:{json.dumps(tags or {}, sort_keys=True)}"
            self.histograms[key].append(value)
            
            # Keep only recent values (last 1000)
            if len(self.histograms[key]) > 1000:
                self.histograms[key] = self.histograms[key][-1000:]
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of all metrics"""
        with self.lock:
            summary = {
                "counters": dict(self.counters),
                "gauges": dict(self.gauges),
                "histograms": {},
                "collection_time": datetime.utcnow().isoformat()
            }
            
            # Calculate histogram statistics
            for key, values in self.histograms.items():
                if values:
                    summary["histograms"][key] = {
                        "count": len(values),
                        "min": min(values),
                        "max": max(values),
                        "avg": sum(values) / len(values)
                    }
        
        return summary


class StructuredLogger:
    """Structured JSON logging with trace ID support"""
    
    def __init__(self, app: Optional[Flask] = None):
        self.app = app
        self.logger = None
        
        if app:
            self.init_app(app)
    
    def init_app(self, app: Flask):
        """Initialize structured logger with Flask app"""
        self.app = app
        app.extensions['structured_logger'] = self
        
        # Configure structured logging
        self._setup_logging()
    
    def _setup_logging(self):
        """Setup structured JSON logging"""
        log_level = self.app.config.get('LOG_LEVEL', 'INFO')
        
        # Create logger
        self.logger = logging.getLogger('finance_app')
        self.logger.setLevel(getattr(logging, log_level.upper()))
        
        # Create console handler
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        
        # Remove existing handlers and add new one
        for existing_handler in self.logger.handlers[:]:
            self.logger.removeHandler(existing_handler)
        
        self.logger.addHandler(handler)
        self.logger.propagate = False
    
    def log(self, level: str, message: str, **kwargs):
        """Log structured message with context"""
        log_data = {
            'message': message,
            'timestamp': datetime.utcnow().isoformat(),
            'level': level.upper(),
            **kwargs
        }
        
        # Add trace ID if available and we're in a Flask context
        try:
            if hasattr(g, 'trace_id'):
                log_data['trace_id'] = g.trace_id
        except RuntimeError:
            # Outside Flask context, skip trace ID
            pass
        
        log_message = json.dumps(log_data)
        getattr(self.logger, level.lower())(log_message)
    
    def info(self, message: str, **kwargs):
        """Log info message"""
        self.log('info', message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message"""
        self.log('warning', message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message"""
        self.log('error', message, **kwargs)


def validate_configuration(app: Flask) -> List[str]:
    """Validate application configuration on startup"""
    errors = []
    
    # Required environment variables
    required_vars = [
        'SQLALCHEMY_DATABASE_URI',
        'SECRET_KEY',
        'DB_ENCRYPTION_KEY'
    ]
    
    for var in required_vars:
        if not app.config.get(var):
            errors.append(f"Missing required configuration: {var}")
    
    return errors


def init_monitoring(app: Flask):
    """Initialize all monitoring components"""
    # Initialize health checker
    health_checker = HealthChecker(app)
    
    # Initialize metrics collector
    metrics_collector = MetricsCollector(app)
    
    # Initialize structured logger
    structured_logger = StructuredLogger(app)
    
    # Validate configuration
    config_errors = validate_configuration(app)
    if config_errors:
        for error in config_errors:
            structured_logger.error("Configuration validation failed", error=error)
        # Don't raise error in development, just log
        if app.config.get('FLASK_ENV') == 'production':
            raise RuntimeError(f"Configuration validation failed: {config_errors}")
    
    # Log successful initialization
    structured_logger.info("Monitoring components initialized successfully")
    
    return {
        'health_checker': health_checker,
        'metrics_collector': metrics_collector,
        'structured_logger': structured_logger
    }
