"""Consent and privacy routes."""

from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request

from app.database import get_database
from app.utils.serializers import serialize_document
from app.utils.constants import AuditAction
from app.core.dependencies import get_current_user
from app.services import audit_service, pii_vault_service
from app.models import Consent, ConsentCreate, ConsentPolicy, ConsentPolicyCreate

consent_router = APIRouter(prefix="/consent", tags=["Consent"])


@consent_router.post("/policy", response_model=ConsentPolicy)
async def create_consent_policy(
    policy_data: ConsentPolicyCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a consent policy."""
    if current_user["role"] not in ["admin", "facilitator"]:
        raise HTTPException(status_code=403, detail="Sin permisos")
    
    db = get_database()
    policy = ConsentPolicy(
        tenant_id=current_user.get("tenant_id") or "default",
        **policy_data.model_dump()
    )
    await db.consent_policies.insert_one(serialize_document(policy.model_dump()))
    
    if policy_data.campaign_id:
        await db.campaigns.update_one(
            {"id": policy_data.campaign_id},
            {"$set": {"consent_policy_id": policy.id}}
        )
    
    return policy


@consent_router.get("/policy/{campaign_id}")
async def get_consent_policy(campaign_id: str, current_user: dict = Depends(get_current_user)):
    """Get the consent policy for a campaign with full content."""
    db = get_database()
    campaign = await db.campaigns.find_one({"id": campaign_id}, {"_id": 0})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaña no encontrada")
    
    policy = None
    if campaign.get("consent_policy_id"):
        policy = await db.consent_policies.find_one(
            {"id": campaign["consent_policy_id"]},
            {"_id": 0}
        )
    
    if not policy:
        # Return default policy
        policy = {
            "id": "default",
            "version": "1.0",
            "purpose": campaign.get("objective", "Diagnóstico organizacional"),
            "data_collected": [
                "Transcripción de conversación",
                "Metadatos de sesión",
                "Insights extraídos"
            ],
            "data_not_used_for": [
                "Vigilancia individual",
                "Acciones punitivas o disciplinarias",
                "Evaluación de desempeño individual",
                "Identificación de personas específicas"
            ],
            "deliverables": [
                "Insights agregados y anonimizados",
                "Reportes sin información identificable",
                "Análisis de tendencias grupales"
            ],
            "risks_mitigations": "Sus respuestas serán pseudonimizadas antes de cualquier análisis.",
            "user_rights": [
                "Acceso a sus datos",
                "Rectificación de información incorrecta",
                "Eliminación de sus datos",
                "Revocación del consentimiento en cualquier momento"
            ],
            "retention_days": 365,
            "contact_email": "privacidad@digikawsay.com"
        }
    
    return {"campaign": campaign, "policy": policy}


@consent_router.get("/policy")
async def list_consent_policies(current_user: dict = Depends(get_current_user)):
    """List all consent policies."""
    if current_user["role"] not in ["admin", "facilitator"]:
        raise HTTPException(status_code=403, detail="Sin permisos")
    
    db = get_database()
    policies = await db.consent_policies.find({"is_active": True}, {"_id": 0}).to_list(100)
    return policies


@consent_router.post("/", response_model=Consent)
async def create_consent(
    consent_data: ConsentCreate,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Create a consent record."""
    db = get_database()
    campaign = await db.campaigns.find_one({"id": consent_data.campaign_id}, {"_id": 0})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaña no encontrada")
    
    existing = await db.consents.find_one({
        "user_id": current_user["id"],
        "campaign_id": consent_data.campaign_id,
        "revoked_at": None
    })
    if existing:
        raise HTTPException(status_code=400, detail="Ya existe consentimiento activo")
    
    policy_version = consent_data.policy_version or "1.0"
    policy_id = campaign.get("consent_policy_id")
    
    consent = Consent(
        user_id=current_user["id"],
        campaign_id=consent_data.campaign_id,
        tenant_id=campaign.get("tenant_id", "default"),
        accepted=consent_data.accepted,
        policy_id=policy_id,
        policy_version=policy_version,
        revocation_preference=consent_data.revocation_preference
    )
    await db.consents.insert_one(serialize_document(consent.model_dump()))
    
    await audit_service.log(
        user_id=current_user["id"],
        user_role=current_user["role"],
        action=AuditAction.CONSENT_GIVEN,
        resource_type="consent",
        resource_id=consent.id,
        campaign_id=consent_data.campaign_id,
        tenant_id=campaign.get("tenant_id"),
        details={"accepted": consent_data.accepted, "policy_version": policy_version},
        ip_address=request.client.host if request.client else None
    )
    
    if consent_data.accepted:
        await db.campaigns.update_one(
            {"id": consent_data.campaign_id},
            {"$inc": {"participant_count": 1}}
        )
    
    return consent


@consent_router.get("/my-consents")
async def get_my_consents(current_user: dict = Depends(get_current_user)):
    """Get current user's consents."""
    db = get_database()
    consents = await db.consents.find(
        {"user_id": current_user["id"], "revoked_at": None},
        {"_id": 0}
    ).to_list(100)
    return consents


@consent_router.post("/{consent_id}/revoke")
async def revoke_consent(
    consent_id: str,
    reason: Optional[str] = None,
    request: Request = None,
    current_user: dict = Depends(get_current_user)
):
    """Revoke a consent."""
    db = get_database()
    consent = await db.consents.find_one(
        {"id": consent_id, "user_id": current_user["id"]},
        {"_id": 0}
    )
    if not consent:
        raise HTTPException(status_code=404, detail="Consentimiento no encontrado")
    
    await db.consents.update_one(
        {"id": consent_id},
        {"$set": {
            "revoked_at": datetime.now(timezone.utc).isoformat(),
            "revocation_reason": reason
        }}
    )
    
    preference = consent.get("revocation_preference", "retain_aggregates")
    
    if preference == "delete_all":
        await db.transcripts.update_many(
            {"user_id": current_user["id"], "campaign_id": consent["campaign_id"]},
            {"$set": {"marked_for_deletion": True}}
        )
        tenant_id = consent.get("tenant_id", "default")
        pseudonym = await pii_vault_service.get_pseudonym(current_user["id"], tenant_id)
        if pseudonym:
            await pii_vault_service.delete_mapping(pseudonym, tenant_id)
    
    await audit_service.log(
        user_id=current_user["id"],
        user_role=current_user["role"],
        action=AuditAction.CONSENT_REVOKED,
        resource_type="consent",
        resource_id=consent_id,
        campaign_id=consent["campaign_id"],
        details={"reason": reason, "preference": preference}
    )
    
    await db.campaigns.update_one(
        {"id": consent["campaign_id"]},
        {"$inc": {"participant_count": -1}}
    )
    
    return {"message": "Consentimiento revocado", "data_handling": preference}
