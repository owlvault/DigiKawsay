"""Initiative and Ritual models for RunaFlow."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field
import uuid

from app.models.base import TimestampMixin


# --- Status and Method Types ---
class InitiativeStatus:
    BACKLOG = "backlog"
    EVALUATING = "en_evaluacion"
    APPROVED = "aprobada"
    IN_PROGRESS = "en_progreso"
    COMPLETED = "completada"
    CANCELLED = "cancelada"


class ScoringMethod:
    ICE = "ice"
    RICE = "rice"


class RitualType:
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"


# --- Initiative ---
class InitiativeCreate(BaseModel):
    title: str
    description: Optional[str] = None
    campaign_id: str
    source_insight_ids: List[str] = []
    source_community_id: Optional[int] = None
    assigned_to: Optional[str] = None
    scoring_method: str = "ice"
    impact_score: int = 5
    confidence_score: int = 5
    ease_score: int = 5
    reach_score: int = 100
    effort_score: int = 5
    tags: List[str] = []
    due_date: Optional[datetime] = None


class InitiativeUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    assigned_to: Optional[str] = None
    scoring_method: Optional[str] = None
    impact_score: Optional[int] = None
    confidence_score: Optional[int] = None
    ease_score: Optional[int] = None
    reach_score: Optional[int] = None
    effort_score: Optional[int] = None
    tags: Optional[List[str]] = None
    due_date: Optional[datetime] = None
    progress_percentage: Optional[int] = None


class Initiative(TimestampMixin):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    campaign_id: str
    title: str
    description: Optional[str] = None
    status: str = "backlog"
    source_insight_ids: List[str] = []
    source_community_id: Optional[int] = None
    assigned_to: Optional[str] = None
    assigned_to_name: Optional[str] = None
    created_by: str
    scoring_method: str = "ice"
    impact_score: int = 5
    confidence_score: int = 5
    ease_score: int = 5
    reach_score: int = 100
    effort_score: int = 5
    final_score: float = 0.0
    tags: List[str] = []
    due_date: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress_percentage: int = 0
    comments_count: int = 0


class InitiativeComment(TimestampMixin):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    initiative_id: str
    user_id: str
    user_name: str
    content: str


# --- Ritual ---
class RitualCreate(BaseModel):
    name: str
    description: Optional[str] = None
    ritual_type: str
    campaign_id: Optional[str] = None
    day_of_week: Optional[int] = None
    day_of_month: Optional[int] = None
    time_of_day: Optional[str] = None
    duration_minutes: int = 30
    participants: List[str] = []
    agenda_template: Optional[str] = None
    is_active: bool = True


class RitualUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    ritual_type: Optional[str] = None
    day_of_week: Optional[int] = None
    day_of_month: Optional[int] = None
    time_of_day: Optional[str] = None
    duration_minutes: Optional[int] = None
    participants: Optional[List[str]] = None
    agenda_template: Optional[str] = None
    is_active: Optional[bool] = None


class Ritual(TimestampMixin):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    campaign_id: Optional[str] = None
    name: str
    description: Optional[str] = None
    ritual_type: str
    day_of_week: Optional[int] = None
    day_of_month: Optional[int] = None
    time_of_day: Optional[str] = None
    duration_minutes: int = 30
    participants: List[str] = []
    agenda_template: Optional[str] = None
    is_active: bool = True
    created_by: str
    last_occurrence: Optional[datetime] = None
    next_occurrence: Optional[datetime] = None
    occurrences_count: int = 0


class RitualOccurrence(TimestampMixin):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    ritual_id: str
    scheduled_at: datetime
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    status: str = "scheduled"
    attendees: List[str] = []
    notes: Optional[str] = None
    action_items: List[Dict[str, Any]] = []


# --- Stats ---
class InitiativeStats(BaseModel):
    total: int = 0
    by_status: Dict[str, int] = {}
    avg_score: float = 0.0
    completion_rate: float = 0.0
    overdue_count: int = 0
    top_contributors: List[Dict[str, Any]] = []
