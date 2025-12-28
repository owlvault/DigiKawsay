"""Pydantic models for DigiKawsay."""

# Base models
from app.models.base import TimestampMixin, BaseResponse, generate_id

# Auth models
from app.models.auth import (
    Tenant, TenantCreate,
    User, UserCreate, UserLogin, UserResponse, UserCreateAdmin, UserUpdateAdmin,
    TokenResponse, LoginAttemptInfo,
)

# Campaign models
from app.models.campaign import (
    Campaign, CampaignCreate, CampaignUpdate,
    Script, ScriptCreate, ScriptUpdate, ScriptStep, ScriptVersion,
    Segment, SegmentCreate,
    Invite, InviteCreate, InviteBulk,
    CoverageStats,
)

# Chat models
from app.models.chat import (
    Session, SessionCreate,
    ChatRequest, ChatResponse,
    Transcript,
)

# Insight models
from app.models.insight import (
    Insight, InsightCreate, InsightUpdate,
    TaxonomyCategory, TaxonomyCategoryCreate,
    ValidationRequest, ValidationRequestCreate, ValidationResponse,
    InsightStats,
)

# Compliance models
from app.models.compliance import (
    ConsentPolicy, ConsentPolicyCreate,
    Consent, ConsentCreate,
    PIIVaultEntry,
    AuditLog,
    ReidentificationRequest, ReidentificationRequestCreate, ReidentificationReason,
)

# Network models
from app.models.network import (
    NetworkNode, NetworkEdge, NetworkSnapshot,
    NetworkMetrics, GraphResponse, GenerateNetworkRequest,
    NodeType, EdgeType,
)

# Initiative models
from app.models.initiative import (
    Initiative, InitiativeCreate, InitiativeUpdate, InitiativeComment,
    Ritual, RitualCreate, RitualUpdate, RitualOccurrence,
    InitiativeStats, InitiativeStatus, ScoringMethod, RitualType,
)

# Governance models
from app.models.governance import (
    DataPolicy, DataPolicyCreate, DataPolicyUpdate,
    ArchivedData,
    DualApprovalRequest, DualApprovalCreate,
    GovernanceMetrics,
    Roles, Permission, ROLE_PERMISSIONS,
)

# Observability models
from app.models.observability import (
    StructuredLog, Alert,
    SystemMetrics, BusinessMetrics, EndpointMetrics,
    ObservabilityDashboard, HealthCheck,
    LogLevel, AlertSeverity,
)

__all__ = [
    # Base
    "TimestampMixin", "BaseResponse", "generate_id",
    # Auth
    "Tenant", "TenantCreate",
    "User", "UserCreate", "UserLogin", "UserResponse", "UserCreateAdmin", "UserUpdateAdmin",
    "TokenResponse", "LoginAttemptInfo",
    # Campaign
    "Campaign", "CampaignCreate", "CampaignUpdate",
    "Script", "ScriptCreate", "ScriptUpdate", "ScriptStep", "ScriptVersion",
    "Segment", "SegmentCreate",
    "Invite", "InviteCreate", "InviteBulk",
    "CoverageStats",
    # Chat
    "Session", "SessionCreate",
    "ChatRequest", "ChatResponse",
    "Transcript",
    # Insight
    "Insight", "InsightCreate", "InsightUpdate",
    "TaxonomyCategory", "TaxonomyCategoryCreate",
    "ValidationRequest", "ValidationRequestCreate", "ValidationResponse",
    "InsightStats",
    # Compliance
    "ConsentPolicy", "ConsentPolicyCreate",
    "Consent", "ConsentCreate",
    "PIIVaultEntry",
    "AuditLog",
    "ReidentificationRequest", "ReidentificationRequestCreate", "ReidentificationReason",
    # Network
    "NetworkNode", "NetworkEdge", "NetworkSnapshot",
    "NetworkMetrics", "GraphResponse", "GenerateNetworkRequest",
    "NodeType", "EdgeType",
    # Initiative
    "Initiative", "InitiativeCreate", "InitiativeUpdate", "InitiativeComment",
    "Ritual", "RitualCreate", "RitualUpdate", "RitualOccurrence",
    "InitiativeStats", "InitiativeStatus", "ScoringMethod", "RitualType",
    # Governance
    "DataPolicy", "DataPolicyCreate", "DataPolicyUpdate",
    "ArchivedData",
    "DualApprovalRequest", "DualApprovalCreate",
    "GovernanceMetrics",
    "Roles", "Permission", "ROLE_PERMISSIONS",
    # Observability
    "StructuredLog", "Alert",
    "SystemMetrics", "BusinessMetrics", "EndpointMetrics",
    "ObservabilityDashboard", "HealthCheck",
    "LogLevel", "AlertSeverity",
]
