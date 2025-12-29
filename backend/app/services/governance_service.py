"""Governance Service for RunaData."""

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional

from fastapi import HTTPException

from app.database import get_database
from app.utils.serializers import serialize_document
from app.models.governance import ArchivedData


# Role-Permission definitions
class Roles:
    """All available roles in the system."""
    ADMIN = "admin"
    FACILITATOR = "facilitator"
    ANALYST = "analyst"
    PARTICIPANT = "participant"
    SPONSOR = "sponsor"
    SECURITY_OFFICER = "security_officer"
    DATA_STEWARD = "data_steward"


class Permission:
    """Granular permissions for RBAC."""
    # Transcript permissions
    VIEW_OWN_TRANSCRIPTS = "view_own_transcripts"
    VIEW_ALL_TRANSCRIPTS = "view_all_transcripts"
    EXPORT_TRANSCRIPTS = "export_transcripts"
    DELETE_TRANSCRIPTS = "delete_transcripts"
    
    # Insight permissions
    VIEW_INSIGHTS = "view_insights"
    CREATE_INSIGHTS = "create_insights"
    EDIT_INSIGHTS = "edit_insights"
    DELETE_INSIGHTS = "delete_insights"
    VALIDATE_INSIGHTS = "validate_insights"
    
    # Campaign permissions
    VIEW_CAMPAIGNS = "view_campaigns"
    CREATE_CAMPAIGNS = "create_campaigns"
    EDIT_CAMPAIGNS = "edit_campaigns"
    DELETE_CAMPAIGNS = "delete_campaigns"
    
    # User management
    VIEW_USERS = "view_users"
    CREATE_USERS = "create_users"
    EDIT_USERS = "edit_users"
    DELETE_USERS = "delete_users"
    
    # Privacy & Compliance
    VIEW_AUDIT_LOGS = "view_audit_logs"
    APPROVE_REIDENTIFICATION = "approve_reidentification"
    MANAGE_CONSENT_POLICIES = "manage_consent_policies"
    MANAGE_DATA_POLICIES = "manage_data_policies"
    
    # Analytics & Reports
    VIEW_ANALYTICS = "view_analytics"
    EXPORT_REPORTS = "export_reports"
    VIEW_NETWORK_ANALYSIS = "view_network_analysis"
    
    # Governance
    MANAGE_ROLES = "manage_roles"
    CONFIGURE_TENANT = "configure_tenant"
    ARCHIVE_DATA = "archive_data"


# Role-Permission Matrix
ROLE_PERMISSIONS = {
    Roles.ADMIN: [
        Permission.VIEW_OWN_TRANSCRIPTS, Permission.VIEW_ALL_TRANSCRIPTS,
        Permission.EXPORT_TRANSCRIPTS, Permission.DELETE_TRANSCRIPTS,
        Permission.VIEW_INSIGHTS, Permission.CREATE_INSIGHTS,
        Permission.EDIT_INSIGHTS, Permission.DELETE_INSIGHTS,
        Permission.VALIDATE_INSIGHTS,
        Permission.VIEW_CAMPAIGNS, Permission.CREATE_CAMPAIGNS,
        Permission.EDIT_CAMPAIGNS, Permission.DELETE_CAMPAIGNS,
        Permission.VIEW_USERS, Permission.CREATE_USERS,
        Permission.EDIT_USERS, Permission.DELETE_USERS,
        Permission.VIEW_AUDIT_LOGS, Permission.APPROVE_REIDENTIFICATION,
        Permission.MANAGE_CONSENT_POLICIES, Permission.MANAGE_DATA_POLICIES,
        Permission.VIEW_ANALYTICS, Permission.EXPORT_REPORTS,
        Permission.VIEW_NETWORK_ANALYSIS,
        Permission.MANAGE_ROLES, Permission.CONFIGURE_TENANT,
        Permission.ARCHIVE_DATA,
    ],
    Roles.FACILITATOR: [
        Permission.VIEW_OWN_TRANSCRIPTS, Permission.VIEW_ALL_TRANSCRIPTS,
        Permission.EXPORT_TRANSCRIPTS,
        Permission.VIEW_INSIGHTS, Permission.CREATE_INSIGHTS,
        Permission.EDIT_INSIGHTS, Permission.VALIDATE_INSIGHTS,
        Permission.VIEW_CAMPAIGNS, Permission.CREATE_CAMPAIGNS,
        Permission.EDIT_CAMPAIGNS,
        Permission.VIEW_USERS,
        Permission.VIEW_AUDIT_LOGS, Permission.MANAGE_CONSENT_POLICIES,
        Permission.VIEW_ANALYTICS, Permission.EXPORT_REPORTS,
        Permission.VIEW_NETWORK_ANALYSIS,
    ],
    Roles.ANALYST: [
        Permission.VIEW_OWN_TRANSCRIPTS,
        Permission.VIEW_INSIGHTS, Permission.CREATE_INSIGHTS,
        Permission.EDIT_INSIGHTS,
        Permission.VIEW_CAMPAIGNS,
        Permission.VIEW_ANALYTICS, Permission.EXPORT_REPORTS,
        Permission.VIEW_NETWORK_ANALYSIS,
    ],
    Roles.SPONSOR: [
        Permission.VIEW_INSIGHTS,
        Permission.VIEW_CAMPAIGNS,
        Permission.VIEW_ANALYTICS, Permission.VIEW_NETWORK_ANALYSIS,
    ],
    Roles.PARTICIPANT: [
        Permission.VIEW_OWN_TRANSCRIPTS,
        Permission.VIEW_CAMPAIGNS,
    ],
    Roles.SECURITY_OFFICER: [
        Permission.VIEW_AUDIT_LOGS, Permission.APPROVE_REIDENTIFICATION,
        Permission.VIEW_CAMPAIGNS,
        Permission.VIEW_ANALYTICS,
    ],
    Roles.DATA_STEWARD: [
        Permission.VIEW_AUDIT_LOGS,
        Permission.MANAGE_CONSENT_POLICIES, Permission.MANAGE_DATA_POLICIES,
        Permission.VIEW_CAMPAIGNS,
        Permission.VIEW_ANALYTICS, Permission.ARCHIVE_DATA,
    ],
}


