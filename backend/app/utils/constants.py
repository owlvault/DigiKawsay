"""Application constants and enums."""


class AuditAction:
    """Audit log action types."""
    VIEW_TRANSCRIPT = "view_transcript"
    VIEW_INSIGHT = "view_insight"
    EXPORT_DATA = "export_data"
    REIDENTIFICATION_REQUEST = "reidentification_request"
    REIDENTIFICATION_APPROVE = "reidentification_approve"
    REIDENTIFICATION_RESOLVE = "reidentification_resolve"
    CONSENT_GIVEN = "consent_given"
    CONSENT_REVOKED = "consent_revoked"
    DATA_DELETED = "data_deleted"
    LOGIN = "login"
    LOGOUT = "logout"
    SECURITY_ACTION = "security_action"
    ACCOUNT_UNLOCK = "account_unlock"


class SessionStatus:
    """Chat session status values."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class CampaignStatus:
    """Campaign status values."""
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class InsightStatus:
    """Insight validation status."""
    PENDING_REVIEW = "pending_review"
    VALIDATED = "validated"
    REJECTED = "rejected"
    NEEDS_REVISION = "needs_revision"


class InitiativeStatus:
    """Initiative status values."""
    PROPOSED = "proposed"
    APPROVED = "approved"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class UserRole:
    """User role values."""
    ADMIN = "admin"
    FACILITATOR = "facilitator"
    ANALYST = "analyst"
    PARTICIPANT = "participant"
    SECURITY_OFFICER = "security_officer"
    PRIVACY_OFFICER = "privacy_officer"
    DATA_STEWARD = "data_steward"
    SPONSOR = "sponsor"


class NetworkEdgeType:
    """Network edge types for SNA."""
    HABLA_DE = "habla_de"
    COMPARTE_TEMA = "comparte_tema"
    SIMILAR = "similar"
    COOCCURRENCE = "cooccurrence"


class NetworkNodeType:
    """Network node types for SNA."""
    PARTICIPANT = "participant"
    THEME = "theme"
    SYMBOL = "symbol"
    TENSION = "tension"
    OPPORTUNITY = "opportunity"
    CATEGORY = "category"
