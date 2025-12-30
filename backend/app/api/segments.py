"""Segment and Invite routes."""

from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.database import get_database
from app.utils.serializers import serialize_document
from app.utils.validators import generate_invite_code
from app.core.dependencies import get_current_user
from app.models import Segment, SegmentCreate, Invite, InviteCreate

segment_router = APIRouter(prefix="/segments", tags=["Segments"])
invite_router = APIRouter(prefix="/invites", tags=["Invites"])


# ============== SEGMENT ROUTES ==============

@segment_router.post("/", response_model=Segment)
async def create_segment(
    segment_data: SegmentCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a segment."""
    if current_user["role"] not in ["admin", "facilitator"]:
        raise HTTPException(status_code=403, detail="Sin permisos")
    
    db = get_database()
    campaign = await db.campaigns.find_one({"id": segment_data.campaign_id}, {"_id": 0})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaña no encontrada")
    
    segment = Segment(
        **segment_data.model_dump(),
        tenant_id=campaign.get("tenant_id", "default")
    )
    await db.segments.insert_one(serialize_document(segment.model_dump()))
    return segment


@segment_router.get("/")
async def list_segments(
    campaign_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """List segments."""
    db = get_database()
    query = {}
    if campaign_id:
        query["campaign_id"] = campaign_id
    
    segments = await db.segments.find(query, {"_id": 0}).to_list(100)
    return segments


@segment_router.get("/{segment_id}")
async def get_segment(
    segment_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get a specific segment."""
    db = get_database()
    segment = await db.segments.find_one({"id": segment_id}, {"_id": 0})
    if not segment:
        raise HTTPException(status_code=404, detail="Segmento no encontrado")
    return segment


@segment_router.delete("/{segment_id}")
async def delete_segment(
    segment_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a segment."""
    if current_user["role"] not in ["admin", "facilitator"]:
        raise HTTPException(status_code=403, detail="Sin permisos")
    
    db = get_database()
    await db.segments.delete_one({"id": segment_id})
    return {"message": "Segmento eliminado"}


# ============== INVITE ROUTES ==============

@invite_router.post("/", response_model=Invite)
async def create_invite(
    invite_data: InviteCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create an invite."""
    if current_user["role"] not in ["admin", "facilitator"]:
        raise HTTPException(status_code=403, detail="Sin permisos")
    
    db = get_database()
    campaign = await db.campaigns.find_one({"id": invite_data.campaign_id}, {"_id": 0})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaña no encontrada")
    
    invite = Invite(
        **invite_data.model_dump(),
        tenant_id=campaign.get("tenant_id", "default"),
        invite_code=generate_invite_code(),
        created_by=current_user["id"]
    )
    await db.invites.insert_one(serialize_document(invite.model_dump()))
    return invite


class BulkInviteRequest(BaseModel):
    campaign_id: str
    segment_id: Optional[str] = None
    emails: List[str]


@invite_router.post("/bulk")
async def create_bulk_invites(
    bulk_data: BulkInviteRequest,
    current_user: dict = Depends(get_current_user)
):
    """Create multiple invites."""
    if current_user["role"] not in ["admin", "facilitator"]:
        raise HTTPException(status_code=403, detail="Sin permisos")
    
    db = get_database()
    campaign = await db.campaigns.find_one({"id": bulk_data.campaign_id}, {"_id": 0})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaña no encontrada")
    
    created = 0
    for email in bulk_data.emails:
        # Check if invite already exists
        existing = await db.invites.find_one({
            "campaign_id": bulk_data.campaign_id,
            "email": email
        })
        if not existing:
            invite = Invite(
                campaign_id=bulk_data.campaign_id,
                segment_id=bulk_data.segment_id,
                email=email,
                tenant_id=campaign.get("tenant_id", "default"),
                invite_code=generate_invite_code(),
                created_by=current_user["id"]
            )
            await db.invites.insert_one(serialize_document(invite.model_dump()))
            created += 1
    
    return {"message": f"Creadas {created} invitaciones", "created": created}


@invite_router.get("/campaign/{campaign_id}")
async def list_campaign_invites(
    campaign_id: str,
    current_user: dict = Depends(get_current_user)
):
    """List invites for a campaign."""
    if current_user["role"] not in ["admin", "facilitator"]:
        raise HTTPException(status_code=403, detail="Sin permisos")
    
    db = get_database()
    invites = await db.invites.find({"campaign_id": campaign_id}, {"_id": 0}).to_list(500)
    return invites


@invite_router.get("/validate/{invite_code}")
async def validate_invite(invite_code: str):
    """Validate an invite code (public endpoint)."""
    db = get_database()
    invite = await db.invites.find_one({"invite_code": invite_code}, {"_id": 0})
    if not invite:
        raise HTTPException(status_code=404, detail="Invitación no encontrada")
    if invite.get("used"):
        raise HTTPException(status_code=400, detail="Invitación ya utilizada")
    
    # Get campaign info
    campaign = await db.campaigns.find_one({"id": invite["campaign_id"]}, {"_id": 0})
    
    return {
        "valid": True,
        "campaign_id": invite["campaign_id"],
        "campaign_name": campaign.get("name") if campaign else None,
        "segment_id": invite.get("segment_id")
    }


@invite_router.post("/use/{invite_code}")
async def use_invite(
    invite_code: str,
    current_user: dict = Depends(get_current_user)
):
    """Mark an invite as used."""
    db = get_database()
    result = await db.invites.update_one(
        {"invite_code": invite_code, "used": {"$ne": True}},
        {"$set": {
            "used": True,
            "used_at": datetime.now(timezone.utc).isoformat(),
            "used_by": current_user["id"]
        }}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=400, detail="Invitación inválida o ya utilizada")
    return {"message": "Invitación utilizada"}
