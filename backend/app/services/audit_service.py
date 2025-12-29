"""Audit logging service."""

import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from app.database import get_database
from app.utils.serializers import serialize_document
from app.models.governance import AuditLog


def generate_correlation_id() -> str:
    """Generate a unique correlation ID."""
    return str(uuid.uuid4())


class AuditService:
    """Service for audit logging."""
    
    @staticmethod
    async def log(
        user_id: str,
        user_role: str,
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        campaign_id: Optional[str] = None,
        details: Dict[str, Any] = None,
        ip_address: Optional[str] = None,
        correlation_id: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None
    ) -> AuditLog:
        """Log an audit event."""
        db = get_database()
        
        audit_entry = AuditLog(
            correlation_id=correlation_id or generate_correlation_id(),
            tenant_id=tenant_id,
            user_id=user_id,
            user_role=user_role,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            campaign_id=campaign_id,
            details=details or {},
            ip_address=ip_address,
            success=success,
            error_message=error_message
        )
        await db.audit_logs.insert_one(serialize_document(audit_entry.model_dump()))
        return audit_entry


# Global service instance
audit_service = AuditService()
