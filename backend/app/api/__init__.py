"""API Routes for DigiKawsay."""

from fastapi import APIRouter

# Create main API router
api_router = APIRouter(prefix="/api")

# Import all sub-routers (will be populated as they are created)
# from app.api.auth import auth_router
# from app.api.users import user_router
# etc.

__all__ = ["api_router"]
