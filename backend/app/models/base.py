"""Base models and mixins."""

from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
import uuid


class TimestampMixin(BaseModel):
    """Mixin for models with timestamp fields."""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class BaseResponse(BaseModel):
    """Base response model."""
    success: bool = True
    message: Optional[str] = None


def generate_id() -> str:
    """Generate a new UUID string."""
    return str(uuid.uuid4())
