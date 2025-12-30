"""Initiative and Ritual routes for RunaFlow."""

from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException

from app.database import get_database
from app.utils.serializers import serialize_document
from app.core.dependencies import get_current_user
from app.services.initiative_service import initiative_service, ritual_service
from app.models import Initiative, InitiativeCreate, InitiativeUpdate, Ritual, RitualCreate

initiative_router = APIRouter(prefix="/initiatives", tags=["Initiatives"])
ritual_router = APIRouter(prefix="/rituals", tags=["Rituals"])


# ============== INITIATIVE ROUTES ==============

@initiative_router.post("/", response_model=Initiative)
async def create_initiative(
    initiative_data: InitiativeCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a new initiative."""
    if current_user["role"] not in ["admin", "facilitator", "analyst"]:
        raise HTTPException(status_code=403, detail="Sin permisos")
    
    db = get_database()
    campaign = await db.campaigns.find_one({"id": initiative_data.campaign_id}, {"_id": 0})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaña no encontrada")
    
    initiative = Initiative(
        **initiative_data.model_dump(),
        tenant_id=campaign.get("tenant_id", "default"),
        created_by=current_user["id"]
    )
    
    # Calculate priority score
    initiative.priority_score = initiative_service.calculate_score(initiative.model_dump())
    
    await db.initiatives.insert_one(serialize_document(initiative.model_dump()))
    return initiative


@initiative_router.get("/")
async def list_initiatives(
    campaign_id: Optional[str] = None,
    status: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """List initiatives."""
    db = get_database()
    query = {}
    if campaign_id:
        query["campaign_id"] = campaign_id
    if status:
        query["status"] = status
    
    initiatives = await db.initiatives.find(query, {"_id": 0}).sort("priority_score", -1).to_list(100)
    return initiatives


@initiative_router.get("/campaign/{campaign_id}")
async def get_campaign_initiatives(
    campaign_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get all initiatives for a campaign."""
    db = get_database()
    initiatives = await db.initiatives.find(
        {"campaign_id": campaign_id},
        {"_id": 0}
    ).sort("priority_score", -1).to_list(100)
    return initiatives


@initiative_router.get("/{initiative_id}")
async def get_initiative(
    initiative_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get a specific initiative."""
    db = get_database()
    initiative = await db.initiatives.find_one({"id": initiative_id}, {"_id": 0})
    if not initiative:
        raise HTTPException(status_code=404, detail="Iniciativa no encontrada")
    return initiative


@initiative_router.put("/{initiative_id}")
async def update_initiative(
    initiative_id: str,
    initiative_data: InitiativeUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update an initiative."""
    if current_user["role"] not in ["admin", "facilitator", "analyst"]:
        raise HTTPException(status_code=403, detail="Sin permisos")
    
    db = get_database()
    update_dict = {k: v for k, v in initiative_data.model_dump().items() if v is not None}
    update_dict["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    # Recalculate score if scoring fields changed
    if any(k in update_dict for k in ["impact_score", "confidence_score", "ease_score", "effort_score", "reach_score"]):
        current = await db.initiatives.find_one({"id": initiative_id}, {"_id": 0})
        if current:
            merged = {**current, **update_dict}
            update_dict["priority_score"] = initiative_service.calculate_score(merged)
    
    await db.initiatives.update_one({"id": initiative_id}, {"$set": update_dict})
    initiative = await db.initiatives.find_one({"id": initiative_id}, {"_id": 0})
    return initiative


@initiative_router.delete("/{initiative_id}")
async def delete_initiative(
    initiative_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete an initiative."""
    if current_user["role"] not in ["admin", "facilitator"]:
        raise HTTPException(status_code=403, detail="Sin permisos")
    
    db = get_database()
    await db.initiatives.delete_one({"id": initiative_id})
    return {"message": "Iniciativa eliminada"}


# ============== RITUAL ROUTES ==============

@ritual_router.post("/", response_model=Ritual)
async def create_ritual(
    ritual_data: RitualCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a new ritual."""
    if current_user["role"] not in ["admin", "facilitator"]:
        raise HTTPException(status_code=403, detail="Sin permisos")
    
    db = get_database()
    campaign = await db.campaigns.find_one({"id": ritual_data.campaign_id}, {"_id": 0})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaña no encontrada")
    
    ritual = Ritual(
        **ritual_data.model_dump(),
        tenant_id=campaign.get("tenant_id", "default"),
        created_by=current_user["id"]
    )
    
    # Calculate next occurrence
    next_occ = ritual_service.calculate_next_occurrence(ritual.model_dump())
    if next_occ:
        ritual.next_occurrence = next_occ
    
    await db.rituals.insert_one(serialize_document(ritual.model_dump()))
    return ritual


@ritual_router.get("/")
async def list_rituals(
    campaign_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """List rituals."""
    db = get_database()
    query = {}
    if campaign_id:
        query["campaign_id"] = campaign_id
    
    rituals = await db.rituals.find(query, {"_id": 0}).to_list(100)
    return rituals


@ritual_router.get("/{ritual_id}")
async def get_ritual(
    ritual_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get a specific ritual."""
    db = get_database()
    ritual = await db.rituals.find_one({"id": ritual_id}, {"_id": 0})
    if not ritual:
        raise HTTPException(status_code=404, detail="Ritual no encontrado")
    return ritual


@ritual_router.delete("/{ritual_id}")
async def delete_ritual(
    ritual_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a ritual."""
    if current_user["role"] not in ["admin", "facilitator"]:
        raise HTTPException(status_code=403, detail="Sin permisos")
    
    db = get_database()
    await db.rituals.delete_one({"id": ritual_id})
    return {"message": "Ritual eliminado"}
