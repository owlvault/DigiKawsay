"""Audit and privacy routes."""

from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Request

from app.database import get_database
from app.utils.serializers import serialize_document
from app.utils.constants import AuditAction
from app.core.dependencies import get_current_user
from app.services import audit_service, pseudonymization_service

audit_router = APIRouter(prefix="/audit", tags=["Audit"])
privacy_router = APIRouter(prefix="/privacy", tags=["Privacy"])
transcript_router = APIRouter(prefix="/transcripts", tags=["Transcripts"])


# ============== AUDIT ROUTES ==============

@audit_router.get("/")
async def get_audit_logs(
    current_user: dict = Depends(get_current_user),
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    user_id: Optional[str] = None,
    limit: int = 100
):
    """Get audit logs (admin/security_officer only)."""
    if current_user["role"] not in ["admin", "security_officer"]:
        raise HTTPException(status_code=403, detail="Sin permisos")
    
    db = get_database()
    query = {}
    if action:
        query["action"] = action
    if resource_type:
        query["resource_type"] = resource_type
    if user_id:
        query["user_id"] = user_id
    if current_user.get("tenant_id"):
        query["tenant_id"] = current_user["tenant_id"]
    
    logs = await db.audit_logs.find(query, {"_id": 0}).sort("timestamp", -1).to_list(limit)
    return logs


@audit_router.get("/actions")
async def get_audit_actions(current_user: dict = Depends(get_current_user)):
    """Get available audit actions."""
    if current_user["role"] not in ["admin", "security_officer"]:
        raise HTTPException(status_code=403, detail="Sin permisos")
    
    return {
        "actions": [
            AuditAction.LOGIN, AuditAction.LOGOUT,
            AuditAction.CONSENT_GIVEN, AuditAction.CONSENT_REVOKED,
            AuditAction.DATA_ACCESSED, AuditAction.DATA_EXPORTED,
            AuditAction.DATA_DELETED, AuditAction.DATA_VIEWED,
            AuditAction.VIEW_TRANSCRIPT, AuditAction.SECURITY_ACTION,
            AuditAction.ACCOUNT_UNLOCK, AuditAction.REIDENTIFICATION_REQUESTED,
            AuditAction.REIDENTIFICATION_APPROVED, AuditAction.REIDENTIFICATION_REJECTED
        ]
    }


@audit_router.get("/stats")
async def get_audit_stats(current_user: dict = Depends(get_current_user)):
    """Get audit statistics."""
    if current_user["role"] not in ["admin", "security_officer"]:
        raise HTTPException(status_code=403, detail="Sin permisos")
    
    db = get_database()
    total = await db.audit_logs.count_documents({})
    
    # Group by action
    pipeline = [
        {"$group": {"_id": "$action", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    by_action = await db.audit_logs.aggregate(pipeline).to_list(20)
    
    return {
        "total_entries": total,
        "by_action": {item["_id"]: item["count"] for item in by_action}
    }


# ============== PRIVACY ROUTES ==============

@privacy_router.get("/pii-scan/{transcript_id}")
async def scan_transcript_pii(
    transcript_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Scan transcript for PII."""
    if current_user["role"] not in ["admin", "facilitator", "security_officer"]:
        raise HTTPException(status_code=403, detail="Sin permisos")
    
    db = get_database()
    transcript = await db.transcripts.find_one({"id": transcript_id}, {"_id": 0})
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript no encontrado")
    
    # Scan messages for PII
    pii_findings = []
    for i, msg in enumerate(transcript.get("messages", [])):
        if msg.get("role") == "user":
            content = msg.get("content", "")
            _, redactions = pseudonymization_service.pseudonymize_text(content, str(i))
            if redactions:
                pii_findings.append({
                    "message_index": i,
                    "pii_types": [r["type"] for r in redactions]
                })
    
    return {
        "transcript_id": transcript_id,
        "is_pseudonymized": transcript.get("is_pseudonymized", False),
        "pii_findings": pii_findings
    }


# ============== TRANSCRIPT ROUTES ==============

@transcript_router.get("/campaign/{campaign_id}")
async def list_campaign_transcripts(
    campaign_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """List transcripts for a campaign."""
    if current_user["role"] not in ["admin", "security_officer"]:
        raise HTTPException(
            status_code=403,
            detail="Transcripciones solo visibles para admin/security_officer"
        )
    
    db = get_database()
    transcripts = await db.transcripts.find(
        {"campaign_id": campaign_id},
        {"_id": 0, "messages": 0}
    ).to_list(500)
    
    await audit_service.log(
        user_id=current_user["id"],
        user_role=current_user["role"],
        action=AuditAction.VIEW_TRANSCRIPT,
        resource_type="transcript_list",
        campaign_id=campaign_id,
        details={"count": len(transcripts)}
    )
    
    return transcripts


@transcript_router.get("/{transcript_id}")
async def get_transcript(
    transcript_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Get a specific transcript."""
    if current_user["role"] not in ["admin", "security_officer"]:
        raise HTTPException(status_code=403, detail="Sin permisos")
    
    db = get_database()
    transcript = await db.transcripts.find_one({"id": transcript_id}, {"_id": 0})
    if not transcript:
        raise HTTPException(status_code=404, detail="No encontrada")
    
    await audit_service.log(
        user_id=current_user["id"],
        user_role=current_user["role"],
        action=AuditAction.VIEW_TRANSCRIPT,
        resource_type="transcript",
        resource_id=transcript_id,
        campaign_id=transcript.get("campaign_id")
    )
    
    return transcript


@transcript_router.post("/{transcript_id}/pseudonymize")
async def pseudonymize_transcript_endpoint(
    transcript_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Pseudonymize a transcript."""
    if current_user["role"] not in ["admin", "facilitator"]:
        raise HTTPException(status_code=403, detail="Sin permisos")
    
    result = await pseudonymization_service.pseudonymize_transcript(transcript_id)
    return result
