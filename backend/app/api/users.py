"""User management routes."""

from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr

from app.database import get_database
from app.utils.auth import get_password_hash
from app.utils.validators import generate_pseudonym, validate_password_strength
from app.utils.serializers import serialize_document
from app.utils.constants import AuditAction
from app.core.dependencies import get_current_user
from app.services import audit_service
from app.models import User, UserResponse

user_router = APIRouter(prefix="/users", tags=["Users"])


class UserCreateAdmin(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: str = "participant"
    department: Optional[str] = None
    position: Optional[str] = None
    tenant_id: Optional[str] = None
    is_active: bool = True


class UserUpdateAdmin(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    full_name: Optional[str] = None
    role: Optional[str] = None
    department: Optional[str] = None
    position: Optional[str] = None
    is_active: Optional[bool] = None


@user_router.get("/", response_model=List[UserResponse])
async def list_users(
    current_user: dict = Depends(get_current_user),
    role: Optional[str] = None
):
    """List all users (admin/facilitator/security_officer only)."""
    if current_user["role"] not in ["admin", "facilitator", "security_officer"]:
        raise HTTPException(status_code=403, detail="Sin permisos")
    
    db = get_database()
    query = {"role": role} if role else {}
    users = await db.users.find(query, {"_id": 0, "hashed_password": 0}).to_list(500)
    return [UserResponse(**{k: u.get(k) for k in UserResponse.model_fields}) for u in users]


@user_router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user_admin(
    user_data: UserCreateAdmin,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Create a new user (admin only)."""
    if current_user["role"] not in ["admin", "security_officer"]:
        raise HTTPException(
            status_code=403,
            detail="Solo admin o security_officer pueden crear usuarios"
        )
    
    db = get_database()
    
    existing = await db.users.find_one({"email": user_data.email})
    if existing:
        raise HTTPException(status_code=400, detail="El email ya está registrado")
    
    is_valid, msg = validate_password_strength(user_data.password)
    if not is_valid:
        raise HTTPException(status_code=400, detail=msg)
    
    user_dict = user_data.model_dump()
    password = user_dict.pop("password")
    
    user_obj = User(**user_dict)
    user_obj.tenant_id = user_data.tenant_id or current_user.get("tenant_id")
    user_obj.pseudonym_id = generate_pseudonym()
    
    doc = user_obj.model_dump()
    doc["hashed_password"] = get_password_hash(password)
    await db.users.insert_one(serialize_document(doc))
    
    await audit_service.log(
        user_id=current_user["id"],
        user_role=current_user["role"],
        action=AuditAction.SECURITY_ACTION,
        resource_type="user",
        resource_id=user_obj.id,
        details={
            "action": "create_user",
            "new_user_email": user_data.email,
            "new_user_role": user_data.role
        },
        tenant_id=current_user.get("tenant_id"),
        ip_address=request.client.host if request.client else None
    )
    
    return UserResponse(**{k: v for k, v in user_obj.model_dump().items() if k in UserResponse.model_fields})


@user_router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: str, current_user: dict = Depends(get_current_user)):
    """Get a specific user by ID."""
    if (current_user["role"] not in ["admin", "facilitator", "security_officer"] 
        and current_user["id"] != user_id):
        raise HTTPException(status_code=403, detail="Sin permisos")
    
    db = get_database()
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "hashed_password": 0})
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    return UserResponse(**{k: user.get(k) for k in UserResponse.model_fields})


@user_router.put("/{user_id}", response_model=UserResponse)
async def update_user_admin(
    user_id: str,
    user_data: UserUpdateAdmin,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Update a user (admin only)."""
    if current_user["role"] not in ["admin", "security_officer"]:
        raise HTTPException(
            status_code=403,
            detail="Solo admin o security_officer pueden modificar usuarios"
        )
    
    if user_id == current_user["id"]:
        raise HTTPException(
            status_code=400,
            detail="No puedes modificar tu propio usuario desde aquí"
        )
    
    db = get_database()
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    update_data = {k: v for k, v in user_data.model_dump().items() if v is not None}
    
    if "password" in update_data:
        is_valid, msg = validate_password_strength(update_data["password"])
        if not is_valid:
            raise HTTPException(status_code=400, detail=msg)
        update_data["hashed_password"] = get_password_hash(update_data.pop("password"))
    
    if "email" in update_data and update_data["email"] != user.get("email"):
        existing = await db.users.find_one({"email": update_data["email"]})
        if existing:
            raise HTTPException(status_code=400, detail="El email ya está registrado")
    
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.users.update_one({"id": user_id}, {"$set": update_data})
    
    await audit_service.log(
        user_id=current_user["id"],
        user_role=current_user["role"],
        action=AuditAction.SECURITY_ACTION,
        resource_type="user",
        resource_id=user_id,
        details={"action": "update_user", "updated_fields": list(update_data.keys())},
        tenant_id=current_user.get("tenant_id"),
        ip_address=request.client.host if request.client else None
    )
    
    updated_user = await db.users.find_one({"id": user_id}, {"_id": 0, "hashed_password": 0})
    return UserResponse(**{k: updated_user.get(k) for k in UserResponse.model_fields})


@user_router.delete("/{user_id}")
async def delete_user_admin(
    user_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Delete a user (admin only)."""
    if current_user["role"] not in ["admin"]:
        raise HTTPException(
            status_code=403,
            detail="Solo admin puede eliminar usuarios"
        )
    
    if user_id == current_user["id"]:
        raise HTTPException(
            status_code=400,
            detail="No puedes eliminar tu propio usuario"
        )
    
    db = get_database()
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    await db.users.delete_one({"id": user_id})
    
    await audit_service.log(
        user_id=current_user["id"],
        user_role=current_user["role"],
        action=AuditAction.DATA_DELETED,
        resource_type="user",
        resource_id=user_id,
        details={"action": "delete_user", "deleted_user_email": user.get("email")},
        tenant_id=current_user.get("tenant_id"),
        ip_address=request.client.host if request.client else None
    )
    
    return {"message": "Usuario eliminado exitosamente"}
