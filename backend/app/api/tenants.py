"""Tenant routes."""

from fastapi import APIRouter, Depends, HTTPException

from app.database import get_database
from app.utils.serializers import serialize_document
from app.core.dependencies import get_current_user
from app.models import Tenant, TenantCreate

tenant_router = APIRouter(prefix="/tenants", tags=["Tenants"])


@tenant_router.post("/", response_model=Tenant)
async def create_tenant(
    tenant_data: TenantCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a new tenant (admin only)."""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Solo admin")
    
    db = get_database()
    tenant = Tenant(**tenant_data.model_dump())
    await db.tenants.insert_one(serialize_document(tenant.model_dump()))
    return tenant


@tenant_router.get("/")
async def list_tenants(current_user: dict = Depends(get_current_user)):
    """List all tenants (admin only)."""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Solo admin")
    
    db = get_database()
    tenants = await db.tenants.find({}, {"_id": 0}).to_list(100)
    return tenants
