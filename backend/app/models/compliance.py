"""Compliance, Audit, Consent, and Privacy models."""

from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field
import uuid

from app.models.base import TimestampMixin


# --- Consent Policy ---
class ConsentPolicyCreate(BaseModel):
    campaign_id: Optional[str] = None
    purpose: str
    data_collected: List[str]  # ["transcript", "metadata", "insights"]
    data_not_used_for: List[str]  # ["individual_surveillance", "punitive_actions"]
    deliverables: List[str]  # ["aggregated_insights", "anonymized_reports"]
    risks_mitigations: str
    user_rights: List[str]  # ["access", "rectification", "deletion", "revocation"]
    retention_days: int = 365
    contact_email: str
    version: str = "1.0"


class ConsentPolicy(TimestampMixin):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    campaign_id: Optional[str] = None
    purpose: str
    data_collected: List[str] = []
    data_not_used_for: List[str] = []
    deliverables: List[str] = []
    risks_mitigations: str = ""
    user_rights: List[str] = []
    retention_days: int = 365
    contact_email: str = ""
    version: str = "1.0"
    is_active: bool = True


# --- Consent ---
class ConsentCreate(BaseModel):
    campaign_id: str
    accepted: bool
    policy_version: Optional[str] = None
    revocation_preference: str = "retain_aggregates"


class Consent(TimestampMixin):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    campaign_id: str
    tenant_id: str
    accepted: bool
    policy_id: Optional[str] = None
    policy_version: str = "1.0"
    consent_text_hash: Optional[str] = None
    revocation_preference: str = "retain_aggregates"
    revoked_at: Optional[datetime] = None
    revocation_reason: Optional[str] = None


# --- PII Vault ---
class PIIVaultEntry(TimestampMixin):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    pseudonym_id: str
    encrypted_identity: str
    identity_type: str = "user"
    campaign_id: Optional[str] = None
    expires_at: Optional[datetime] = None
    is_deleted: bool = False


# --- Audit Log ---
class AuditLog(TimestampMixin):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    correlation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: Optional[str] = None
    user_id: str
    user_role: str
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    campaign_id: Optional[str] = None
    details: Dict[str, Any] = {}
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    success: bool = True
    error_message: Optional[str] = None


# --- Reidentification ---
class ReidentificationReason:
    SAFETY_CONCERN = "safety_concern"
    LEGAL_COMPLIANCE = "legal_compliance"
    EXPLICIT_CONSENT = "explicit_consent"
    DATA_CORRECTION = "data_correction"


class ReidentificationRequestCreate(BaseModel):
    pseudonym_id: str
    reason_code: str
    justification: str
    campaign_id: Optional[str] = None


class ReidentificationRequest(TimestampMixin):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    pseudonym_id: str
    reason_code: str
    justification: str
    campaign_id: Optional[str] = None
    requested_by: str
    status: str = "pending"
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    review_notes: Optional[str] = None
    resolved_identity: Optional[str] = None
    expires_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc) + timedelta(hours=24)
    )
