"""Script routes."""

from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException

from app.database import get_database
from app.utils.serializers import serialize_document
from app.core.dependencies import get_current_user
from app.models import Script, ScriptCreate, ScriptUpdate

script_router = APIRouter(prefix="/scripts", tags=["Scripts"])


@script_router.post("/", response_model=Script)
async def create_script(
    script_data: ScriptCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a new script."""
    if current_user["role"] not in ["admin", "facilitator"]:
        raise HTTPException(status_code=403, detail="Sin permisos")
    
    db = get_database()
    campaign = await db.campaigns.find_one({"id": script_data.campaign_id}, {"_id": 0})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaña no encontrada")
    
    # Get next version
    existing = await db.scripts.find(
        {"campaign_id": script_data.campaign_id}
    ).sort("version", -1).limit(1).to_list(1)
    next_version = (existing[0]["version"] + 1) if existing else 1
    
    script = Script(
        **script_data.model_dump(),
        version=next_version,
        tenant_id=campaign.get("tenant_id", "default"),
        created_by=current_user["id"]
    )
    await db.scripts.insert_one(serialize_document(script.model_dump()))
    return script


@script_router.get("/")
async def list_scripts(
    campaign_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """List scripts."""
    db = get_database()
    query = {}
    if campaign_id:
        query["campaign_id"] = campaign_id
    scripts = await db.scripts.find(query, {"_id": 0}).to_list(100)
    return scripts


@script_router.get("/{script_id}")
async def get_script(
    script_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get a specific script."""
    db = get_database()
    script = await db.scripts.find_one({"id": script_id}, {"_id": 0})
    if not script:
        raise HTTPException(status_code=404, detail="Script no encontrado")
    return script


@script_router.put("/{script_id}")
async def update_script(
    script_id: str,
    script_data: ScriptUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update a script."""
    if current_user["role"] not in ["admin", "facilitator"]:
        raise HTTPException(status_code=403, detail="Sin permisos")
    
    db = get_database()
    update_dict = {k: v for k, v in script_data.model_dump().items() if v is not None}
    update_dict["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.scripts.update_one({"id": script_id}, {"$set": update_dict})
    script = await db.scripts.find_one({"id": script_id}, {"_id": 0})
    return script


@script_router.delete("/{script_id}")
async def delete_script(
    script_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a script."""
    if current_user["role"] not in ["admin"]:
        raise HTTPException(status_code=403, detail="Sin permisos")
    
    db = get_database()
    await db.scripts.delete_one({"id": script_id})
    return {"message": "Script eliminado"}
