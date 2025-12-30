"""Insight routes for RunaCultur."""

from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException

from app.database import get_database
from app.utils.serializers import serialize_document
from app.utils.constants import AuditAction
from app.core.dependencies import get_current_user
from app.services import audit_service, insight_extraction_service, suppression_service
from app.models import Insight, InsightCreate, InsightUpdate, ValidationResponse

insight_router = APIRouter(prefix="/insights", tags=["Insights"])


@insight_router.post("/", response_model=Insight)
async def create_insight(
    insight_data: InsightCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a new insight manually."""
    if current_user["role"] not in ["admin", "facilitator", "analyst"]:
        raise HTTPException(status_code=403, detail="Sin permisos")
    
    db = get_database()
    campaign = await db.campaigns.find_one({"id": insight_data.campaign_id}, {"_id": 0})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaña no encontrada")
    
    insight = Insight(
        **insight_data.model_dump(),
        tenant_id=campaign.get("tenant_id", "default"),
        created_by=current_user["id"],
        extracted_by="manual"
    )
    await db.insights.insert_one(serialize_document(insight.model_dump()))
    return insight


@insight_router.get("/")
async def list_insights(
    campaign_id: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """List insights with optional filters."""
    db = get_database()
    query = {}
    
    if campaign_id:
        query["campaign_id"] = campaign_id
    if category:
        query["category"] = category
    if status:
        query["status"] = status
    if current_user.get("tenant_id"):
        query["tenant_id"] = current_user["tenant_id"]
    
    # Apply suppression for non-admin users
    if current_user["role"] not in ["admin", "security_officer"]:
        query["is_suppressed"] = {"$ne": True}
    
    insights = await db.insights.find(query, {"_id": 0}).to_list(500)
    return insights


@insight_router.get("/campaign/{campaign_id}")
async def get_campaign_insights(
    campaign_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get all insights for a campaign."""
    db = get_database()
    query = {"campaign_id": campaign_id}
    
    # Apply suppression for non-admin users
    if current_user["role"] not in ["admin", "security_officer"]:
        query["is_suppressed"] = {"$ne": True}
    
    insights = await db.insights.find(query, {"_id": 0}).to_list(500)
    return insights


@insight_router.get("/{insight_id}")
async def get_insight(insight_id: str, current_user: dict = Depends(get_current_user)):
    """Get a specific insight."""
    db = get_database()
    insight = await db.insights.find_one({"id": insight_id}, {"_id": 0})
    if not insight:
        raise HTTPException(status_code=404, detail="Insight no encontrado")
    return insight


@insight_router.put("/{insight_id}")
async def update_insight(
    insight_id: str,
    insight_data: InsightUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update an insight."""
    if current_user["role"] not in ["admin", "facilitator", "analyst"]:
        raise HTTPException(status_code=403, detail="Sin permisos")
    
    db = get_database()
    update_dict = {k: v for k, v in insight_data.model_dump().items() if v is not None}
    update_dict["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.insights.update_one({"id": insight_id}, {"$set": update_dict})
    insight = await db.insights.find_one({"id": insight_id}, {"_id": 0})
    return insight


@insight_router.delete("/{insight_id}")
async def delete_insight(insight_id: str, current_user: dict = Depends(get_current_user)):
    """Delete an insight."""
    if current_user["role"] not in ["admin", "facilitator"]:
        raise HTTPException(status_code=403, detail="Sin permisos")
    
    db = get_database()
    await db.insights.delete_one({"id": insight_id})
    return {"message": "Insight eliminado"}


@insight_router.post("/{insight_id}/validate")
async def validate_insight(
    insight_id: str,
    validation: ValidationResponse,
    current_user: dict = Depends(get_current_user)
):
    """Validate an insight (member checking)."""
    db = get_database()
    insight = await db.insights.find_one({"id": insight_id}, {"_id": 0})
    if not insight:
        raise HTTPException(status_code=404, detail="Insight no encontrado")
    
    validation_record = {
        "user_id": current_user["id"],
        "user_role": current_user["role"],
        "validated": validation.validated,
        "comment": validation.comment,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    await db.insights.update_one(
        {"id": insight_id},
        {
            "$push": {"validations": validation_record},
            "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}
        }
    )
    
    await audit_service.log(
        user_id=current_user["id"],
        user_role=current_user["role"],
        action=AuditAction.DATA_VIEWED,
        resource_type="insight",
        resource_id=insight_id,
        details={"validated": validation.validated}
    )
    
    return {"message": "Validación registrada"}


@insight_router.post("/campaign/{campaign_id}/extract")
async def extract_insights(
    campaign_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Extract insights from all unprocessed transcripts in a campaign."""
    if current_user["role"] not in ["admin", "facilitator", "analyst"]:
        raise HTTPException(status_code=403, detail="Sin permisos")
    
    db = get_database()
    campaign = await db.campaigns.find_one({"id": campaign_id}, {"_id": 0})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaña no encontrada")
    
    tenant_id = campaign.get("tenant_id", "default")
    
    # Find unprocessed transcripts
    transcripts = await db.transcripts.find(
        {"campaign_id": campaign_id, "insights_extracted": {"$ne": True}},
        {"_id": 0}
    ).to_list(100)
    
    total_insights = 0
    for transcript in transcripts:
        insights = await insight_extraction_service.extract_insights_from_transcript(
            transcript_id=transcript["id"],
            campaign_id=campaign_id,
            tenant_id=tenant_id
        )
        total_insights += len(insights)
    
    # Run suppression check
    suppression_result = await suppression_service.check_and_suppress_insights(campaign_id)
    
    return {
        "message": f"Extracción completada",
        "transcripts_processed": len(transcripts),
        "insights_created": total_insights,
        "suppression": suppression_result
    }
