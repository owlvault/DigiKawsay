"""Observability and monitoring routes."""

import time
from datetime import datetime, timezone
from typing import Dict, Optional, List
from fastapi import APIRouter, Depends, HTTPException, Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from app.database import get_database
from app.core.dependencies import get_current_user
from app.services.observability_service import (
    observability_service,
    observability_store,
    structured_logger,
)
from app.models.observability import ObservabilityDashboard

observability_router = APIRouter(prefix="/observability", tags=["Observability"])


@observability_router.get("/dashboard")
async def get_observability_dashboard(current_user: dict = Depends(get_current_user)):
    """Get complete observability dashboard data."""
    if current_user["role"] not in ["admin", "security_officer"]:
        raise HTTPException(status_code=403, detail="Sin permisos")
    
    system_metrics = observability_service.get_system_metrics()
    business_metrics = await observability_service.get_business_metrics()
    endpoint_metrics = observability_service.get_endpoint_metrics()
    
    # Check thresholds and create alerts if needed
    observability_service.check_thresholds()
    
    # Determine health status
    health_status = "healthy"
    active_alerts = observability_service.get_active_alerts()
    if any(a.get("severity") == "critical" for a in active_alerts):
        health_status = "critical"
    elif any(a.get("severity") == "high" for a in active_alerts):
        health_status = "degraded"
    
    return ObservabilityDashboard(
        system=system_metrics,
        business=business_metrics,
        endpoints=endpoint_metrics,
        recent_logs=observability_service.get_recent_logs(50),
        active_alerts=active_alerts,
        health_status=health_status
    )


@observability_router.get("/metrics/system")
async def get_system_metrics(current_user: dict = Depends(get_current_user)):
    """Get system metrics (CPU, memory, disk)."""
    if current_user["role"] not in ["admin", "security_officer"]:
        raise HTTPException(status_code=403, detail="Sin permisos")
    return observability_service.get_system_metrics()


@observability_router.get("/metrics/business")
async def get_business_metrics_endpoint(current_user: dict = Depends(get_current_user)):
    """Get business metrics."""
    if current_user["role"] not in ["admin", "security_officer", "analyst"]:
        raise HTTPException(status_code=403, detail="Sin permisos")
    return await observability_service.get_business_metrics()


@observability_router.get("/metrics/endpoints")
async def get_endpoint_metrics_list(current_user: dict = Depends(get_current_user)):
    """Get per-endpoint metrics."""
    if current_user["role"] not in ["admin", "security_officer"]:
        raise HTTPException(status_code=403, detail="Sin permisos")
    return observability_service.get_endpoint_metrics()


@observability_router.get("/metrics/prometheus")
async def get_prometheus_metrics():
    """Get metrics in Prometheus format."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@observability_router.get("/logs")
async def get_logs(
    limit: int = 100,
    level: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get recent logs."""
    if current_user["role"] not in ["admin", "security_officer"]:
        raise HTTPException(status_code=403, detail="Sin permisos")
    
    logs = observability_service.get_recent_logs(limit)
    if level:
        logs = [log for log in logs if log.get("level") == level]
    return logs


@observability_router.get("/alerts")
async def get_alerts(current_user: dict = Depends(get_current_user)):
    """Get active alerts."""
    if current_user["role"] not in ["admin", "security_officer"]:
        raise HTTPException(status_code=403, detail="Sin permisos")
    return observability_service.get_active_alerts()


@observability_router.get("/alerts/all")
async def get_all_alerts(current_user: dict = Depends(get_current_user)):
    """Get all alerts including acknowledged."""
    if current_user["role"] not in ["admin", "security_officer"]:
        raise HTTPException(status_code=403, detail="Sin permisos")
    return list(observability_store.alerts)


@observability_router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert_endpoint(
    alert_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Acknowledge an alert."""
    if current_user["role"] not in ["admin", "security_officer"]:
        raise HTTPException(status_code=403, detail="Sin permisos")
    
    success = observability_service.acknowledge_alert(alert_id, current_user["id"])
    if not success:
        raise HTTPException(status_code=404, detail="Alerta no encontrada")
    return {"message": "Alerta reconocida", "alert_id": alert_id}


@observability_router.get("/health")
async def health_check():
    """Health check endpoint (no auth required)."""
    db = get_database()
    try:
        await db.command("ping")
        db_status = "healthy"
    except:
        db_status = "unhealthy"
    
    return {
        "status": "healthy" if db_status == "healthy" else "unhealthy",
        "database": db_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime_seconds": time.time() - observability_store.start_time
    }


@observability_router.get("/thresholds")
async def get_thresholds(current_user: dict = Depends(get_current_user)):
    """Get current alert thresholds."""
    if current_user["role"] not in ["admin"]:
        raise HTTPException(status_code=403, detail="Sin permisos")
    return observability_store.thresholds


@observability_router.put("/thresholds")
async def update_thresholds(
    thresholds: Dict[str, float],
    current_user: dict = Depends(get_current_user)
):
    """Update alert thresholds."""
    if current_user["role"] not in ["admin"]:
        raise HTTPException(status_code=403, detail="Sin permisos")
    
    for key, value in thresholds.items():
        if key in observability_store.thresholds:
            observability_store.thresholds[key] = value
    
    structured_logger.info(
        "Thresholds updated",
        user_id=current_user["id"],
        thresholds=observability_store.thresholds
    )
    return observability_store.thresholds
