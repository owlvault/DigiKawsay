"""Governance and data policy models for RunaData."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field
import uuid

from app.models.base import TimestampMixin


# --- Roles and Permissions ---
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
        Permission.EDIT_INSIGHTS, Permission.DELETE_INSIGHTS, Permission.VALIDATE_INSIGHTS,
        Permission.VIEW_CAMPAIGNS, Permission.CREATE_CAMPAIGNS,
        Permission.EDIT_CAMPAIGNS, Permission.DELETE_CAMPAIGNS,
        Permission.VIEW_USERS, Permission.CREATE_USERS,
        Permission.EDIT_USERS, Permission.DELETE_USERS,
        Permission.VIEW_AUDIT_LOGS, Permission.APPROVE_REIDENTIFICATION,
        Permission.MANAGE_CONSENT_POLICIES, Permission.MANAGE_DATA_POLICIES,
        Permission.VIEW_ANALYTICS, Permission.EXPORT_REPORTS, Permission.VIEW_NETWORK_ANALYSIS,
        Permission.MANAGE_ROLES, Permission.CONFIGURE_TENANT, Permission.ARCHIVE_DATA,
    ],
    Roles.FACILITATOR: [
        Permission.VIEW_OWN_TRANSCRIPTS, Permission.VIEW_ALL_TRANSCRIPTS,
        Permission.EXPORT_TRANSCRIPTS,
        Permission.VIEW_INSIGHTS, Permission.CREATE_INSIGHTS,
        Permission.EDIT_INSIGHTS, Permission.VALIDATE_INSIGHTS,
        Permission.VIEW_CAMPAIGNS, Permission.CREATE_CAMPAIGNS, Permission.EDIT_CAMPAIGNS,
        Permission.VIEW_USERS,
        Permission.VIEW_AUDIT_LOGS, Permission.MANAGE_CONSENT_POLICIES,
        Permission.VIEW_ANALYTICS, Permission.EXPORT_REPORTS, Permission.VIEW_NETWORK_ANALYSIS,
    ],
    Roles.ANALYST: [
        Permission.VIEW_OWN_TRANSCRIPTS,
        Permission.VIEW_INSIGHTS, Permission.CREATE_INSIGHTS, Permission.EDIT_INSIGHTS,
        Permission.VIEW_CAMPAIGNS,
        Permission.VIEW_ANALYTICS, Permission.EXPORT_REPORTS, Permission.VIEW_NETWORK_ANALYSIS,
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


# --- Data Policy ---
class DataPolicy(TimestampMixin):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    name: str
    description: Optional[str] = None
    retention_days: int = 365
    archive_after_days: int = 180
    auto_anonymize_days: int = 90
    allow_transcript_export: bool = False
    allow_insight_export: bool = True
    allow_bulk_export: bool = False
    require_approval_for_export: bool = True
    anonymization_level: str = "standard"
    suppress_small_groups: bool = True
    min_group_size: int = 5
    is_active: bool = True
    created_by: str
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None


class DataPolicyCreate(BaseModel):
    name: str
    description: Optional[str] = None
    retention_days: int = 365
    archive_after_days: int = 180
    auto_anonymize_days: int = 90
    allow_transcript_export: bool = False
    allow_insight_export: bool = True
    allow_bulk_export: bool = False
    require_approval_for_export: bool = True
    anonymization_level: str = "standard"
    suppress_small_groups: bool = True
    min_group_size: int = 5


class DataPolicyUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    retention_days: Optional[int] = None
    archive_after_days: Optional[int] = None
    auto_anonymize_days: Optional[int] = None
    allow_transcript_export: Optional[bool] = None
    allow_insight_export: Optional[bool] = None
    allow_bulk_export: Optional[bool] = None
    require_approval_for_export: Optional[bool] = None
    anonymization_level: Optional[str] = None
    suppress_small_groups: Optional[bool] = None
    min_group_size: Optional[int] = None
    is_active: Optional[bool] = None


# --- Archived Data ---
class ArchivedData(TimestampMixin):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    original_collection: str
    original_id: str
    data_hash: str
    archived_by: str
    reason: str
    restore_allowed: bool = True
    expires_at: Optional[str] = None


# --- Dual Approval ---
class DualApprovalRequest(TimestampMixin):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    request_type: str
    resource_type: str
    resource_id: str
    requested_by: str
    requested_by_name: str
    justification: str
    status: str = "pending"
    first_approver_id: Optional[str] = None
    first_approver_name: Optional[str] = None
    first_approved_at: Optional[str] = None
    first_approver_comment: Optional[str] = None
    second_approver_id: Optional[str] = None
    second_approver_name: Optional[str] = None
    second_approved_at: Optional[str] = None
    second_approver_comment: Optional[str] = None
    rejected_by: Optional[str] = None
    rejected_at: Optional[str] = None
    rejection_reason: Optional[str] = None
    resolved_at: Optional[str] = None
    result_data: Optional[Dict[str, Any]] = None


class DualApprovalCreate(BaseModel):
    request_type: str
    resource_type: str
    resource_id: str
    justification: str


# --- Metrics ---
class GovernanceMetrics(BaseModel):
    total_policies: int = 0
    active_policies: int = 0
    pending_approvals: int = 0
    archived_records: int = 0
    data_by_age: Dict[str, int] = {}
    compliance_score: float = 0.0
    recent_violations: List[Dict[str, Any]] = []
