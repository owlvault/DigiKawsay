"""
DigiKawsay API - Modular Main Application
=========================================
Plataforma de Facilitación Conversacional con VAL

Este archivo ensambla la aplicación FastAPI usando los módulos
modularizados en /app/backend/app/
"""

import os
import time
import uuid
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Load environment variables
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Import database
from app.database import get_database, client

# Import API routers
from app.api import api_router

# Import observability services
from app.services.observability_service import (
    observability_service,
    structured_logger,
    ERRORS_TOTAL,
)


# ============== RATE LIMITER ==============
limiter = Limiter(key_func=get_remote_address, default_limits=["30/minute"])


# ============== PII SANITIZER ==============
class PIISanitizer:
    """Simple PII sanitizer for logging."""
    @staticmethod
    def sanitize(text: str) -> str:
        if '@' in text:
            parts = text.split('@')
            return f"{parts[0][:2]}***@{parts[1]}"
        return text[:50] if len(text) > 50 else text


# ============== MIDDLEWARE ==============

class ObservabilityMiddleware(BaseHTTPMiddleware):
    """Middleware for request tracking and metrics."""
    
    async def dispatch(self, request: Request, call_next):
        correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
        request.state.correlation_id = correlation_id
        
        start_time = time.time()
        
        try:
            response = await call_next(request)
            duration_ms = (time.time() - start_time) * 1000
            
            # Skip metrics endpoints to avoid recursion
            if not request.url.path.startswith("/api/observability/metrics"):
                observability_service.record_request(
                    method=request.method,
                    endpoint=request.url.path,
                    status_code=response.status_code,
                    duration_ms=duration_ms
                )
                
                structured_logger.info(
                    PIISanitizer.sanitize(f"{request.method} {request.url.path}"),
                    correlation_id=correlation_id,
                    method=request.method,
                    endpoint=request.url.path,
                    status_code=response.status_code,
                    duration_ms=round(duration_ms, 2)
                )
            
            response.headers["X-Correlation-ID"] = correlation_id
            return response
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            structured_logger.error(
                PIISanitizer.sanitize(f"Request error: {str(e)}"),
                correlation_id=correlation_id,
                method=request.method,
                endpoint=request.url.path,
                duration_ms=round(duration_ms, 2),
                error=PIISanitizer.sanitize(str(e))
            )
            ERRORS_TOTAL.labels(type="exception", endpoint=request.url.path).inc()
            raise


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
            response.headers["Pragma"] = "no-cache"
        
        return response


# ============== APPLICATION FACTORY ==============

def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    
    app = FastAPI(
        title="DigiKawsay API",
        version="0.9.0",
        description="Plataforma de Facilitación Conversacional con VAL - Modular",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json"
    )
    
    # Rate Limiter
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    
    # Include API routers
    app.include_router(api_router)
    
    # Add Middleware (order matters - last added is first executed)
    app.add_middleware(ObservabilityMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_credentials=True,
        allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
        allow_methods=["*"],
        allow_headers=["*"]
    )
    
    # Startup event
    @app.on_event("startup")
    async def startup_event():
        structured_logger.info("DigiKawsay API started", version="0.9.0")
        await create_indexes()
    
    # Shutdown event
    @app.on_event("shutdown")
    async def shutdown_event():
        structured_logger.info("DigiKawsay API shutting down")
        client.close()
    
    return app


# ============== DATABASE INDEXES ==============

async def create_indexes():
    """Create MongoDB indexes for performance optimization."""
    db = get_database()
    indexes_created = 0
    indexes_failed = 0
    
    async def safe_create_index(collection, index_spec, **kwargs):
        nonlocal indexes_created, indexes_failed
        try:
            await collection.create_index(index_spec, **kwargs)
            indexes_created += 1
        except Exception:
            indexes_failed += 1
    
    # Users collection
    await safe_create_index(db.users, "email", unique=True)
    await safe_create_index(db.users, "tenant_id")
    await safe_create_index(db.users, "role")
    await safe_create_index(db.users, [("email", 1), ("is_active", 1)])
    
    # Sessions collection
    await safe_create_index(db.sessions, "participant_id")
    await safe_create_index(db.sessions, "campaign_id")
    await safe_create_index(db.sessions, "status")
    await safe_create_index(db.sessions, [("campaign_id", 1), ("status", 1)])
    await safe_create_index(db.sessions, "created_at")
    
    # Campaigns collection
    await safe_create_index(db.campaigns, "tenant_id")
    await safe_create_index(db.campaigns, "status")
    await safe_create_index(db.campaigns, [("tenant_id", 1), ("status", 1)])
    
    # Insights collection
    await safe_create_index(db.insights, "campaign_id")
    await safe_create_index(db.insights, "tenant_id")
    await safe_create_index(db.insights, "category")
    await safe_create_index(db.insights, "status")
    await safe_create_index(db.insights, [("campaign_id", 1), ("status", 1)])
    
    # Audit logs collection
    await safe_create_index(db.audit_logs, "user_id")
    await safe_create_index(db.audit_logs, "action")
    await safe_create_index(db.audit_logs, "resource_type")
    await safe_create_index(db.audit_logs, "tenant_id")
    await safe_create_index(db.audit_logs, "timestamp")
    await safe_create_index(db.audit_logs, [("tenant_id", 1), ("timestamp", -1)])
    await safe_create_index(db.audit_logs, [("user_id", 1), ("action", 1)])
    
    # PII Vault collection
    await safe_create_index(db.pii_vault, "pseudonym", unique=True, sparse=True)
    await safe_create_index(db.pii_vault, "tenant_id")
    
    # Consent policies
    await safe_create_index(db.consent_policies, "tenant_id")
    await safe_create_index(db.consent_policies, [("tenant_id", 1), ("is_active", 1)])
    
    # Scripts collection
    await safe_create_index(db.scripts, "campaign_id")
    await safe_create_index(db.scripts, [("campaign_id", 1), ("version", -1)])
    
    # Network snapshots
    await safe_create_index(db.network_snapshots, "campaign_id")
    await safe_create_index(db.network_snapshots, "created_at")
    
    # Initiatives
    await safe_create_index(db.initiatives, "campaign_id")
    await safe_create_index(db.initiatives, "status")
    await safe_create_index(db.initiatives, [("campaign_id", 1), ("priority_score", -1)])
    
    # Rituals
    await safe_create_index(db.rituals, "campaign_id")
    await safe_create_index(db.rituals, "status")
    
    # Access policies
    await safe_create_index(db.access_policies, "tenant_id")
    await safe_create_index(db.access_policies, [("tenant_id", 1), ("is_active", 1)])
    
    # Login attempts (with TTL)
    await safe_create_index(db.login_attempts, "email")
    await safe_create_index(db.login_attempts, "ip_address")
    await safe_create_index(db.login_attempts, "timestamp")
    await safe_create_index(db.login_attempts, [("email", 1), ("timestamp", -1)])
    await safe_create_index(db.login_attempts, "timestamp", expireAfterSeconds=2592000)
    
    structured_logger.info(
        f"MongoDB indexes initialization complete",
        indexes_created=indexes_created,
        indexes_skipped=indexes_failed
    )


# ============== APPLICATION INSTANCE ==============

app = create_app()


# ============== ROOT ENDPOINTS ==============

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "DigiKawsay API v0.9.0",
        "status": "healthy",
        "docs": "/api/docs"
    }


@app.get("/health")
async def health():
    """Simple health check."""
    return {"status": "ok"}
