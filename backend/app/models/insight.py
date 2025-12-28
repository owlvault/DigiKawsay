"""Insight, Taxonomy, and Validation models."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field
import uuid

from app.models.base import TimestampMixin


# --- Taxonomy ---
class TaxonomyCategoryCreate(BaseModel):
    name: str
    type: str
    description: Optional[str] = None
    color: Optional[str] = None
    parent_id: Optional[str] = None


class TaxonomyCategory(TimestampMixin):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    name: str
    type: str
    description: Optional[str] = None
    color: Optional[str] = None
    parent_id: Optional[str] = None
    is_active: bool = True
    usage_count: int = 0


# --- Insight ---
class InsightCreate(BaseModel):
    campaign_id: str
    content: str
    type: str = "theme"
    category_id: Optional[str] = None
    source_session_id: Optional[str] = None
    source_quote: Optional[str] = None
    sentiment: Optional[str] = None
    importance: int = 5


class InsightUpdate(BaseModel):
    content: Optional[str] = None
    type: Optional[str] = None
    category_id: Optional[str] = None
    status: Optional[str] = None
    sentiment: Optional[str] = None
    importance: Optional[int] = None


class Insight(TimestampMixin):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    campaign_id: str
    content: str
    type: str = "theme"
    category_id: Optional[str] = None
    source_session_id: Optional[str] = None
    source_quote: Optional[str] = None
    sentiment: Optional[str] = None
    importance: int = 5
    status: str = "draft"
    extracted_by: str = "ai"
    validated_by: Optional[str] = None
    validated_at: Optional[datetime] = None
    occurrence_count: int = 1
    related_insights: List[str] = []
    is_suppressed: bool = False


# --- Validation ---
class ValidationRequestCreate(BaseModel):
    insight_id: str
    message: Optional[str] = None


class ValidationRequest(TimestampMixin):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    insight_id: str
    campaign_id: str
    tenant_id: str
    user_id: str
    status: str = "pending"
    response: Optional[str] = None
    responded_at: Optional[datetime] = None


class ValidationResponse(BaseModel):
    validated: bool
    comment: Optional[str] = None


# --- Stats ---
class InsightStats(BaseModel):
    campaign_id: str
    total_insights: int = 0
    by_type: Dict[str, int] = {}
    by_status: Dict[str, int] = {}
    by_sentiment: Dict[str, int] = {}
    top_categories: List[Dict[str, Any]] = []
    suppressed_count: int = 0