class GovernanceService:
    """Service for data governance and access control."""
    
    @staticmethod
    def has_permission(user: dict, permission: str) -> bool:
        """Check if user has a specific permission."""
        role = user.get("role", "participant")
        role_perms = ROLE_PERMISSIONS.get(role, [])
        return permission in role_perms
    
    @staticmethod
    def get_user_permissions(user: dict) -> List[str]:
        """Get all permissions for a user."""
        role = user.get("role", "participant")
        return ROLE_PERMISSIONS.get(role, [])
    
    @staticmethod
    def check_permission(user: dict, permission: str):
        """Raise exception if user doesn't have permission."""
        if not GovernanceService.has_permission(user, permission):
            raise HTTPException(
                status_code=403,
                detail=f"Sin permiso: {permission}"
            )
    
    @staticmethod
    async def get_active_policy(tenant_id: str) -> Optional[Dict]:
        """Get active data policy for tenant."""
        db = get_database()
        policy = await db.data_policies.find_one(
            {"tenant_id": tenant_id, "is_active": True},
            {"_id": 0}
        )
        return policy
    
    @staticmethod
    async def check_dual_approval_status(request_id: str) -> Dict:
        """Check dual approval request status."""
        db = get_database()
        request = await db.dual_approval_requests.find_one(
            {"id": request_id},
            {"_id": 0}
        )
        if not request:
            return {"exists": False}
        
        return {
            "exists": True,
            "status": request.get("status"),
            "has_first_approval": request.get("first_approver_id") is not None,
            "has_second_approval": request.get("second_approver_id") is not None,
            "is_complete": request.get("status") in ["approved", "rejected"]
        }
    
    @staticmethod
    async def process_dual_approval(
        request_id: str,
        approver: dict,
        approved: bool,
        comment: str = None
    ) -> Dict:
        """Process a dual approval step."""
        db = get_database()
        
        request = await db.dual_approval_requests.find_one(
            {"id": request_id},
            {"_id": 0}
        )
        
        if not request:
            raise HTTPException(status_code=404, detail="Solicitud no encontrada")
        
        if request.get("status") in ["approved", "rejected"]:
            raise HTTPException(status_code=400, detail="Solicitud ya procesada")
        
        approver_role = approver.get("role")
        approver_id = approver.get("id")
        approver_name = approver.get("full_name", "Unknown")
        now = datetime.now(timezone.utc).isoformat()
        
        # Check if user already approved
        if (request.get("first_approver_id") == approver_id or 
            request.get("second_approver_id") == approver_id):
            raise HTTPException(
                status_code=400,
                detail="Ya has aprobado esta solicitud"
            )
        
        # Rejection handling
        if not approved:
            await db.dual_approval_requests.update_one(
                {"id": request_id},
                {"$set": {
                    "status": "rejected",
                    "rejected_by": approver_id,
                    "rejected_at": now,
                    "rejection_reason": comment,
                    "resolved_at": now,
                    "updated_at": now
                }}
            )
            return {"status": "rejected", "message": "Solicitud rechazada"}
        
        # First approval (admin)
        if approver_role == "admin" and not request.get("first_approver_id"):
            new_status = "first_approved"
            update_data = {
                "status": new_status,
                "first_approver_id": approver_id,
                "first_approver_name": approver_name,
                "first_approved_at": now,
                "first_approver_comment": comment,
                "updated_at": now
            }
            await db.dual_approval_requests.update_one(
                {"id": request_id},
                {"$set": update_data}
            )
            return {
                "status": new_status,
                "message": "Primera aprobación registrada. Requiere aprobación de security_officer."
            }
        
        # Second approval (security_officer)
        elif (approver_role == "security_officer" and 
              request.get("status") == "first_approved"):
            update_data = {
                "status": "approved",
                "second_approver_id": approver_id,
                "second_approver_name": approver_name,
                "second_approved_at": now,
                "second_approver_comment": comment,
                "resolved_at": now,
                "updated_at": now
            }
            await db.dual_approval_requests.update_one(
                {"id": request_id},
                {"$set": update_data}
            )
            return {
                "status": "approved",
                "message": "Solicitud aprobada completamente"
            }
        
        else:
            if approver_role == "admin" and request.get("first_approver_id"):
                raise HTTPException(
                    status_code=400,
                    detail="Ya existe aprobación de admin. Requiere security_officer."
                )
            elif (approver_role == "security_officer" and 
                  request.get("status") != "first_approved"):
                raise HTTPException(
                    status_code=400,
                    detail="Requiere primera aprobación de admin"
                )
            else:
                raise HTTPException(
                    status_code=403,
                    detail="Solo admin o security_officer pueden aprobar"
                )
    
    @staticmethod
    async def archive_old_data(
        tenant_id: str,
        policy: dict,
        archived_by: str
    ) -> Dict:
        """Archive data older than policy threshold."""
        db = get_database()
        
        archive_days = policy.get("archive_after_days", 180)
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=archive_days)
        cutoff_str = cutoff_date.isoformat()
        
        archived_count = {"transcripts": 0, "sessions": 0}
        
        # Archive old transcripts
        old_transcripts = await db.transcripts.find({
            "tenant_id": tenant_id,
            "created_at": {"$lt": cutoff_str},
            "is_archived": {"$ne": True}
        }, {"_id": 0}).to_list(1000)
        
        for transcript in old_transcripts:
            archive_record = ArchivedData(
                tenant_id=tenant_id,
                original_collection="transcripts",
                original_id=transcript.get("id"),
                data_hash=hashlib.sha256(str(transcript).encode()).hexdigest(),
                archived_by=archived_by,
                reason=f"Auto-archived per policy (>{archive_days} days old)"
            )
            await db.archived_data.insert_one(
                serialize_document(archive_record.model_dump())
            )
            await db.transcripts.update_one(
                {"id": transcript.get("id")},
                {"$set": {
                    "is_archived": True,
                    "archived_at": datetime.now(timezone.utc).isoformat()
                }}
            )
            archived_count["transcripts"] += 1
        
        # Archive old sessions
        old_sessions = await db.sessions.find({
            "tenant_id": tenant_id,
            "created_at": {"$lt": cutoff_str},
            "is_archived": {"$ne": True}
        }, {"_id": 0}).to_list(1000)
        
        for session in old_sessions:
            archive_record = ArchivedData(
                tenant_id=tenant_id,
                original_collection="sessions",
                original_id=session.get("id"),
                data_hash=hashlib.sha256(str(session).encode()).hexdigest(),
                archived_by=archived_by,
                reason=f"Auto-archived per policy (>{archive_days} days old)"
            )
            await db.archived_data.insert_one(
                serialize_document(archive_record.model_dump())
            )
            await db.sessions.update_one(
                {"id": session.get("id")},
                {"$set": {
                    "is_archived": True,
                    "archived_at": datetime.now(timezone.utc).isoformat()
                }}
            )
            archived_count["sessions"] += 1
        
        return archived_count
    
    @staticmethod
    async def calculate_compliance_score(tenant_id: str) -> float:
        """Calculate compliance score based on various factors."""
        db = get_database()
        score = 100.0
        
        # Check if data policy exists
        policy = await db.data_policies.find_one(
            {"tenant_id": tenant_id, "is_active": True}
        )
        if not policy:
            score -= 20  # No active policy
        
        # Check pending reidentification requests
        pending = await db.dual_approval_requests.count_documents({
            "tenant_id": tenant_id,
            "status": "pending"
        })
        if pending > 5:
            score -= 10
        
        # Check for non-pseudonymized transcripts
        non_pseudo = await db.transcripts.count_documents({
            "tenant_id": tenant_id,
            "is_pseudonymized": {"$ne": True}
        })
        if non_pseudo > 0:
            score -= min(20, non_pseudo * 2)
        
        # Check for missing consent
        missing_consent = await db.sessions.count_documents({
            "tenant_id": tenant_id,
            "consent_given": {"$ne": True}
        })
        if missing_consent > 0:
            score -= min(15, missing_consent * 3)
        
        return max(0, score)


# Global service instance
governance_service = GovernanceService()
