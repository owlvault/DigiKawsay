"""Campaign routes."""

from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException

from app.database import get_database
from app.utils.serializers import serialize_document
from app.core.dependencies import get_current_user
from app.models import Campaign, CampaignCreate, CampaignUpdate, CoverageStats

campaign_router = APIRouter(prefix="/campaigns", tags=["Campaigns"])


@campaign_router.post("/", response_model=Campaign)
async def create_campaign(
    campaign_data: CampaignCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a new campaign."""
    db = get_database()
    campaign = Campaign(**campaign_data.model_dump(), created_by=current_user["id"], tenant_id=current_user.get("tenant_id", "default"))
    await db.campaigns.insert_one(serialize_document(campaign.model_dump()))
    return campaign


@campaign_router.get("/")
async def list_campaigns(current_user: dict = Depends(get_current_user)):
    """List campaigns for current user's tenant."""
    db = get_database()
    query = {}
    if current_user.get("tenant_id"):
        query["tenant_id"] = current_user["tenant_id"]
    campaigns = await db.campaigns.find(query, {"_id": 0}).to_list(100)
    return campaigns


@campaign_router.get("/{campaign_id}")
async def get_campaign(campaign_id: str, current_user: dict = Depends(get_current_user)):
    """Get a specific campaign."""
    db = get_database()
    campaign = await db.campaigns.find_one({"id": campaign_id}, {"_id": 0})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaña no encontrada")
    return campaign


@campaign_router.put("/{campaign_id}")
async def update_campaign(
    campaign_id: str,
    campaign_data: CampaignUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update a campaign."""
    db = get_database()
    update_dict = {k: v for k, v in campaign_data.model_dump().items() if v is not None}
    update_dict["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.campaigns.update_one({"id": campaign_id}, {"$set": update_dict})
    campaign = await db.campaigns.find_one({"id": campaign_id}, {"_id": 0})
    return campaign


@campaign_router.patch("/{campaign_id}/status")
async def update_campaign_status(
    campaign_id: str,
    status: str,
    current_user: dict = Depends(get_current_user)
):
    """Update campaign status."""
    db = get_database()
    await db.campaigns.update_one(
        {"id": campaign_id},
        {"$set": {"status": status, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    return {"message": "Estado actualizado"}


@campaign_router.get("/{campaign_id}/coverage")
async def get_campaign_coverage(
    campaign_id: str,
    current_user: dict = Depends(get_current_user)
) -> CoverageStats:
    """Get coverage statistics for a campaign."""
    db = get_database()
    
    # Get campaign
    campaign = await db.campaigns.find_one({"id": campaign_id}, {"_id": 0})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaña no encontrada")
    
    # Count invites
    total_invited = await db.invites.count_documents({"campaign_id": campaign_id})
    
    # Count consents
    total_consented = await db.consents.count_documents({
        "campaign_id": campaign_id,
        "accepted": True,
        "revoked_at": None
    })
    
    # Count sessions
    total_sessions = await db.sessions.count_documents({"campaign_id": campaign_id})
    completed_sessions = await db.sessions.count_documents({
        "campaign_id": campaign_id,
        "status": "completed"
    })
    
    # Calculate rates
    participation_rate = (total_consented / total_invited * 100) if total_invited > 0 else 0
    completion_rate = (completed_sessions / total_sessions * 100) if total_sessions > 0 else 0
    
    # Get segment stats
    segments = await db.segments.find({"campaign_id": campaign_id}, {"_id": 0}).to_list(50)
    segment_stats = []
    for seg in segments:
        seg_invites = await db.invites.count_documents({
            "campaign_id": campaign_id,
            "segment_id": seg.get("id")
        })
        seg_sessions = await db.sessions.count_documents({
            "campaign_id": campaign_id,
            "segment_id": seg.get("id")
        })
        segment_stats.append({
            "segment_id": seg.get("id"),
            "name": seg.get("name"),
            "invited": seg_invites,
            "sessions": seg_sessions
        })
    
    return CoverageStats(
        campaign_id=campaign_id,
        total_invited=total_invited,
        total_consented=total_consented,
        total_sessions=total_sessions,
        completed_sessions=completed_sessions,
        participation_rate=round(participation_rate, 2),
        completion_rate=round(completion_rate, 2),
        segments=segment_stats
    )
