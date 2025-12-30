"""API Routes for DigiKawsay."""

from fastapi import APIRouter

# Import all routers
from app.api.auth import auth_router
from app.api.users import user_router
from app.api.tenants import tenant_router
from app.api.campaigns import campaign_router
from app.api.scripts import script_router
from app.api.segments import segment_router, invite_router
from app.api.sessions import session_router, chat_router
from app.api.consent import consent_router
from app.api.insights import insight_router
from app.api.taxonomy import taxonomy_router
from app.api.audit import audit_router, privacy_router, transcript_router
from app.api.network import network_router
from app.api.initiatives import initiative_router, ritual_router
from app.api.governance import governance_router, reidentification_router
from app.api.observability import observability_router

# Create main API router
api_router = APIRouter(prefix="/api")

# Include all sub-routers
api_router.include_router(auth_router)
api_router.include_router(user_router)
api_router.include_router(tenant_router)
api_router.include_router(campaign_router)
api_router.include_router(script_router)
api_router.include_router(segment_router)
api_router.include_router(invite_router)
api_router.include_router(session_router)
api_router.include_router(chat_router)
api_router.include_router(consent_router)
api_router.include_router(insight_router)
api_router.include_router(taxonomy_router)
api_router.include_router(audit_router)
api_router.include_router(privacy_router)
api_router.include_router(transcript_router)
api_router.include_router(network_router)
api_router.include_router(initiative_router)
api_router.include_router(ritual_router)
api_router.include_router(governance_router)
api_router.include_router(reidentification_router)
api_router.include_router(observability_router)

__all__ = [
    "api_router",
    "auth_router",
    "user_router",
    "tenant_router",
    "campaign_router",
    "script_router",
    "segment_router",
    "invite_router",
    "session_router",
    "chat_router",
    "consent_router",
    "insight_router",
    "taxonomy_router",
    "audit_router",
    "privacy_router",
    "transcript_router",
    "network_router",
    "initiative_router",
    "ritual_router",
    "governance_router",
    "reidentification_router",
    "observability_router",
]
