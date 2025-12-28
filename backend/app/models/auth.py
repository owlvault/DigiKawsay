"""Authentication and user models."""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field, EmailStr
import uuid

from app.models.base import TimestampMixin


# --- Tenant ---
class TenantCreate(BaseModel):
    name: str
    description: Optional[str] = None
    logo_url: Optional[str] = None


class Tenant(TimestampMixin):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None
    logo_url: Optional[str] = None
    is_active: bool = True


# --- User ---
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: str = "participant"
    tenant_id: Optional[str] = None
    department: Optional[str] = None
    position: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class User(TimestampMixin):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: str
    full_name: str
    role: str
    tenant_id: Optional[str] = None
    department: Optional[str] = None
    position: Optional[str] = None
    is_active: bool = True
    pseudonym_id: Optional[str] = None


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    tenant_id: Optional[str] = None
    department: Optional[str] = None
    position: Optional[str] = None
    is_active: bool


class UserCreateAdmin(BaseModel):
    """Admin user creation model."""
    email: EmailStr
    password: str
    full_name: str
    role: str = "participant"
    department: Optional[str] = None
    position: Optional[str] = None
    tenant_id: Optional[str] = None
    is_active: bool = True


class UserUpdateAdmin(BaseModel):
    """Admin user update model."""
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    full_name: Optional[str] = None
    role: Optional[str] = None
    department: Optional[str] = None
    position: Optional[str] = None
    is_active: Optional[bool] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class LoginAttemptInfo(BaseModel):
    """Login attempt tracking."""
    email: str
    attempts: int
    last_attempt: Optional[str] = None
    is_locked: bool
    lockout_remaining_minutes: Optional[int] = None
