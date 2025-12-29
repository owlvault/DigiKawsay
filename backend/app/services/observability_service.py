"""Observability Service for monitoring and logging."""

import sys
import time
import json
import logging
import uuid
from collections import defaultdict, deque
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

import psutil
from prometheus_client import Counter, Histogram, Gauge

from app.database import get_database
from app.models.observability import (
    StructuredLog,
    Alert,
    SystemMetrics,
    BusinessMetrics,
    EndpointMetrics
)


class LogLevel:
    """Log level constants."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertSeverity:
    """Alert severity constants."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# Prometheus Metrics
REQUESTS_TOTAL = Counter(
    'digikawsay_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

REQUEST_LATENCY = Histogram(
    'digikawsay_request_latency_seconds',
    'Request latency in seconds',
    ['method', 'endpoint'],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

ACTIVE_USERS = Gauge(
    'digikawsay_active_users',
    'Number of active users'
)

DB_OPERATIONS = Counter(
    'digikawsay_db_operations_total',
    'Total database operations',
    ['operation', 'collection']
)

ERRORS_TOTAL = Counter(
    'digikawsay_errors_total',
    'Total errors',
    ['type', 'endpoint']
)


class ObservabilityStore:
    """In-memory storage for recent logs and metrics."""
    
    def __init__(self, max_logs: int = 1000, max_alerts: int = 100):
        self.logs: deque = deque(maxlen=max_logs)
        self.alerts: deque = deque(maxlen=max_alerts)
        self.endpoint_metrics: Dict[str, Dict] = defaultdict(lambda: {
            "request_count": 0,
            "error_count": 0,
            "latencies": deque(maxlen=1000)
        })
        self.start_time = time.time()
        self.thresholds = {
            "error_rate": 0.1,  # 10% error rate
            "latency_p95_ms": 2000,  # 2 seconds
            "memory_percent": 90,
            "cpu_percent": 90
        }


# Global store instance
observability_store = ObservabilityStore()


class StructuredLogger:
    """JSON structured logger."""
    
    def __init__(self, name: str = "digikawsay"):
        self.name = name
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        # Remove existing handlers
        self.logger.handlers = []
        
        # JSON formatter
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter('%(message)s'))
        self.logger.addHandler(handler)
    
    def _format_log(self, level: str, message: str, **kwargs) -> StructuredLog:
        """Format a log entry."""
        log = StructuredLog(
            timestamp=datetime.now(timezone.utc).isoformat(),
            level=level,
            message=message,
            correlation_id=kwargs.get("correlation_id"),
            user_id=kwargs.get("user_id"),
            tenant_id=kwargs.get("tenant_id"),
            endpoint=kwargs.get("endpoint"),
            method=kwargs.get("method"),
            status_code=kwargs.get("status_code"),
            duration_ms=kwargs.get("duration_ms"),
            extra={k: v for k, v in kwargs.items() if k not in [
                "correlation_id", "user_id", "tenant_id", "endpoint",
                "method", "status_code", "duration_ms"
            ]}
        )
        return log
    
    def _log(self, level: str, message: str, **kwargs):
        """Internal log method."""
        log = self._format_log(level, message, **kwargs)
        observability_store.logs.append(log.model_dump())
        
        # Output JSON to stdout
        log_dict = log.model_dump()
        self.logger.log(
            getattr(logging, level.upper(), logging.INFO),
            json.dumps(log_dict)
        )
        return log
    
    def debug(self, message: str, **kwargs):
        """Log debug message."""
        return self._log(LogLevel.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """Log info message."""
        return self._log(LogLevel.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message."""
        return self._log(LogLevel.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message."""
        return self._log(LogLevel.ERROR, message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log critical message."""
        return self._log(LogLevel.CRITICAL, message, **kwargs)


# Global logger instance
structured_logger = StructuredLogger()


class ObservabilityService:
    """Service for observability metrics and monitoring."""
    
    @staticmethod
    def record_request(
        method: str,
        endpoint: str,
        status_code: int,
        duration_ms: float
    ):
        """Record request metrics."""
        key = f"{method}:{endpoint}"
        observability_store.endpoint_metrics[key]["request_count"] += 1
        observability_store.endpoint_metrics[key]["latencies"].append(duration_ms)
        
        if status_code >= 400:
            observability_store.endpoint_metrics[key]["error_count"] += 1
            ERRORS_TOTAL.labels(type="http", endpoint=endpoint).inc()
        
        # Prometheus metrics
        REQUESTS_TOTAL.labels(
            method=method,
            endpoint=endpoint,
            status=str(status_code)
        ).inc()
        REQUEST_LATENCY.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration_ms / 1000)
    
    @staticmethod
    def get_system_metrics() -> SystemMetrics:
        """Get current system metrics."""
        try:
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            return SystemMetrics(
                cpu_percent=psutil.cpu_percent(interval=0.1),
                memory_percent=memory.percent,
                memory_used_mb=memory.used / (1024 * 1024),
                disk_percent=disk.percent,
                active_connections=len(psutil.net_connections()),
                uptime_seconds=time.time() - observability_store.start_time
            )
        except Exception as e:
            structured_logger.error(f"Error getting system metrics: {e}")
            return SystemMetrics()
    
    @staticmethod
    async def get_business_metrics() -> BusinessMetrics:
        """Get business metrics from database."""
        try:
            db = get_database()
            today_start = datetime.now(timezone.utc).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            today_str = today_start.isoformat()
            
            total_users = await db.users.count_documents({})
            active_sessions = await db.sessions.count_documents({"status": "active"})
            total_campaigns = await db.campaigns.count_documents({})
            total_insights = await db.insights.count_documents({})
            messages_today = await db.sessions.count_documents({
                "created_at": {"$gte": today_str}
            })
            insights_today = await db.insights.count_documents({
                "created_at": {"$gte": today_str}
            })
            
            ACTIVE_USERS.set(total_users)
            
            return BusinessMetrics(
                total_users=total_users,
                active_sessions=active_sessions,
                total_campaigns=total_campaigns,
                total_insights=total_insights,
                messages_today=messages_today,
                insights_generated_today=insights_today
            )
        except Exception as e:
            structured_logger.error(f"Error getting business metrics: {e}")
            return BusinessMetrics()
    
    @staticmethod
    def get_endpoint_metrics() -> List[EndpointMetrics]:
        """Get metrics per endpoint."""
        metrics = []
        for key, data in observability_store.endpoint_metrics.items():
            method, endpoint = key.split(":", 1)
            latencies = list(data["latencies"])
            
            if latencies:
                sorted_latencies = sorted(latencies)
                avg = sum(latencies) / len(latencies)
                p95_idx = int(len(sorted_latencies) * 0.95)
                p99_idx = int(len(sorted_latencies) * 0.99)
                p95 = sorted_latencies[p95_idx] if p95_idx < len(sorted_latencies) else sorted_latencies[-1]
                p99 = sorted_latencies[p99_idx] if p99_idx < len(sorted_latencies) else sorted_latencies[-1]
            else:
                avg = p95 = p99 = 0
            
            metrics.append(EndpointMetrics(
                endpoint=endpoint,
                method=method,
                request_count=data["request_count"],
                error_count=data["error_count"],
                avg_latency_ms=round(avg, 2),
                p95_latency_ms=round(p95, 2),
                p99_latency_ms=round(p99, 2)
            ))
        
        return sorted(metrics, key=lambda x: -x.request_count)[:20]
    
    @staticmethod
    def create_alert(
        severity: str,
        title: str,
        message: str,
        source: str,
        metric_name: str = None,
        metric_value: float = None,
        threshold: float = None
    ) -> Alert:
        """Create a new alert."""
        alert = Alert(
            severity=severity,
            title=title,
            message=message,
            source=source,
            metric_name=metric_name,
            metric_value=metric_value,
            threshold=threshold
        )
        observability_store.alerts.append(alert.model_dump())
        structured_logger.warning(
            f"Alert created: {title}",
            alert_id=alert.id,
            severity=severity
        )
        return alert
    
    @staticmethod
    def check_thresholds() -> List[Alert]:
        """Check metrics against thresholds and create alerts."""
        alerts = []
        system_metrics = ObservabilityService.get_system_metrics()
        
        # Check CPU
        if system_metrics.cpu_percent > observability_store.thresholds["cpu_percent"]:
            alert = ObservabilityService.create_alert(
                severity=AlertSeverity.HIGH,
                title="High CPU Usage",
                message=f"CPU usage is {system_metrics.cpu_percent}%",
                source="system",
                metric_name="cpu_percent",
                metric_value=system_metrics.cpu_percent,
                threshold=observability_store.thresholds["cpu_percent"]
            )
            alerts.append(alert)
        
        # Check Memory
        if system_metrics.memory_percent > observability_store.thresholds["memory_percent"]:
            alert = ObservabilityService.create_alert(
                severity=AlertSeverity.HIGH,
                title="High Memory Usage",
                message=f"Memory usage is {system_metrics.memory_percent}%",
                source="system",
                metric_name="memory_percent",
                metric_value=system_metrics.memory_percent,
                threshold=observability_store.thresholds["memory_percent"]
            )
            alerts.append(alert)
        
        return alerts
    
    @staticmethod
    def get_recent_logs(limit: int = 100) -> List[Dict]:
        """Get recent logs."""
        logs = list(observability_store.logs)
        return logs[-limit:] if len(logs) > limit else logs
    
    @staticmethod
    def get_active_alerts() -> List[Dict]:
        """Get active (unacknowledged) alerts."""
        return [
            alert for alert in observability_store.alerts
            if not alert.get("acknowledged")
        ]
    
    @staticmethod
    def acknowledge_alert(alert_id: str, user_id: str) -> bool:
        """Acknowledge an alert."""
        for alert in observability_store.alerts:
            if alert.get("id") == alert_id:
                alert["acknowledged"] = True
                alert["acknowledged_by"] = user_id
                alert["acknowledged_at"] = datetime.now(timezone.utc).isoformat()
                return True
        return False


# Global service instance
observability_service = ObservabilityService()
