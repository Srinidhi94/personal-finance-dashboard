"""
Enhanced Monitoring Routes
Production-ready health checks, metrics endpoints, and monitoring features.
"""

import json
import uuid
from datetime import datetime, timedelta
from flask import jsonify, request, current_app, g
from dataclasses import asdict

from monitoring import HealthChecker, MetricsCollector, StructuredLogger


def register_monitoring_routes(app):
    """Register all monitoring routes with the Flask app"""
    
    # Initialize monitoring components if not already done
    if 'health_checker' not in app.extensions:
        from monitoring import init_monitoring
        init_monitoring(app)
    
    @app.route("/health", methods=["GET"])
    def health_check():
        """Basic health check endpoint"""
        try:
            health_checker = app.extensions['health_checker']
            
            # Run basic health checks
            results = health_checker.run_all_checks()
            overall_status = health_checker.get_overall_status(results)
            
            # Simple response for load balancers
            if overall_status == "healthy":
                return jsonify({
                    "status": "healthy",
                    "timestamp": datetime.utcnow().isoformat()
                }), 200
            else:
                return jsonify({
                    "status": overall_status,
                    "timestamp": datetime.utcnow().isoformat()
                }), 503  # Service Unavailable
                
        except Exception as e:
            return jsonify({
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }), 500
    
    @app.route("/health/detailed", methods=["GET"])
    def health_check_detailed():
        """Detailed health check endpoint with full diagnostics"""
        try:
            health_checker = app.extensions['health_checker']
            
            # Run all health checks
            results = health_checker.run_all_checks()
            overall_status = health_checker.get_overall_status(results)
            
            # Convert results to dict format
            detailed_results = {}
            for service, result in results.items():
                detailed_results[service] = {
                    "status": result.status,
                    "response_time_ms": result.response_time_ms,
                    "message": result.message,
                    "details": result.details,
                    "timestamp": result.timestamp.isoformat()
                }
            
            response_data = {
                "overall_status": overall_status,
                "services": detailed_results,
                "timestamp": datetime.utcnow().isoformat(),
                "environment": current_app.config.get('FLASK_ENV', 'unknown')
            }
            
            # Return appropriate status code
            status_code = 200 if overall_status == "healthy" else 503
            return jsonify(response_data), status_code
            
        except Exception as e:
            return jsonify({
                "overall_status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }), 500
    
    @app.route("/metrics", methods=["GET"])
    def metrics_endpoint():
        """Metrics endpoint for monitoring systems"""
        try:
            metrics_collector = app.extensions['metrics_collector']
            
            # Get metrics summary
            metrics_summary = metrics_collector.get_metrics_summary()
            
            # Add system metrics
            import psutil
            system_metrics = {
                "system_cpu_percent": psutil.cpu_percent(),
                "system_memory_percent": psutil.virtual_memory().percent,
                "system_disk_percent": psutil.disk_usage('/').percent,
                "system_load_avg": psutil.getloadavg()[0] if hasattr(psutil, 'getloadavg') else 0
            }
            
            # Add application metrics
            from models import Transaction, Account
            app_metrics = {
                "total_transactions": Transaction.query.count(),
                "total_accounts": Account.query.count(),
                "active_accounts": Account.query.filter_by(is_active=True).count()
            }
            
            response_data = {
                "application_metrics": app_metrics,
                "system_metrics": system_metrics,
                "custom_metrics": metrics_summary,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            return jsonify(response_data)
            
        except Exception as e:
            return jsonify({
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }), 500
    
    @app.route("/metrics/prometheus", methods=["GET"])
    def prometheus_metrics():
        """Prometheus-compatible metrics endpoint"""
        try:
            metrics_collector = app.extensions['metrics_collector']
            
            # Get metrics data
            metrics_summary = metrics_collector.get_metrics_summary()
            
            # Convert to Prometheus format
            prometheus_output = []
            
            # Add counters
            for counter_name, value in metrics_summary.get("counters", {}).items():
                # Parse counter name and tags
                if ":" in counter_name:
                    name, tags_json = counter_name.split(":", 1)
                    try:
                        tags = json.loads(tags_json)
                        tag_string = ",".join([f'{k}="{v}"' for k, v in tags.items()])
                        prometheus_output.append(f"finance_app_{name}{{{tag_string}}} {value}")
                    except:
                        prometheus_output.append(f"finance_app_{name} {value}")
                else:
                    prometheus_output.append(f"finance_app_{counter_name} {value}")
            
            # Add gauges
            for gauge_name, value in metrics_summary.get("gauges", {}).items():
                if ":" in gauge_name:
                    name, tags_json = gauge_name.split(":", 1)
                    try:
                        tags = json.loads(tags_json)
                        tag_string = ",".join([f'{k}="{v}"' for k, v in tags.items()])
                        prometheus_output.append(f"finance_app_{name}{{{tag_string}}} {value}")
                    except:
                        prometheus_output.append(f"finance_app_{name} {value}")
                else:
                    prometheus_output.append(f"finance_app_{gauge_name} {value}")
            
            # Add system metrics
            import psutil
            prometheus_output.extend([
                f"system_cpu_percent {psutil.cpu_percent()}",
                f"system_memory_percent {psutil.virtual_memory().percent}",
                f"system_disk_percent {psutil.disk_usage('/').percent}"
            ])
            
            # Add application metrics
            from models import Transaction, Account
            prometheus_output.extend([
                f"app_total_transactions {Transaction.query.count()}",
                f"app_total_accounts {Account.query.count()}",
                f"app_active_accounts {Account.query.filter_by(is_active=True).count()}"
            ])
            
            return "\n".join(prometheus_output), 200, {'Content-Type': 'text/plain'}
            
        except Exception as e:
            return f"# ERROR: {str(e)}", 500, {'Content-Type': 'text/plain'}
    
    @app.route("/debug/config", methods=["GET"])
    def debug_config():
        """Debug endpoint to check application configuration"""
        try:
            # Only show non-sensitive config
            safe_config = {}
            for key, value in current_app.config.items():
                if any(sensitive in key.lower() for sensitive in ['password', 'secret', 'key', 'token']):
                    safe_config[key] = "***REDACTED***" if value else None
                else:
                    safe_config[key] = value
            
            return jsonify({
                "config": safe_config,
                "environment": current_app.config.get('FLASK_ENV', 'unknown'),
                "timestamp": datetime.utcnow().isoformat()
            })
            
        except Exception as e:
            return jsonify({
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }), 500
    
    @app.route("/debug/trace/<trace_id>", methods=["GET"])
    def debug_trace(trace_id):
        """Debug endpoint to trace specific operations"""
        try:
            # Validate trace ID format
            try:
                uuid.UUID(trace_id)
            except ValueError:
                return jsonify({"error": "Invalid trace ID format"}), 400
            
            # Get trace information from background tasks
            from background_tasks import task_manager
            
            trace_info = {
                "trace_id": trace_id,
                "timestamp": datetime.utcnow().isoformat(),
                "status": "not_found"
            }
            
            # Check if trace exists in task manager
            status = task_manager.get_task_status(trace_id)
            if status:
                trace_info.update({
                    "status": status.get("status", "unknown"),
                    "progress": status.get("progress", 0),
                    "message": status.get("message", ""),
                    "created_at": status.get("created_at", ""),
                    "details": status.get("details", {})
                })
            
            return jsonify(trace_info)
            
        except Exception as e:
            return jsonify({
                "error": str(e),
                "trace_id": trace_id,
                "timestamp": datetime.utcnow().isoformat()
            }), 500
    
    @app.route("/debug/logs", methods=["GET"])
    def debug_logs():
        """Debug endpoint to view recent application logs"""
        try:
            # Get recent log entries (this is a simplified implementation)
            # In production, you'd typically read from log files or a logging service
            
            log_level = request.args.get('level', 'INFO').upper()
            limit = min(int(request.args.get('limit', 100)), 1000)  # Max 1000 entries
            
            # For now, return a placeholder response
            # In a real implementation, you'd read from your logging system
            
            return jsonify({
                "message": "Log endpoint not fully implemented",
                "note": "This would return recent application logs in production",
                "requested_level": log_level,
                "requested_limit": limit,
                "timestamp": datetime.utcnow().isoformat()
            })
            
        except Exception as e:
            return jsonify({
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }), 500
    
    # Middleware to add trace IDs to requests
    @app.before_request
    def add_trace_id():
        """Add trace ID to request context for logging"""
        if not hasattr(g, 'trace_id'):
            g.trace_id = str(uuid.uuid4())
    
    # Middleware to record request metrics
    @app.before_request
    def record_request_start():
        """Record request start time for metrics"""
        g.request_start_time = datetime.utcnow()
    
    @app.after_request
    def record_request_metrics(response):
        """Record request completion metrics"""
        try:
            if hasattr(g, 'request_start_time') and 'metrics_collector' in current_app.extensions:
                metrics_collector = current_app.extensions['metrics_collector']
                
                # Calculate request duration
                duration = (datetime.utcnow() - g.request_start_time).total_seconds() * 1000
                
                # Record metrics
                tags = {
                    'method': request.method,
                    'endpoint': request.endpoint or 'unknown',
                    'status_code': str(response.status_code)
                }
                
                metrics_collector.record_histogram('request_duration_ms', duration, tags)
                metrics_collector.increment_counter('requests_total', tags=tags)
                
                # Record error metrics
                if response.status_code >= 400:
                    error_tags = tags.copy()
                    error_tags['error_type'] = 'http_error'
                    metrics_collector.increment_counter('errors_total', tags=error_tags)
        
        except Exception:
            # Don't let metrics recording break the response
            pass
        
        return response
    
    # Error handlers with metrics
    @app.errorhandler(404)
    def not_found(error):
        """Handle 404 errors with metrics"""
        if 'metrics_collector' in current_app.extensions:
            metrics_collector = current_app.extensions['metrics_collector']
            metrics_collector.increment_counter('errors_total', tags={'error_type': '404'})
        
        return jsonify({
            "error": "Not found",
            "status_code": 404,
            "timestamp": datetime.utcnow().isoformat()
        }), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 errors with metrics and logging"""
        if 'metrics_collector' in current_app.extensions:
            metrics_collector = current_app.extensions['metrics_collector']
            metrics_collector.increment_counter('errors_total', tags={'error_type': '500'})
        
        if 'structured_logger' in current_app.extensions:
            structured_logger = current_app.extensions['structured_logger']
            structured_logger.error("Internal server error", error=str(error))
        
        return jsonify({
            "error": "Internal server error",
            "status_code": 500,
            "timestamp": datetime.utcnow().isoformat()
        }), 500 