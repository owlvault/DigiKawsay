"""Governance routes for RunaData."""

from datetime import datetime, timezone
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException

from app.database import get_database
from app.utils.serializers import serialize_document
from app.utils.constants import AuditAction
from app.core.dependencies import get_current_user
from app.services import audit_service
from app.services.governance_service import (
    governance_service,
    ROLE_PERMISSIONS,
    Roles,
)
from app.models import ReidentificationRequest, ReidentificationRequestCreate

governance_router = APIRouter(prefix="/governance", tags=["Governance"])
reidentification_router = APIRouter(prefix="/reidentification", tags=["Reidentification"])


# ============== GOVERNANCE ROUTES ==============

@governance_router.get("/permissions")
async def get_user_permissions(current_user: dict = Depends(get_current_user)):
    """Get permissions for current user."""
    permissions = governance_service.get_user_permissions(current_user)
    return {
        "user_id": current_user["id"],
        "role": current_user["role"],
        "permissions": permissions
    }


@governance_router.get("/roles")
async def get_available_roles(current_user: dict = Depends(get_current_user)):
    """Get available roles and their permissions."""
    if current_user["role"] not in ["admin", "security_officer"]:
        raise HTTPException(status_code=403, detail="Sin permisos")
    
    return {
        "roles": [
            {
                "name": role,
                "permissions": perms,
                "permission_count": len(perms)
            }
            for role, perms in ROLE_PERMISSIONS.items()
        ]
    }


@governance_router.get("/compliance-score")
async def get_compliance_score(current_user: dict = Depends(get_current_user)):
    """Get compliance score for tenant."""
    if current_user["role"] not in ["admin", "security_officer", "data_steward"]:
        raise HTTPException(status_code=403, detail="Sin permisos")
    
    tenant_id = current_user.get("tenant_id", "default")
    score = await governance_service.calculate_compliance_score(tenant_id)
    
    return {
        "tenant_id": tenant_id,
        "compliance_score": score,
        "status": "compliant" if score >= 80 else "needs_attention" if score >= 60 else "critical"
    }


@governance_router.get("/data-policy")
async def get_data_policy(current_user: dict = Depends(get_current_user)):
    """Get active data policy for tenant."""
    tenant_id = current_user.get("tenant_id", "default")
    policy = await governance_service.get_active_policy(tenant_id)
    
    if not policy:
        # Return default policy
        policy = {
            "id": "default",
            "retention_days": 365,
            "archive_after_days": 180,
            "anonymization_level": "pseudonymization",
            "small_group_threshold": 5
        }
    
    return policy


# ============== REIDENTIFICATION ROUTES ==============

@reidentification_router.post("/", response_model=ReidentificationRequest)
async def create_reidentification_request(
    request_data: ReidentificationRequestCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a reidentification request (dual approval required)."""
    if current_user["role"] not in ["admin", "security_officer", "facilitator"]:
        raise HTTPException(status_code=403, detail="Sin permisos")
    
    db = get_database()
    
    # Check if pseudonym exists
    vault_entry = await db.pii_vault.find_one({
        "pseudonym_id": request_data.pseudonym_id,
        "is_deleted": {"$ne": True}
    })
    if not vault_entry:
        raise HTTPException(status_code=404, detail="Pseudonym no encontrado")
    
    request_obj = ReidentificationRequest(
        tenant_id=current_user.get("tenant_id", "default"),
        pseudonym_id=request_data.pseudonym_id,
        requested_by=current_user["id"],
        reason=request_data.reason,
        campaign_id=request_data.campaign_id
    )
    await db.reidentification_requests.insert_one(
        serialize_document(request_obj.model_dump())
    )
    
    await audit_service.log(
        user_id=current_user["id"],
        user_role=current_user["role"],
        action=AuditAction.REIDENTIFICATION_REQUESTED,
        resource_type="reidentification",
        resource_id=request_obj.id,
        details={"pseudonym_id": request_data.pseudonym_id, "reason": request_data.reason}
    )
    
    return request_obj


@reidentification_router.get("/")
async def list_reidentification_requests(
    status: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """List reidentification requests."""
    if current_user["role"] not in ["admin", "security_officer"]:
        raise HTTPException(status_code=403, detail="Sin permisos")
    
    db = get_database()
    query = {}
    if status:
        query["status"] = status
    if current_user.get("tenant_id"):
        query["tenant_id"] = current_user["tenant_id"]
    
    requests = await db.reidentification_requests.find(query, {"_id": 0}).to_list(100)
    return requests


@reidentification_router.post("/{request_id}/approve")
async def approve_reidentification(
    request_id: str,
    comment: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Approve a reidentification request (part of dual approval)."""
    if current_user["role"] not in ["admin", "security_officer"]:
        raise HTTPException(status_code=403, detail="Solo admin o security_officer pueden aprobar")
    
    result = await governance_service.process_dual_approval(
        request_id=request_id,
        approver=current_user,
        approved=True,
        comment=comment
    )
    
    await audit_service.log(
        user_id=current_user["id"],
        user_role=current_user["role"],
        action=AuditAction.REIDENTIFICATION_APPROVED,
        resource_type="reidentification",
        resource_id=request_id,
        details={"approval_step": result.get("status")}
    )
    
    return result


@reidentification_router.post("/{request_id}/reject")
async def reject_reidentification(
    request_id: str,
    reason: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Reject a reidentification request."""
    if current_user["role"] not in ["admin", "security_officer"]:
        raise HTTPException(status_code=403, detail="Solo admin o security_officer pueden rechazar")
    
    result = await governance_service.process_dual_approval(
        request_id=request_id,
        approver=current_user,
        approved=False,
        comment=reason
    )
    
    await audit_service.log(
        user_id=current_user["id"],
        user_role=current_user["role"],
        action=AuditAction.REIDENTIFICATION_REJECTED,
        resource_type="reidentification",
        resource_id=request_id,
        details={"reason": reason}
    )
    
    return result
