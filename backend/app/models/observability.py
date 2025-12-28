"""Observability and monitoring models."""

from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
import uuid


# --- Log Levels ---
class LogLevel:
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertSeverity:
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# --- Structured Logging ---
class StructuredLog(BaseModel):
    timestamp: str
    level: str
    message: str
    correlation_id: Optional[str] = None
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    endpoint: Optional[str] = None
    method: Optional[str] = None
    status_code: Optional[int] = None
    duration_ms: Optional[float] = None
    extra: Dict[str, Any] = {}


# --- Alerts ---
class Alert(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    severity: str
    title: str
    message: str
    source: str
    metric_name: Optional[str] = None
    metric_value: Optional[float] = None
    threshold: Optional[float] = None
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[str] = None


# --- Metrics ---
class SystemMetrics(BaseModel):
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    memory_used_mb: float = 0.0
    disk_percent: float = 0.0
    active_connections: int = 0
    uptime_seconds: float = 0.0


class BusinessMetrics(BaseModel):
    total_users: int = 0
    active_sessions: int = 0
    total_campaigns: int = 0
    total_insights: int = 0
    messages_today: int = 0
    insights_generated_today: int = 0


class EndpointMetrics(BaseModel):
    endpoint: str
    method: str
    request_count: int = 0
    error_count: int = 0
    avg_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0


# --- Dashboard ---
class ObservabilityDashboard(BaseModel):
    system: SystemMetrics
    business: BusinessMetrics
    endpoints: List[EndpointMetrics] = []
    recent_logs: List[StructuredLog] = []
    active_alerts: List[Alert] = []
    health_status: str = "healthy"


# --- Health ---
class HealthCheck(BaseModel):
    status: str = "healthy"
    version: str = "1.0.0"
    database: str = "connected"
    uptime_seconds: float = 0.0
    checks: Dict[str, bool] = {}
