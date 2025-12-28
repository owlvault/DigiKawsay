"""Chat session and message models."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field
import uuid

from app.models.base import TimestampMixin


# --- Session ---
class SessionCreate(BaseModel):
    campaign_id: str


class Session(TimestampMixin):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    campaign_id: str
    tenant_id: str
    status: str = "pending"
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    correlation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    current_step: int = 0
    script_id: Optional[str] = None


# --- Chat ---
class ChatRequest(BaseModel):
    session_id: str
    message: str


class ChatResponse(BaseModel):
    session_id: str
    message: str
    timestamp: datetime


# --- Transcript ---
class Transcript(TimestampMixin):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    campaign_id: str
    tenant_id: str
    user_id: str
    pseudonym_id: Optional[str] = None
    messages: List[Dict[str, Any]] = []
    is_pseudonymized: bool = False
    pseudonymized_at: Optional[datetime] = None
    insights_extracted: bool = False
