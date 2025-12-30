"""Authentication routes."""

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from app.config import settings
from app.database import get_database
from app.utils.auth import create_access_token, get_password_hash, verify_password
from app.utils.validators import generate_pseudonym
from app.utils.serializers import serialize_document
from app.utils.constants import AuditAction
from app.core.dependencies import get_current_user
from app.services import audit_service
from app.services.observability_service import structured_logger
from app.models import (
    User, UserCreate, UserLogin, UserResponse, TokenResponse, LoginAttemptInfo
)

auth_router = APIRouter(prefix="/auth", tags=["Authentication"])

# Security configuration
SESSION_TIMEOUT_MINUTES = settings.SESSION_TIMEOUT_MINUTES
PASSWORD_MIN_LENGTH = settings.PASSWORD_MIN_LENGTH
MAX_LOGIN_ATTEMPTS = settings.MAX_LOGIN_ATTEMPTS
LOGIN_LOCKOUT_MINUTES = settings.LOGIN_LOCKOUT_MINUTES

# In-memory failed login attempts (will be migrated to DB)
failed_login_attempts: Dict[str, Dict] = {}


class PIISanitizer:
    """Simple PII sanitizer for logging."""
    @staticmethod
    def sanitize(text: str) -> str:
        if '@' in text:
            parts = text.split('@')
            return f"{parts[0][:2]}***@{parts[1]}"
        return text[:2] + "***" if len(text) > 2 else "***"


def check_login_lockout(email: str) -> bool:
    """Check if account is locked due to failed attempts."""
    if email not in failed_login_attempts:
        return False
    attempts = failed_login_attempts[email]
    if attempts["count"] < MAX_LOGIN_ATTEMPTS:
        return False
    # Check if lockout period has passed
    if attempts["last_attempt"]:
        lockout_until = attempts["last_attempt"] + timedelta(minutes=LOGIN_LOCKOUT_MINUTES)
        if datetime.now(timezone.utc) > lockout_until:
            # Reset after lockout period
            del failed_login_attempts[email]
            return False
    return True


async def check_login_lockout_db(email: str) -> bool:
    """Check login lockout from database."""
    db = get_database()
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=LOGIN_LOCKOUT_MINUTES)
    count = await db.login_attempts.count_documents({
        "email": email,
        "success": False,
        "timestamp": {"$gte": cutoff.isoformat()}
    })
    return count >= MAX_LOGIN_ATTEMPTS


