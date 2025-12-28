"""FastAPI dependencies."""

from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.config import settings
from app.database import get_database
from app.utils.auth import decode_token

# Security scheme
security = HTTPBearer()


def get_db() -> AsyncIOMotorDatabase:
    """Get database dependency."""
    return get_database()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncIOMotorDatabase = Depends(get_db)
) -> dict:
    """Get current authenticated user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales inválidas"
    )
    session_expired_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Sesión expirada por inactividad"
    )
    
    # Decode token
    payload = decode_token(credentials.credentials)
    if payload is None:
        raise credentials_exception
    
    user_id: str = payload.get("sub")
    if user_id is None:
        raise credentials_exception
    
    # Check token expiration
    exp = payload.get("exp")
    if exp:
        exp_datetime = datetime.fromtimestamp(exp, tz=timezone.utc)
        if datetime.now(timezone.utc) > exp_datetime:
            raise session_expired_exception
    
    # Get user from database
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if user is None:
        raise credentials_exception
    
    # Check if user is active
    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cuenta desactivada"
        )
    
    # Check session timeout based on last activity
    last_activity = user.get("last_activity")
    if last_activity:
        try:
            if isinstance(last_activity, str):
                last_time = datetime.fromisoformat(last_activity.replace("Z", "+00:00"))
            else:
                last_time = last_activity.replace(tzinfo=timezone.utc) if last_activity.tzinfo is None else last_activity
            
            if datetime.now(timezone.utc) - last_time > timedelta(minutes=settings.SESSION_TIMEOUT_MINUTES):
                raise session_expired_exception
        except (ValueError, AttributeError):
            pass  # If we can't parse, continue
    
    # Update last activity timestamp
    await db.users.update_one(
        {"id": user_id},
        {"$set": {"last_activity": datetime.now(timezone.utc).isoformat()}}
    )
    
    return user


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        HTTPBearer(auto_error=False)
    ),
    db: AsyncIOMotorDatabase = Depends(get_db)
) -> Optional[dict]:
    """Get current user if authenticated, None otherwise."""
    if credentials is None:
        return None
    
    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None


def require_roles(*allowed_roles: str):
    """Dependency factory to require specific roles."""
    async def role_checker(current_user: dict = Depends(get_current_user)) -> dict:
        if current_user.get("role") not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Se requiere rol: {', '.join(allowed_roles)}"
            )
        return current_user
    return role_checker
