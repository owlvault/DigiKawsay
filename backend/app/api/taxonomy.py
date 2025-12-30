"""Taxonomy routes."""

from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException

from app.database import get_database
from app.utils.serializers import serialize_document
from app.core.dependencies import get_current_user
from app.models import TaxonomyCategory, TaxonomyCategoryCreate

taxonomy_router = APIRouter(prefix="/taxonomy", tags=["Taxonomy"])


@taxonomy_router.post("/")
async def create_taxonomy_category(
    category_data: TaxonomyCategoryCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a taxonomy category."""
    if current_user["role"] not in ["admin", "facilitator"]:
        raise HTTPException(status_code=403, detail="Sin permisos")
    
    db = get_database()
    category = TaxonomyCategory(
        **category_data.model_dump(),
        tenant_id=current_user.get("tenant_id", "default")
    )
    await db.taxonomy_categories.insert_one(serialize_document(category.model_dump()))
    return category


@taxonomy_router.get("/")
async def list_taxonomy_categories(
    type: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """List taxonomy categories."""
    db = get_database()
    query = {"is_active": True}
    if type:
        query["type"] = type
    if current_user.get("tenant_id"):
        query["tenant_id"] = current_user["tenant_id"]
    
    categories = await db.taxonomy_categories.find(query, {"_id": 0}).to_list(100)
    return categories


@taxonomy_router.get("/{category_id}")
async def get_taxonomy_category(
    category_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get a specific taxonomy category."""
    db = get_database()
    category = await db.taxonomy_categories.find_one({"id": category_id}, {"_id": 0})
    if not category:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    return category


@taxonomy_router.put("/{category_id}")
async def update_taxonomy_category(
    category_id: str,
    category_data: TaxonomyCategoryCreate,
    current_user: dict = Depends(get_current_user)
):
    """Update a taxonomy category."""
    if current_user["role"] not in ["admin", "facilitator"]:
        raise HTTPException(status_code=403, detail="Sin permisos")
    
    db = get_database()
    update_dict = category_data.model_dump()
    update_dict["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.taxonomy_categories.update_one({"id": category_id}, {"$set": update_dict})
    category = await db.taxonomy_categories.find_one({"id": category_id}, {"_id": 0})
    return category


@taxonomy_router.delete("/{category_id}")
async def delete_taxonomy_category(
    category_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete (deactivate) a taxonomy category."""
    if current_user["role"] not in ["admin"]:
        raise HTTPException(status_code=403, detail="Sin permisos")
    
    db = get_database()
    await db.taxonomy_categories.update_one(
        {"id": category_id},
        {"$set": {"is_active": False, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    return {"message": "Categoría desactivada"}