async def record_failed_login_db(email: str, ip_address: str = None):
    """Record failed login attempt in database."""
    db = get_database()
    await db.login_attempts.insert_one({
        "email": email,
        "ip_address": ip_address,
        "success": False,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    # Also track in memory
    if email not in failed_login_attempts:
        failed_login_attempts[email] = {"count": 0, "last_attempt": None}
    failed_login_attempts[email]["count"] += 1
    failed_login_attempts[email]["last_attempt"] = datetime.now(timezone.utc)


async def record_successful_login_db(email: str, ip_address: str = None):
    """Record successful login and clear failed attempts."""
    db = get_database()
    await db.login_attempts.insert_one({
        "email": email,
        "ip_address": ip_address,
        "success": True,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    # Clear in-memory attempts on success
    if email in failed_login_attempts:
        del failed_login_attempts[email]


@auth_router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate):
    """Register a new user."""
    db = get_database()
    existing = await db.users.find_one({"email": user_data.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email ya registrado")
    
    user_dict = user_data.model_dump()
    password = user_dict.pop("password")
    user_obj = User(**user_dict)
    user_obj.pseudonym_id = generate_pseudonym()
    
    doc = user_obj.model_dump()
    doc["hashed_password"] = get_password_hash(password)
    await db.users.insert_one(serialize_document(doc))
    
    access_token = create_access_token(data={"sub": user_obj.id})
    return TokenResponse(
        access_token=access_token,
        user=UserResponse(**{k: v for k, v in user_obj.model_dump().items() if k in UserResponse.model_fields})
    )


@auth_router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin, request: Request):
    """Login with email and password."""
    db = get_database()
    ip_address = request.client.host if request.client else None
    
    # Check for lockout
    if check_login_lockout(credentials.email) or await check_login_lockout_db(credentials.email):
        structured_logger.warning(
            f"Login attempt blocked - account locked",
            email=PIISanitizer.sanitize(credentials.email),
            ip=ip_address
        )
        raise HTTPException(
            status_code=429,
            detail=f"Cuenta bloqueada por {LOGIN_LOCKOUT_MINUTES} minutos debido a múltiples intentos fallidos"
        )
    
    user = await db.users.find_one({"email": credentials.email}, {"_id": 0})
    if not user or not verify_password(credentials.password, user.get("hashed_password", "")):
        await record_failed_login_db(credentials.email, ip_address)
        structured_logger.warning(
            f"Failed login attempt",
            email=PIISanitizer.sanitize(credentials.email),
            ip=ip_address
        )
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
    
    if not user.get("is_active", True):
        raise HTTPException(status_code=403, detail="Cuenta desactivada")
    
    await record_successful_login_db(credentials.email, ip_address)
    
    await audit_service.log(
        user_id=user["id"],
        user_role=user["role"],
        action=AuditAction.LOGIN,
        resource_type="session",
        tenant_id=user.get("tenant_id"),
        ip_address=ip_address
    )
    
    await db.users.update_one(
        {"id": user["id"]},
        {"$set": {
            "last_login": datetime.now(timezone.utc).isoformat(),
            "last_activity": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    access_token = create_access_token(data={"sub": user["id"]})
    return TokenResponse(
        access_token=access_token,
        user=UserResponse(**{k: user.get(k) for k in UserResponse.model_fields})
    )


@auth_router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    """Get current authenticated user."""
    return UserResponse(**{k: current_user.get(k) for k in UserResponse.model_fields})


@auth_router.get("/security/locked-accounts", response_model=List[LoginAttemptInfo])
async def get_locked_accounts(current_user: dict = Depends(get_current_user)):
    """Get list of accounts with failed login attempts (admin/security_officer only)."""
    if current_user["role"] not in ["admin", "security_officer"]:
        raise HTTPException(
            status_code=403,
            detail="Solo admin o security_officer pueden ver cuentas bloqueadas"
        )
    
    locked_accounts = []
    for email, attempts in failed_login_attempts.items():
        is_locked = attempts["count"] >= MAX_LOGIN_ATTEMPTS
        lockout_remaining = None
        
        if is_locked and attempts["last_attempt"]:
            lockout_until = attempts["last_attempt"] + timedelta(minutes=LOGIN_LOCKOUT_MINUTES)
            remaining = lockout_until - datetime.now(timezone.utc)
            if remaining.total_seconds() > 0:
                lockout_remaining = int(remaining.total_seconds() / 60)
            else:
                is_locked = False
        
        locked_accounts.append(LoginAttemptInfo(
            email=email,
            attempts=attempts["count"],
            last_attempt=attempts["last_attempt"].isoformat() if attempts["last_attempt"] else None,
            is_locked=is_locked,
            lockout_remaining_minutes=lockout_remaining
        ))
    
    return locked_accounts


@auth_router.post("/security/unlock-account/{email}")
async def unlock_account(
    email: str,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Unlock a locked account (admin/security_officer only)."""
    if current_user["role"] not in ["admin", "security_officer"]:
        raise HTTPException(
            status_code=403,
            detail="Solo admin o security_officer pueden desbloquear cuentas"
        )
    
    if email not in failed_login_attempts:
        raise HTTPException(
            status_code=404,
            detail="No hay intentos fallidos registrados para este email"
        )
    
    del failed_login_attempts[email]
    
    await audit_service.log(
        user_id=current_user["id"],
        user_role=current_user["role"],
        action=AuditAction.ACCOUNT_UNLOCK,
        resource_type="security",
        resource_id=email,
        details={"action": "unlock_account", "unlocked_email": email},
        tenant_id=current_user.get("tenant_id"),
        ip_address=request.client.host if request.client else None
    )
    
    structured_logger.info(
        f"Account unlocked by admin",
        unlocked_email=PIISanitizer.sanitize(email),
        admin_id=current_user["id"]
    )
    
    return {"message": f"Cuenta {email} desbloqueada exitosamente"}


@auth_router.get("/security/config")
async def get_security_config(current_user: dict = Depends(get_current_user)):
    """Get current security configuration (admin/security_officer only)."""
    if current_user["role"] not in ["admin", "security_officer"]:
        raise HTTPException(
            status_code=403,
            detail="Solo admin o security_officer pueden ver configuración de seguridad"
        )
    
    return {
        "session_timeout_minutes": SESSION_TIMEOUT_MINUTES,
        "password_min_length": PASSWORD_MIN_LENGTH,
        "max_login_attempts": MAX_LOGIN_ATTEMPTS,
        "login_lockout_minutes": LOGIN_LOCKOUT_MINUTES,
        "rate_limit_per_minute": 30,
        "login_rate_limit_per_minute": 10
    }
