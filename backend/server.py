from fastapi import FastAPI, APIRouter, HTTPException, Depends, status, Query, BackgroundTasks, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import re
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional, Dict, Any, Tuple
import uuid
from datetime import datetime, timezone, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from emergentintegrations.llm.chat import LlmChat, UserMessage
import asyncio
import hashlib
from functools import wraps
from collections import defaultdict
import networkx as nx
from community import community_louvain

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ.get('MONGO_URL')
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get('DB_NAME')]

# JWT Configuration
SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'default_secret_key')
ALGORITHM = os.environ.get('JWT_ALGORITHM', 'HS256')
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get('ACCESS_TOKEN_EXPIRE_MINUTES', 60))

# Privacy Configuration
SMALL_GROUP_THRESHOLD = int(os.environ.get('SMALL_GROUP_THRESHOLD', 5))
PII_VAULT_ENCRYPTION_KEY = os.environ.get('PII_VAULT_KEY', 'default_vault_key_change_in_prod')

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

app = FastAPI(title="DigiKawsay API", version="0.5.0")

# Routers
api_router = APIRouter(prefix="/api")
auth_router = APIRouter(prefix="/auth", tags=["Authentication"])
tenant_router = APIRouter(prefix="/tenants", tags=["Tenants"])
user_router = APIRouter(prefix="/users", tags=["Users"])
campaign_router = APIRouter(prefix="/campaigns", tags=["Campaigns"])
script_router = APIRouter(prefix="/scripts", tags=["Scripts"])
segment_router = APIRouter(prefix="/segments", tags=["Segments"])
invite_router = APIRouter(prefix="/invites", tags=["Invitations"])
session_router = APIRouter(prefix="/sessions", tags=["Sessions"])
consent_router = APIRouter(prefix="/consents", tags=["Consents"])
chat_router = APIRouter(prefix="/chat", tags=["VAL Chat"])
insight_router = APIRouter(prefix="/insights", tags=["Insights"])
taxonomy_router = APIRouter(prefix="/taxonomy", tags=["Taxonomy"])
transcript_router = APIRouter(prefix="/transcripts", tags=["Transcripts"])
audit_router = APIRouter(prefix="/audit", tags=["Audit"])
privacy_router = APIRouter(prefix="/privacy", tags=["Privacy"])
reidentification_router = APIRouter(prefix="/reidentification", tags=["Reidentification"])
network_router = APIRouter(prefix="/network", tags=["RunaMap - Network Analysis"])
initiative_router = APIRouter(prefix="/initiatives", tags=["RunaFlow - Initiatives"])
ritual_router = APIRouter(prefix="/rituals", tags=["RunaFlow - Rituals"])

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ============== PYDANTIC MODELS ==============

class TimestampMixin(BaseModel):
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

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

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

# --- Consent Policy (NEW - Phase 3.5) ---
class ConsentPolicyCreate(BaseModel):
    campaign_id: Optional[str] = None
    purpose: str
    data_collected: List[str]  # ["transcript", "metadata", "insights"]
    data_not_used_for: List[str]  # ["individual_surveillance", "punitive_actions"]
    deliverables: List[str]  # ["aggregated_insights", "anonymized_reports"]
    risks_mitigations: str
    user_rights: List[str]  # ["access", "rectification", "deletion", "revocation"]
    retention_days: int = 365
    contact_email: str
    version: str = "1.0"

class ConsentPolicy(TimestampMixin):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    campaign_id: Optional[str] = None
    purpose: str
    data_collected: List[str] = []
    data_not_used_for: List[str] = []
    deliverables: List[str] = []
    risks_mitigations: str = ""
    user_rights: List[str] = []
    retention_days: int = 365
    contact_email: str = ""
    version: str = "1.0"
    is_active: bool = True

# --- Consent (Enhanced) ---
class ConsentCreate(BaseModel):
    campaign_id: str
    accepted: bool
    policy_version: Optional[str] = None
    revocation_preference: str = "retain_aggregates"  # retain_aggregates, delete_all

class Consent(TimestampMixin):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    campaign_id: str
    tenant_id: str
    accepted: bool
    policy_id: Optional[str] = None
    policy_version: str = "1.0"
    consent_text_hash: Optional[str] = None
    revocation_preference: str = "retain_aggregates"
    revoked_at: Optional[datetime] = None
    revocation_reason: Optional[str] = None

# --- PII Vault (NEW - Phase 3.5) ---
class PIIVaultEntry(TimestampMixin):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    pseudonym_id: str
    encrypted_identity: str  # Encrypted user_id
    identity_type: str = "user"  # user, external
    campaign_id: Optional[str] = None
    expires_at: Optional[datetime] = None
    is_deleted: bool = False

# --- Audit Log (NEW - Phase 3.5) ---
class AuditAction:
    VIEW_TRANSCRIPT = "view_transcript"
    VIEW_INSIGHT = "view_insight"
    EXPORT_DATA = "export_data"
    REIDENTIFICATION_REQUEST = "reidentification_request"
    REIDENTIFICATION_APPROVE = "reidentification_approve"
    REIDENTIFICATION_RESOLVE = "reidentification_resolve"
    CONSENT_GIVEN = "consent_given"
    CONSENT_REVOKED = "consent_revoked"
    DATA_DELETED = "data_deleted"
    LOGIN = "login"
    LOGOUT = "logout"

class AuditLog(TimestampMixin):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    correlation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: Optional[str] = None
    user_id: str
    user_role: str
    action: str
    resource_type: str  # transcript, insight, consent, user, etc.
    resource_id: Optional[str] = None
    campaign_id: Optional[str] = None
    details: Dict[str, Any] = {}
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    success: bool = True
    error_message: Optional[str] = None

# --- Reidentification (NEW - Phase 3.5) ---
class ReidentificationReason:
    SAFETY_CONCERN = "safety_concern"
    LEGAL_COMPLIANCE = "legal_compliance"
    EXPLICIT_CONSENT = "explicit_consent"
    DATA_CORRECTION = "data_correction"

class ReidentificationRequestCreate(BaseModel):
    pseudonym_id: str
    reason_code: str
    justification: str
    campaign_id: Optional[str] = None

class ReidentificationRequest(TimestampMixin):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    pseudonym_id: str
    reason_code: str
    justification: str
    campaign_id: Optional[str] = None
    requested_by: str
    status: str = "pending"  # pending, approved, denied, resolved, expired
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    review_notes: Optional[str] = None
    resolved_identity: Optional[str] = None  # Only filled temporarily
    expires_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc) + timedelta(hours=24))

# --- Script ---
class ScriptStep(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    order: int
    question: str
    description: Optional[str] = None
    type: str = "open"
    options: Optional[List[str]] = None
    is_required: bool = True
    follow_up_prompt: Optional[str] = None

class ScriptCreate(BaseModel):
    name: str
    description: Optional[str] = None
    objective: str
    steps: List[ScriptStep] = []
    welcome_message: Optional[str] = None
    closing_message: Optional[str] = None
    estimated_duration_minutes: int = 15

class ScriptUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    objective: Optional[str] = None
    steps: Optional[List[ScriptStep]] = None
    welcome_message: Optional[str] = None
    closing_message: Optional[str] = None
    estimated_duration_minutes: Optional[int] = None

class Script(TimestampMixin):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    name: str
    description: Optional[str] = None
    objective: str
    version: int = 1
    is_active: bool = True
    steps: List[Dict[str, Any]] = []
    welcome_message: Optional[str] = None
    closing_message: Optional[str] = None
    estimated_duration_minutes: int = 15
    created_by: str
    parent_id: Optional[str] = None

class ScriptVersion(TimestampMixin):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    script_id: str
    version: int
    changes: str
    created_by: str
    snapshot: Dict[str, Any] = {}

# --- Segment ---
class SegmentCreate(BaseModel):
    name: str
    description: Optional[str] = None
    criteria: Optional[Dict[str, Any]] = None
    target_count: int = 0

class Segment(TimestampMixin):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    campaign_id: str
    tenant_id: str
    name: str
    description: Optional[str] = None
    criteria: Dict[str, Any] = {}
    target_count: int = 0
    current_count: int = 0
    completion_rate: float = 0.0

# --- Invitation ---
class InviteCreate(BaseModel):
    campaign_id: str
    user_id: Optional[str] = None
    email: Optional[str] = None
    segment_id: Optional[str] = None
    message: Optional[str] = None

class InviteBulk(BaseModel):
    campaign_id: str
    user_ids: List[str] = []
    emails: List[str] = []
    segment_id: Optional[str] = None
    message: Optional[str] = None

class Invite(TimestampMixin):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    campaign_id: str
    tenant_id: str
    user_id: Optional[str] = None
    email: Optional[str] = None
    segment_id: Optional[str] = None
    status: str = "pending"
    sent_at: Optional[datetime] = None
    responded_at: Optional[datetime] = None
    message: Optional[str] = None
    invited_by: str

# --- Campaign ---
class CampaignCreate(BaseModel):
    name: str
    description: Optional[str] = None
    objective: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    script_id: Optional[str] = None
    target_participants: int = 0

class CampaignUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    objective: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    script_id: Optional[str] = None
    target_participants: Optional[int] = None

class Campaign(TimestampMixin):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    name: str
    description: Optional[str] = None
    objective: str
    status: str = "draft"
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    script_id: Optional[str] = None
    created_by: str
    participant_count: int = 0
    session_count: int = 0
    completed_sessions: int = 0
    target_participants: int = 0
    invite_count: int = 0
    insights_extracted: bool = False
    consent_policy_id: Optional[str] = None

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
    is_suppressed: bool = False  # NEW: for small group suppression

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

# --- Coverage ---
class CoverageStats(BaseModel):
    campaign_id: str
    total_invited: int = 0
    total_consented: int = 0
    total_sessions: int = 0
    completed_sessions: int = 0
    participation_rate: float = 0.0
    completion_rate: float = 0.0
    segments: List[Dict[str, Any]] = []

class InsightStats(BaseModel):
    campaign_id: str
    total_insights: int = 0
    by_type: Dict[str, int] = {}
    by_status: Dict[str, int] = {}
    by_sentiment: Dict[str, int] = {}
    top_categories: List[Dict[str, Any]] = []
    suppressed_count: int = 0

# ============== RUNAMAP MODELS (Phase 4) ==============

class NodeType:
    PARTICIPANT = "participant"
    THEME = "theme"
    TENSION = "tension"
    SYMBOL = "symbol"
    CATEGORY = "category"

class EdgeType:
    HABLA_DE = "habla_de"  # Participant -> Theme
    CO_OCURRE = "co_ocurre"  # Theme <-> Theme
    CONSULTA = "consulta"  # Participant -> Participant
    COLABORA = "colabora"  # Participant <-> Participant
    COMPARTE_TEMA = "comparte_tema"  # Participant <-> Participant (indirect via themes)

class NetworkNode(TimestampMixin):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    campaign_id: str
    node_type: str  # participant, theme, tension, symbol, category
    label: str
    pseudonym_id: Optional[str] = None  # For participants
    source_id: Optional[str] = None  # Original entity ID (user_id, category_id, insight_id)
    metadata: Dict[str, Any] = {}
    degree_in: int = 0
    degree_out: int = 0
    betweenness: float = 0.0
    clustering_coef: float = 0.0
    community_id: Optional[int] = None

class NetworkEdge(TimestampMixin):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    campaign_id: str
    source_node_id: str
    target_node_id: str
    edge_type: str  # habla_de, co_ocurre, consulta, colabora, comparte_tema
    weight: float = 1.0
    evidence_links: List[str] = []  # IDs of insights/transcripts that support this edge
    metadata: Dict[str, Any] = {}

class NetworkSnapshot(TimestampMixin):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tenant_id: str
    campaign_id: str
    name: str
    description: Optional[str] = None
    node_count: int = 0
    edge_count: int = 0
    community_count: int = 0
    metrics: Dict[str, Any] = {}
    created_by: str

class NetworkMetrics(BaseModel):
    total_nodes: int = 0
    total_edges: int = 0
    density: float = 0.0
    avg_clustering: float = 0.0
    num_communities: int = 0
    top_brokers: List[Dict[str, Any]] = []
    communities: List[Dict[str, Any]] = []
    nodes_by_type: Dict[str, int] = {}
    edges_by_type: Dict[str, int] = {}

class GraphResponse(BaseModel):
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
    metrics: NetworkMetrics
    snapshot_id: Optional[str] = None

class GenerateNetworkRequest(BaseModel):
    campaign_id: str
    include_participant_theme: bool = True
    include_theme_cooccurrence: bool = True
    include_participant_similarity: bool = True
    min_edge_weight: float = 1.0
    snapshot_name: Optional[str] = None

# ============== RUNAFLOW MODELS (Phase 5) ==============

class InitiativeStatus:
    BACKLOG = "backlog"
    EVALUATING = "en_evaluacion"
    APPROVED = "aprobada"
    IN_PROGRESS = "en_progreso"
    COMPLETED = "completada"
    CANCELLED = "cancelada"

class ScoringMethod:
    ICE = "ice"  # Impact × Confidence × Ease
    RICE = "rice"  # Reach × Impact × Confidence / Effort

class RitualType:
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"

class InitiativeCreate(BaseModel):
    title: str
    description: Optional[str] = None
    campaign_id: str
    source_insight_ids: List[str] = []
    source_community_id: Optional[int] = None
    assigned_to: Optional[str] = None  # user_id
    scoring_method: str = "ice"
    # ICE scores (1-10)
    impact_score: int = 5
    confidence_score: int = 5
    ease_score: int = 5
    # RICE additional fields
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
    # Scoring
    scoring_method: str = "ice"
    impact_score: int = 5
    confidence_score: int = 5
    ease_score: int = 5
    reach_score: int = 100
    effort_score: int = 5
    final_score: float = 0.0
    # Meta
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

class RitualCreate(BaseModel):
    name: str
    description: Optional[str] = None
    ritual_type: str  # daily, weekly, monthly, quarterly
    campaign_id: Optional[str] = None
    day_of_week: Optional[int] = None  # 0=Monday, 6=Sunday
    day_of_month: Optional[int] = None
    time_of_day: Optional[str] = None  # HH:MM format
    duration_minutes: int = 30
    participants: List[str] = []  # user_ids
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
    status: str = "scheduled"  # scheduled, in_progress, completed, cancelled
    attendees: List[str] = []
    notes: Optional[str] = None
    action_items: List[Dict[str, Any]] = []

class InitiativeStats(BaseModel):
    total: int = 0
    by_status: Dict[str, int] = {}
    avg_score: float = 0.0
    completion_rate: float = 0.0
    overdue_count: int = 0
    top_contributors: List[Dict[str, Any]] = []

# ============== HELPER FUNCTIONS ==============

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    credentials_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas")
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if user is None:
        raise credentials_exception
    return user

def generate_pseudonym() -> str:
    return f"P-{uuid.uuid4().hex[:8].upper()}"

def generate_correlation_id() -> str:
    return str(uuid.uuid4())

def serialize_datetime(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    return obj

def serialize_document(doc: dict) -> dict:
    result = {}
    for key, value in doc.items():
        if isinstance(value, datetime):
            result[key] = value.isoformat()
        elif isinstance(value, dict):
            result[key] = serialize_document(value)
        elif isinstance(value, list):
            result[key] = [serialize_document(v) if isinstance(v, dict) else serialize_datetime(v) for v in value]
        else:
            result[key] = value
    return result

def encrypt_identity(identity: str) -> str:
    """Simple encryption for vault - in production use proper encryption"""
    return hashlib.sha256(f"{identity}{PII_VAULT_ENCRYPTION_KEY}".encode()).hexdigest()

def hash_consent_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]

# ============== AUDIT SERVICE (NEW - Phase 3.5) ==============

class AuditService:
    @staticmethod
    async def log(
        user_id: str,
        user_role: str,
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        campaign_id: Optional[str] = None,
        details: Dict[str, Any] = None,
        ip_address: Optional[str] = None,
        correlation_id: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None
    ):
        audit_entry = AuditLog(
            correlation_id=correlation_id or generate_correlation_id(),
            tenant_id=tenant_id,
            user_id=user_id,
            user_role=user_role,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            campaign_id=campaign_id,
            details=details or {},
            ip_address=ip_address,
            success=success,
            error_message=error_message
        )
        await db.audit_logs.insert_one(serialize_document(audit_entry.model_dump()))
        return audit_entry

audit_service = AuditService()

# ============== PII VAULT SERVICE (NEW - Phase 3.5) ==============

class PIIVaultService:
    @staticmethod
    async def create_mapping(user_id: str, tenant_id: str, campaign_id: Optional[str] = None) -> str:
        """Create a new pseudonym mapping in the vault"""
        pseudonym_id = generate_pseudonym()
        encrypted_id = encrypt_identity(user_id)
        
        entry = PIIVaultEntry(
            tenant_id=tenant_id,
            pseudonym_id=pseudonym_id,
            encrypted_identity=encrypted_id,
            campaign_id=campaign_id
        )
        await db.pii_vault.insert_one(serialize_document(entry.model_dump()))
        return pseudonym_id
    
    @staticmethod
    async def get_pseudonym(user_id: str, tenant_id: str) -> Optional[str]:
        """Get existing pseudonym for user"""
        encrypted_id = encrypt_identity(user_id)
        entry = await db.pii_vault.find_one({
            "encrypted_identity": encrypted_id,
            "tenant_id": tenant_id,
            "is_deleted": False
        }, {"_id": 0})
        return entry.get("pseudonym_id") if entry else None
    
    @staticmethod
    async def resolve_identity(pseudonym_id: str, tenant_id: str, requester_id: str) -> Optional[str]:
        """Resolve pseudonym to identity - REQUIRES APPROVED REIDENTIFICATION REQUEST"""
        # Check for approved request
        request = await db.reidentification_requests.find_one({
            "pseudonym_id": pseudonym_id,
            "tenant_id": tenant_id,
            "status": "approved",
            "expires_at": {"$gt": datetime.now(timezone.utc).isoformat()}
        }, {"_id": 0})
        
        if not request:
            return None
        
        # Get vault entry
        entry = await db.pii_vault.find_one({
            "pseudonym_id": pseudonym_id,
            "tenant_id": tenant_id,
            "is_deleted": False
        }, {"_id": 0})
        
        if not entry:
            return None
        
        # Mark request as resolved
        await db.reidentification_requests.update_one(
            {"id": request["id"]},
            {"$set": {"status": "resolved", "updated_at": datetime.now(timezone.utc).isoformat()}}
        )
        
        # Return user info (not the encrypted ID, need to look up)
        users = await db.users.find({}, {"_id": 0, "hashed_password": 0}).to_list(1000)
        for user in users:
            if encrypt_identity(user["id"]) == entry["encrypted_identity"]:
                return user["id"]
        
        return None
    
    @staticmethod
    async def delete_mapping(pseudonym_id: str, tenant_id: str):
        """Soft delete a mapping (for consent revocation with delete_all)"""
        await db.pii_vault.update_one(
            {"pseudonym_id": pseudonym_id, "tenant_id": tenant_id},
            {"$set": {"is_deleted": True, "updated_at": datetime.now(timezone.utc).isoformat()}}
        )

pii_vault_service = PIIVaultService()

# ============== PSEUDONYMIZATION SERVICE (Enhanced - Phase 3.5) ==============

class PseudonymizationService:
    def __init__(self):
        # Enhanced patterns for NER-like detection
        self.patterns = {
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'phone': r'\b(?:\+?[0-9]{1,3}[-.\s]?)?(?:\([0-9]{2,3}\)[-.\s]?)?[0-9]{3,4}[-.\s]?[0-9]{3,4}\b',
            'name_title': r'\b(?:Sr\.|Sra\.|Dr\.|Dra\.|Ing\.|Lic\.|Prof\.)\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+\b',
            'full_name': r'\b[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)?\b',
            'dni_cedula': r'\b[0-9]{7,11}\b',
            'date_birth': r'\b(?:0?[1-9]|[12][0-9]|3[01])[/-](?:0?[1-9]|1[012])[/-](?:19|20)?\d{2}\b',
            'address': r'\b(?:Calle|Av\.|Avenida|Carrera|Jr\.|Jirón)\s+[A-Za-záéíóúñÁÉÍÓÚÑ0-9\s,#.-]+\b',
        }
    
    def _generate_replacement(self, match_type: str, original: str, session_id: str) -> str:
        hash_val = hashlib.sha256(f"{original}{session_id}".encode()).hexdigest()[:6].upper()
        replacements = {
            'email': f'[EMAIL-{hash_val}]',
            'phone': '[TELÉFONO-REDACTADO]',
            'name_title': f'[PERSONA-{hash_val}]',
            'full_name': f'[PERSONA-{hash_val}]',
            'dni_cedula': '[DOCUMENTO-REDACTADO]',
            'date_birth': '[FECHA-REDACTADA]',
            'address': '[DIRECCIÓN-REDACTADA]',
        }
        return replacements.get(match_type, f'[REDACTADO-{hash_val}]')
    
    def pseudonymize_text(self, text: str, session_id: str = "") -> tuple[str, List[Dict]]:
        """Enhanced pseudonymization with tracking of redactions"""
        result = text
        redactions = []
        
        for pattern_name, pattern in self.patterns.items():
            for match in re.finditer(pattern, result):
                original = match.group()
                replacement = self._generate_replacement(pattern_name, original, session_id)
                redactions.append({
                    "type": pattern_name,
                    "original_hash": hashlib.sha256(original.encode()).hexdigest()[:8],
                    "replacement": replacement
                })
                result = result.replace(original, replacement, 1)
        
        return result, redactions
    
    async def pseudonymize_transcript(self, transcript_id: str) -> Dict[str, Any]:
        """Pseudonymize transcript and store mapping in vault"""
        transcript = await db.transcripts.find_one({"id": transcript_id}, {"_id": 0})
        if not transcript or transcript.get("is_pseudonymized"):
            return {"success": False, "reason": "Already pseudonymized or not found"}
        
        session_id = transcript.get("session_id", "")
        user_id = transcript.get("user_id")
        tenant_id = transcript.get("tenant_id", "default")
        
        # Create or get pseudonym in vault
        pseudonym_id = await pii_vault_service.get_pseudonym(user_id, tenant_id)
        if not pseudonym_id:
            pseudonym_id = await pii_vault_service.create_mapping(user_id, tenant_id, transcript.get("campaign_id"))
        
        pseudonymized_messages = []
        total_redactions = []
        
        for msg in transcript.get("messages", []):
            new_msg = msg.copy()
            if msg.get("role") == "user":
                new_content, redactions = self.pseudonymize_text(msg.get("content", ""), session_id)
                new_msg["content"] = new_content
                total_redactions.extend(redactions)
            pseudonymized_messages.append(new_msg)
        
        await db.transcripts.update_one(
            {"id": transcript_id},
            {"$set": {
                "messages": pseudonymized_messages,
                "is_pseudonymized": True,
                "pseudonymized_at": datetime.now(timezone.utc).isoformat(),
                "pseudonym_id": pseudonym_id,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        return {
            "success": True,
            "pseudonym_id": pseudonym_id,
            "redactions_count": len(total_redactions),
            "redaction_types": list(set(r["type"] for r in total_redactions))
        }

pseudonymization_service = PseudonymizationService()

# ============== SUPPRESSION SERVICE (NEW - Phase 3.5) ==============

class SuppressionService:
    @staticmethod
    async def check_and_suppress_insights(campaign_id: str, threshold: int = None) -> Dict[str, Any]:
        """Check insights for small group suppression"""
        threshold = threshold or SMALL_GROUP_THRESHOLD
        
        # Get all insights grouped by source characteristics
        insights = await db.insights.find({"campaign_id": campaign_id}, {"_id": 0}).to_list(1000)
        
        suppressed = 0
        unsuppressed = 0
        
        # Group by category and type
        groups = {}
        for insight in insights:
            key = f"{insight.get('type', 'unknown')}_{insight.get('category_id', 'none')}"
            if key not in groups:
                groups[key] = []
            groups[key].append(insight)
        
        # Check each group
        for group_key, group_insights in groups.items():
            # Count unique sources (sessions)
            unique_sources = len(set(i.get("source_session_id") for i in group_insights if i.get("source_session_id")))
            
            should_suppress = unique_sources < threshold and unique_sources > 0
            
            for insight in group_insights:
                if should_suppress and not insight.get("is_suppressed"):
                    await db.insights.update_one(
                        {"id": insight["id"]},
                        {"$set": {"is_suppressed": True, "updated_at": datetime.now(timezone.utc).isoformat()}}
                    )
                    suppressed += 1
                elif not should_suppress and insight.get("is_suppressed"):
                    await db.insights.update_one(
                        {"id": insight["id"]},
                        {"$set": {"is_suppressed": False, "updated_at": datetime.now(timezone.utc).isoformat()}}
                    )
                    unsuppressed += 1
        
        return {
            "campaign_id": campaign_id,
            "threshold": threshold,
            "suppressed_count": suppressed,
            "unsuppressed_count": unsuppressed,
            "total_groups": len(groups)
        }
    
    @staticmethod
    async def get_visible_insights(campaign_id: str, user_role: str) -> List[Dict]:
        """Get insights respecting suppression rules"""
        query = {"campaign_id": campaign_id}
        
        # Only admins and security officers can see suppressed insights
        if user_role not in ["admin", "security_officer"]:
            query["is_suppressed"] = {"$ne": True}
        
        insights = await db.insights.find(query, {"_id": 0}).to_list(500)
        return insights

suppression_service = SuppressionService()

# ============== VAL CHAT SERVICE ==============

class VALChatService:
    def __init__(self):
        self.api_key = os.environ.get('EMERGENT_LLM_KEY')
        self.active_chats: Dict[str, LlmChat] = {}
    
    def get_system_prompt(self, campaign_objective: str = "", script_context: str = "") -> str:
        return f"""Eres VAL, una facilitadora conversacional experta en coaching ontológico e Investigación Acción Participativa (IAP).

Tu rol es:
1. Facilitar diálogos reflexivos y generativos
2. Escuchar activamente y hacer preguntas poderosas
3. Ayudar a los participantes a explorar sus experiencias y perspectivas
4. Mantener un espacio seguro y confidencial
5. Extraer insights valiosos de las conversaciones

Objetivo de la campaña: {campaign_objective or "Explorar experiencias organizacionales"}

{script_context}

Principios de facilitación:
- Usa preguntas abiertas que inviten a la reflexión
- Valida las emociones y experiencias compartidas
- Busca patrones y temas emergentes
- Mantén la neutralidad y evita juicios
- Fomenta la profundización en los temas importantes

Responde siempre en español de manera cálida y profesional. Limita tus respuestas a 2-3 párrafos máximo."""

    async def get_or_create_chat(self, session_id: str, campaign_objective: str = "", script_context: str = "") -> LlmChat:
        if session_id not in self.active_chats:
            chat = LlmChat(api_key=self.api_key, session_id=session_id, system_message=self.get_system_prompt(campaign_objective, script_context))
            chat.with_model("gemini", "gemini-2.5-flash")
            self.active_chats[session_id] = chat
        return self.active_chats[session_id]
    
    async def send_message(self, session_id: str, message: str, campaign_objective: str = "", script_context: str = "") -> str:
        chat = await self.get_or_create_chat(session_id, campaign_objective, script_context)
        response = await chat.send_message(UserMessage(text=message))
        return response
    
    def close_session(self, session_id: str):
        if session_id in self.active_chats:
            del self.active_chats[session_id]

val_service = VALChatService()

# ============== INSIGHT EXTRACTION SERVICE ==============

class InsightExtractionService:
    def __init__(self):
        self.api_key = os.environ.get('EMERGENT_LLM_KEY')
    
    async def extract_insights_from_transcript(self, transcript_id: str, campaign_id: str, tenant_id: str) -> List[Dict]:
        transcript = await db.transcripts.find_one({"id": transcript_id}, {"_id": 0})
        if not transcript:
            return []
        
        campaign = await db.campaigns.find_one({"id": campaign_id}, {"_id": 0})
        objective = campaign.get("objective", "") if campaign else ""
        
        conversation = "\n".join([f"{'Participante' if m['role'] == 'user' else 'VAL'}: {m['content']}" for m in transcript.get("messages", [])])
        if not conversation:
            return []
        
        extraction_prompt = f"""Analiza la siguiente conversación de una campaña de diagnóstico organizacional.
        
Objetivo: {objective}

Conversación:
{conversation}

Extrae los insights más relevantes en formato JSON. Para cada insight incluye:
- content: descripción del hallazgo (máx 200 caracteres)
- type: uno de [theme, tension, symbol, opportunity, risk]
- sentiment: uno de [positive, negative, neutral, mixed]
- importance: número del 1 al 10
- source_quote: cita textual que respalda el insight (máx 150 caracteres)

Responde SOLO con un array JSON válido. Máximo 5 insights."""

        try:
            chat = LlmChat(api_key=self.api_key, session_id=f"extraction-{transcript_id}", system_message="Eres un experto en análisis cualitativo organizacional.")
            chat.with_model("gemini", "gemini-2.5-flash")
            response = await chat.send_message(UserMessage(text=extraction_prompt))
            
            import json
            response_clean = response.strip()
            if response_clean.startswith("```json"): response_clean = response_clean[7:]
            if response_clean.startswith("```"): response_clean = response_clean[3:]
            if response_clean.endswith("```"): response_clean = response_clean[:-3]
            
            insights_data = json.loads(response_clean.strip())
            created_insights = []
            
            for data in insights_data:
                insight = Insight(
                    tenant_id=tenant_id, campaign_id=campaign_id,
                    content=data.get("content", "")[:500], type=data.get("type", "theme"),
                    sentiment=data.get("sentiment"), importance=min(max(int(data.get("importance", 5)), 1), 10),
                    source_session_id=transcript.get("session_id"), source_quote=data.get("source_quote", "")[:300],
                    extracted_by="ai"
                )
                await db.insights.insert_one(serialize_document(insight.model_dump()))
                created_insights.append(insight.model_dump())
            
            await db.transcripts.update_one({"id": transcript_id}, {"$set": {"insights_extracted": True}})
            return created_insights
        except Exception as e:
            logger.error(f"Error extracting insights: {e}")
            return []

insight_extraction_service = InsightExtractionService()

# ============== NETWORK ANALYSIS SERVICE (Phase 4 - RunaMap) ==============

class NetworkAnalysisService:
    """Service for Social Network Analysis (SNA) - RunaMap"""
    
    @staticmethod
    async def build_graph_from_campaign(
        campaign_id: str,
        tenant_id: str,
        include_participant_theme: bool = True,
        include_theme_cooccurrence: bool = True,
        include_participant_similarity: bool = True,
        min_edge_weight: float = 1.0
    ) -> Tuple[List[Dict], List[Dict]]:
        """Build network graph from campaign data"""
        
        nodes = []
        edges = []
        node_map = {}  # source_id -> node_id
        
        # Get all insights and transcripts for the campaign
        insights = await db.insights.find(
            {"campaign_id": campaign_id, "is_suppressed": {"$ne": True}},
            {"_id": 0}
        ).to_list(500)
        
        transcripts = await db.transcripts.find(
            {"campaign_id": campaign_id},
            {"_id": 0}
        ).to_list(500)
        
        # Get taxonomy categories
        categories = await db.taxonomy_categories.find(
            {"tenant_id": tenant_id, "is_active": True},
            {"_id": 0}
        ).to_list(100)
        
        # Build participant nodes from transcripts
        participant_themes = defaultdict(set)  # pseudonym_id -> set of category_ids
        
        for transcript in transcripts:
            pseudonym_id = transcript.get("pseudonym_id")
            if not pseudonym_id:
                continue
            
            if pseudonym_id not in node_map:
                node_id = str(uuid.uuid4())
                node_map[pseudonym_id] = node_id
                nodes.append({
                    "id": node_id,
                    "tenant_id": tenant_id,
                    "campaign_id": campaign_id,
                    "node_type": NodeType.PARTICIPANT,
                    "label": pseudonym_id,
                    "pseudonym_id": pseudonym_id,
                    "source_id": pseudonym_id,
                    "metadata": {"session_count": 1}
                })
            else:
                # Increment session count
                for n in nodes:
                    if n["id"] == node_map[pseudonym_id]:
                        n["metadata"]["session_count"] = n["metadata"].get("session_count", 0) + 1
        
        # Build theme nodes from categories and link to insights
        category_map = {c["id"]: c for c in categories}
        theme_participants = defaultdict(set)  # category_id -> set of pseudonym_ids
        theme_cooccurrence = defaultdict(lambda: defaultdict(int))  # theme1 -> theme2 -> count
        
        for insight in insights:
            category_id = insight.get("category_id")
            session_id = insight.get("source_session_id")
            
            if category_id and category_id not in node_map:
                cat = category_map.get(category_id, {})
                node_id = str(uuid.uuid4())
                node_map[category_id] = node_id
                nodes.append({
                    "id": node_id,
                    "tenant_id": tenant_id,
                    "campaign_id": campaign_id,
                    "node_type": cat.get("type", NodeType.THEME),
                    "label": cat.get("name", "Tema desconocido"),
                    "source_id": category_id,
                    "metadata": {
                        "color": cat.get("color"),
                        "description": cat.get("description"),
                        "insight_count": 1
                    }
                })
            elif category_id:
                # Increment insight count
                for n in nodes:
                    if n["id"] == node_map[category_id]:
                        n["metadata"]["insight_count"] = n["metadata"].get("insight_count", 0) + 1
            
            # Link participant to theme
            if session_id:
                transcript = next((t for t in transcripts if t.get("session_id") == session_id), None)
                if transcript and transcript.get("pseudonym_id"):
                    pseudonym_id = transcript["pseudonym_id"]
                    if category_id:
                        participant_themes[pseudonym_id].add(category_id)
                        theme_participants[category_id].add(pseudonym_id)
        
        # Build theme co-occurrence from insights in same session
        session_themes = defaultdict(set)
        for insight in insights:
            session_id = insight.get("source_session_id")
            category_id = insight.get("category_id")
            if session_id and category_id:
                session_themes[session_id].add(category_id)
        
        for session_id, themes in session_themes.items():
            themes_list = list(themes)
            for i, t1 in enumerate(themes_list):
                for t2 in themes_list[i+1:]:
                    theme_cooccurrence[t1][t2] += 1
                    theme_cooccurrence[t2][t1] += 1
        
        # Create edges
        edge_counts = defaultdict(int)
        
        # 1. Participant -> Theme edges (HABLA_DE)
        if include_participant_theme:
            for pseudonym_id, themes in participant_themes.items():
                if pseudonym_id not in node_map:
                    continue
                participant_node_id = node_map[pseudonym_id]
                for theme_id in themes:
                    if theme_id not in node_map:
                        continue
                    theme_node_id = node_map[theme_id]
                    edge_key = f"{participant_node_id}_{theme_node_id}_habla_de"
                    if edge_key not in edge_counts:
                        edges.append({
                            "id": str(uuid.uuid4()),
                            "tenant_id": tenant_id,
                            "campaign_id": campaign_id,
                            "source_node_id": participant_node_id,
                            "target_node_id": theme_node_id,
                            "edge_type": EdgeType.HABLA_DE,
                            "weight": 1.0,
                            "evidence_links": []
                        })
                    edge_counts[edge_key] += 1
        
        # 2. Theme <-> Theme edges (CO_OCURRE)
        if include_theme_cooccurrence:
            for t1, cooccs in theme_cooccurrence.items():
                if t1 not in node_map:
                    continue
                for t2, count in cooccs.items():
                    if t2 not in node_map or count < min_edge_weight:
                        continue
                    if t1 < t2:  # Avoid duplicates
                        edges.append({
                            "id": str(uuid.uuid4()),
                            "tenant_id": tenant_id,
                            "campaign_id": campaign_id,
                            "source_node_id": node_map[t1],
                            "target_node_id": node_map[t2],
                            "edge_type": EdgeType.CO_OCURRE,
                            "weight": float(count),
                            "evidence_links": []
                        })
        
        # 3. Participant <-> Participant edges (COMPARTE_TEMA)
        if include_participant_similarity:
            pseudonyms = list(participant_themes.keys())
            for i, p1 in enumerate(pseudonyms):
                if p1 not in node_map:
                    continue
                for p2 in pseudonyms[i+1:]:
                    if p2 not in node_map:
                        continue
                    # Calculate shared themes
                    shared = participant_themes[p1] & participant_themes[p2]
                    if len(shared) >= min_edge_weight:
                        edges.append({
                            "id": str(uuid.uuid4()),
                            "tenant_id": tenant_id,
                            "campaign_id": campaign_id,
                            "source_node_id": node_map[p1],
                            "target_node_id": node_map[p2],
                            "edge_type": EdgeType.COMPARTE_TEMA,
                            "weight": float(len(shared)),
                            "evidence_links": list(shared)
                        })
        
        return nodes, edges
    
    @staticmethod
    def calculate_metrics(nodes: List[Dict], edges: List[Dict]) -> Dict[str, Any]:
        """Calculate network metrics using NetworkX"""
        
        if not nodes:
            return NetworkMetrics().model_dump()
        
        # Build NetworkX graph
        G = nx.Graph()
        
        for node in nodes:
            G.add_node(node["id"], **node)
        
        for edge in edges:
            G.add_edge(
                edge["source_node_id"],
                edge["target_node_id"],
                weight=edge.get("weight", 1.0),
                edge_type=edge.get("edge_type")
            )
        
        # Calculate metrics
        metrics = {
            "total_nodes": G.number_of_nodes(),
            "total_edges": G.number_of_edges(),
            "density": nx.density(G) if G.number_of_nodes() > 1 else 0.0,
            "avg_clustering": 0.0,
            "num_communities": 0,
            "top_brokers": [],
            "communities": [],
            "nodes_by_type": defaultdict(int),
            "edges_by_type": defaultdict(int)
        }
        
        # Count by type
        for node in nodes:
            metrics["nodes_by_type"][node.get("node_type", "unknown")] += 1
        for edge in edges:
            metrics["edges_by_type"][edge.get("edge_type", "unknown")] += 1
        
        metrics["nodes_by_type"] = dict(metrics["nodes_by_type"])
        metrics["edges_by_type"] = dict(metrics["edges_by_type"])
        
        if G.number_of_nodes() < 2:
            return metrics
        
        # Betweenness Centrality (for brokers)
        try:
            betweenness = nx.betweenness_centrality(G, weight="weight")
            top_brokers = sorted(betweenness.items(), key=lambda x: x[1], reverse=True)[:10]
            metrics["top_brokers"] = [
                {
                    "node_id": node_id,
                    "label": G.nodes[node_id].get("label", ""),
                    "node_type": G.nodes[node_id].get("node_type", ""),
                    "betweenness": round(score, 4)
                }
                for node_id, score in top_brokers if score > 0
            ]
            
            # Update node betweenness
            for node in nodes:
                node["betweenness"] = round(betweenness.get(node["id"], 0.0), 4)
        except Exception as e:
            logger.warning(f"Error calculating betweenness: {e}")
        
        # Degree Centrality
        try:
            in_degree = dict(G.degree())
            for node in nodes:
                node["degree_in"] = in_degree.get(node["id"], 0)
                node["degree_out"] = in_degree.get(node["id"], 0)  # Undirected
        except Exception as e:
            logger.warning(f"Error calculating degree: {e}")
        
        # Clustering Coefficient
        try:
            clustering = nx.clustering(G)
            metrics["avg_clustering"] = round(nx.average_clustering(G), 4)
            for node in nodes:
                node["clustering_coef"] = round(clustering.get(node["id"], 0.0), 4)
        except Exception as e:
            logger.warning(f"Error calculating clustering: {e}")
        
        # Community Detection (Louvain)
        try:
            if G.number_of_edges() > 0:
                partition = community_louvain.best_partition(G, weight="weight")
                communities = defaultdict(list)
                for node_id, comm_id in partition.items():
                    communities[comm_id].append({
                        "node_id": node_id,
                        "label": G.nodes[node_id].get("label", ""),
                        "node_type": G.nodes[node_id].get("node_type", "")
                    })
                    # Update node community
                    for node in nodes:
                        if node["id"] == node_id:
                            node["community_id"] = comm_id
                
                metrics["num_communities"] = len(communities)
                metrics["communities"] = [
                    {"id": comm_id, "size": len(members), "members": members[:5]}
                    for comm_id, members in sorted(communities.items(), key=lambda x: -len(x[1]))
                ]
        except Exception as e:
            logger.warning(f"Error detecting communities: {e}")
        
        return metrics
    
    @staticmethod
    async def save_snapshot(
        campaign_id: str,
        tenant_id: str,
        nodes: List[Dict],
        edges: List[Dict],
        metrics: Dict[str, Any],
        name: str,
        created_by: str,
        description: str = None
    ) -> str:
        """Save a network snapshot"""
        
        snapshot = NetworkSnapshot(
            tenant_id=tenant_id,
            campaign_id=campaign_id,
            name=name,
            description=description,
            node_count=len(nodes),
            edge_count=len(edges),
            community_count=metrics.get("num_communities", 0),
            metrics=metrics,
            created_by=created_by
        )
        
        await db.network_snapshots.insert_one(serialize_document(snapshot.model_dump()))
        
        # Save nodes and edges with snapshot reference
        for node in nodes:
            node["snapshot_id"] = snapshot.id
        for edge in edges:
            edge["snapshot_id"] = snapshot.id
        
        if nodes:
            await db.network_nodes.insert_many([serialize_document(n) for n in nodes])
        if edges:
            await db.network_edges.insert_many([serialize_document(e) for e in edges])
        
        return snapshot.id

network_analysis_service = NetworkAnalysisService()

# ============== RUNAFLOW SERVICE (Phase 5) ==============

class InitiativeService:
    @staticmethod
    def calculate_ice_score(impact: int, confidence: int, ease: int) -> float:
        """Calculate ICE score: Impact × Confidence × Ease / 10"""
        return round((impact * confidence * ease) / 10, 2)
    
    @staticmethod
    def calculate_rice_score(reach: int, impact: int, confidence: int, effort: int) -> float:
        """Calculate RICE score: (Reach × Impact × Confidence) / Effort"""
        if effort <= 0:
            effort = 1
        # Normalize: reach in hundreds, impact/confidence 1-10, effort 1-10
        return round((reach * impact * (confidence / 10)) / effort, 2)
    
    @staticmethod
    def calculate_score(initiative: dict) -> float:
        """Calculate score based on scoring method"""
        method = initiative.get("scoring_method", "ice")
        if method == "rice":
            return InitiativeService.calculate_rice_score(
                initiative.get("reach_score", 100),
                initiative.get("impact_score", 5),
                initiative.get("confidence_score", 5),
                initiative.get("effort_score", 5)
            )
        else:  # ICE
            return InitiativeService.calculate_ice_score(
                initiative.get("impact_score", 5),
                initiative.get("confidence_score", 5),
                initiative.get("ease_score", 5)
            )
    
    @staticmethod
    async def get_initiative_leaders(campaign_id: str) -> List[Dict]:
        """Get users who lead initiatives for network visualization"""
        initiatives = await db.initiatives.find(
            {"campaign_id": campaign_id, "assigned_to": {"$ne": None}},
            {"_id": 0}
        ).to_list(500)
        
        leader_stats = defaultdict(lambda: {"count": 0, "completed": 0, "in_progress": 0})
        
        for init in initiatives:
            user_id = init.get("assigned_to")
            if user_id:
                leader_stats[user_id]["count"] += 1
                if init.get("status") == "completada":
                    leader_stats[user_id]["completed"] += 1
                elif init.get("status") == "en_progreso":
                    leader_stats[user_id]["in_progress"] += 1
        
        # Get user details
        leaders = []
        for user_id, stats in leader_stats.items():
            user = await db.users.find_one({"id": user_id}, {"_id": 0, "hashed_password": 0})
            if user:
                leaders.append({
                    "user_id": user_id,
                    "name": user.get("full_name", "Unknown"),
                    "pseudonym_id": user.get("pseudonym_id"),
                    "initiatives_count": stats["count"],
                    "completed_count": stats["completed"],
                    "in_progress_count": stats["in_progress"],
                    "is_initiative_leader": True
                })
        
        return sorted(leaders, key=lambda x: -x["initiatives_count"])

initiative_service = InitiativeService()

class RitualService:
    @staticmethod
    def calculate_next_occurrence(ritual: dict) -> Optional[datetime]:
        """Calculate next occurrence based on ritual type"""
        now = datetime.now(timezone.utc)
        ritual_type = ritual.get("ritual_type")
        time_str = ritual.get("time_of_day", "09:00")
        
        try:
            hour, minute = map(int, time_str.split(":"))
        except:
            hour, minute = 9, 0
        
        if ritual_type == "daily":
            next_date = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if next_date <= now:
                next_date += timedelta(days=1)
            return next_date
        
        elif ritual_type == "weekly":
            day_of_week = ritual.get("day_of_week", 0)
            days_ahead = day_of_week - now.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            next_date = now + timedelta(days=days_ahead)
            return next_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        elif ritual_type == "monthly":
            day_of_month = ritual.get("day_of_month", 1)
            next_date = now.replace(day=min(day_of_month, 28), hour=hour, minute=minute, second=0, microsecond=0)
            if next_date <= now:
                if now.month == 12:
                    next_date = next_date.replace(year=now.year + 1, month=1)
                else:
                    next_date = next_date.replace(month=now.month + 1)
            return next_date
        
        elif ritual_type == "quarterly":
            current_quarter = (now.month - 1) // 3
            next_quarter_start_month = ((current_quarter + 1) % 4) * 3 + 1
            year = now.year if next_quarter_start_month > now.month else now.year + 1
            day_of_month = ritual.get("day_of_month", 1)
            return datetime(year, next_quarter_start_month, min(day_of_month, 28), hour, minute, tzinfo=timezone.utc)
        
        return None

ritual_service = RitualService()

# ============== AUTH ROUTES ==============

@auth_router.post("/register", response_model=TokenResponse)
async def register(user_data: UserCreate):
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
    return TokenResponse(access_token=access_token, user=UserResponse(**{k: v for k, v in user_obj.model_dump().items() if k in UserResponse.model_fields}))

@auth_router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin, request: Request):
    user = await db.users.find_one({"email": credentials.email}, {"_id": 0})
    if not user or not verify_password(credentials.password, user.get("hashed_password", "")):
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
    
    # Audit login
    await audit_service.log(
        user_id=user["id"], user_role=user["role"], action=AuditAction.LOGIN,
        resource_type="session", tenant_id=user.get("tenant_id"),
        ip_address=request.client.host if request.client else None
    )
    
    access_token = create_access_token(data={"sub": user["id"]})
    return TokenResponse(access_token=access_token, user=UserResponse(**{k: user.get(k) for k in UserResponse.model_fields}))

@auth_router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    return UserResponse(**{k: current_user.get(k) for k in UserResponse.model_fields})

# ============== USER ROUTES ==============

@user_router.get("/", response_model=List[UserResponse])
async def list_users(current_user: dict = Depends(get_current_user), role: Optional[str] = None):
    if current_user["role"] not in ["admin", "facilitator"]:
        raise HTTPException(status_code=403, detail="Sin permisos")
    query = {"role": role} if role else {}
    users = await db.users.find(query, {"_id": 0, "hashed_password": 0}).to_list(500)
    return [UserResponse(**{k: u.get(k) for k in UserResponse.model_fields}) for u in users]

# ============== CONSENT POLICY ROUTES (NEW - Phase 3.5) ==============

@consent_router.post("/policy", response_model=ConsentPolicy)
async def create_consent_policy(policy_data: ConsentPolicyCreate, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["admin", "facilitator"]:
        raise HTTPException(status_code=403, detail="Sin permisos")
    
    policy = ConsentPolicy(tenant_id=current_user.get("tenant_id") or "default", **policy_data.model_dump())
    await db.consent_policies.insert_one(serialize_document(policy.model_dump()))
    
    # Link to campaign if specified
    if policy_data.campaign_id:
        await db.campaigns.update_one({"id": policy_data.campaign_id}, {"$set": {"consent_policy_id": policy.id}})
    
    return policy

@consent_router.get("/policy/{campaign_id}")
async def get_consent_policy(campaign_id: str, current_user: dict = Depends(get_current_user)):
    """Get the consent policy for a campaign with full content"""
    campaign = await db.campaigns.find_one({"id": campaign_id}, {"_id": 0})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaña no encontrada")
    
    policy = None
    if campaign.get("consent_policy_id"):
        policy = await db.consent_policies.find_one({"id": campaign["consent_policy_id"]}, {"_id": 0})
    
    if not policy:
        # Return default policy
        policy = {
            "id": "default",
            "version": "1.0",
            "purpose": campaign.get("objective", "Diagnóstico organizacional"),
            "data_collected": ["Transcripción de conversación", "Metadatos de sesión", "Insights extraídos"],
            "data_not_used_for": [
                "Vigilancia individual",
                "Acciones punitivas o disciplinarias",
                "Evaluación de desempeño individual",
                "Identificación de personas específicas"
            ],
            "deliverables": [
                "Insights agregados y anonimizados",
                "Reportes sin información identificable",
                "Análisis de tendencias grupales"
            ],
            "risks_mitigations": "Sus respuestas serán pseudonimizadas antes de cualquier análisis. Los grupos pequeños (<5 personas) serán suprimidos para evitar identificación indirecta.",
            "user_rights": [
                "Acceso a sus datos",
                "Rectificación de información incorrecta",
                "Eliminación de sus datos",
                "Revocación del consentimiento en cualquier momento"
            ],
            "retention_days": 365,
            "contact_email": "privacidad@digikawsay.com"
        }
    
    return {"campaign": campaign, "policy": policy}

@consent_router.get("/policy")
async def list_consent_policies(current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["admin", "facilitator"]:
        raise HTTPException(status_code=403, detail="Sin permisos")
    policies = await db.consent_policies.find({"is_active": True}, {"_id": 0}).to_list(100)
    return policies

# ============== CONSENT ROUTES (Enhanced) ==============

@consent_router.post("/", response_model=Consent)
async def create_consent(consent_data: ConsentCreate, request: Request, current_user: dict = Depends(get_current_user)):
    campaign = await db.campaigns.find_one({"id": consent_data.campaign_id}, {"_id": 0})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaña no encontrada")
    
    existing = await db.consents.find_one({"user_id": current_user["id"], "campaign_id": consent_data.campaign_id, "revoked_at": None})
    if existing:
        raise HTTPException(status_code=400, detail="Ya existe consentimiento activo")
    
    # Get policy version
    policy_version = consent_data.policy_version or "1.0"
    policy_id = campaign.get("consent_policy_id")
    
    consent = Consent(
        user_id=current_user["id"],
        campaign_id=consent_data.campaign_id,
        tenant_id=campaign.get("tenant_id", "default"),
        accepted=consent_data.accepted,
        policy_id=policy_id,
        policy_version=policy_version,
        revocation_preference=consent_data.revocation_preference
    )
    await db.consents.insert_one(serialize_document(consent.model_dump()))
    
    # Audit
    await audit_service.log(
        user_id=current_user["id"], user_role=current_user["role"],
        action=AuditAction.CONSENT_GIVEN, resource_type="consent",
        resource_id=consent.id, campaign_id=consent_data.campaign_id,
        tenant_id=campaign.get("tenant_id"),
        details={"accepted": consent_data.accepted, "policy_version": policy_version},
        ip_address=request.client.host if request.client else None
    )
    
    if consent_data.accepted:
        await db.campaigns.update_one({"id": consent_data.campaign_id}, {"$inc": {"participant_count": 1}})
    
    return consent

@consent_router.get("/my-consents")
async def get_my_consents(current_user: dict = Depends(get_current_user)):
    consents = await db.consents.find({"user_id": current_user["id"], "revoked_at": None}, {"_id": 0}).to_list(100)
    return consents

@consent_router.post("/{consent_id}/revoke")
async def revoke_consent(consent_id: str, reason: Optional[str] = None, request: Request = None, current_user: dict = Depends(get_current_user)):
    consent = await db.consents.find_one({"id": consent_id, "user_id": current_user["id"]}, {"_id": 0})
    if not consent:
        raise HTTPException(status_code=404, detail="Consentimiento no encontrado")
    
    # Update consent
    await db.consents.update_one(
        {"id": consent_id},
        {"$set": {
            "revoked_at": datetime.now(timezone.utc).isoformat(),
            "revocation_reason": reason
        }}
    )
    
    # Handle data based on revocation preference
    preference = consent.get("revocation_preference", "retain_aggregates")
    
    if preference == "delete_all":
        # Mark transcripts for deletion
        await db.transcripts.update_many(
            {"user_id": current_user["id"], "campaign_id": consent["campaign_id"]},
            {"$set": {"marked_for_deletion": True}}
        )
        # Delete vault mappings
        tenant_id = consent.get("tenant_id", "default")
        pseudonym = await pii_vault_service.get_pseudonym(current_user["id"], tenant_id)
        if pseudonym:
            await pii_vault_service.delete_mapping(pseudonym, tenant_id)
    
    # Audit
    await audit_service.log(
        user_id=current_user["id"], user_role=current_user["role"],
        action=AuditAction.CONSENT_REVOKED, resource_type="consent",
        resource_id=consent_id, campaign_id=consent["campaign_id"],
        details={"reason": reason, "preference": preference}
    )
    
    # Update campaign count
    await db.campaigns.update_one({"id": consent["campaign_id"]}, {"$inc": {"participant_count": -1}})
    
    return {"message": "Consentimiento revocado", "data_handling": preference}

# ============== AUDIT ROUTES (NEW - Phase 3.5) ==============

@audit_router.get("/")
async def get_audit_logs(
    current_user: dict = Depends(get_current_user),
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    user_id: Optional[str] = None,
    campaign_id: Optional[str] = None,
    limit: int = 100
):
    if current_user["role"] not in ["admin", "security_officer"]:
        raise HTTPException(status_code=403, detail="Solo admin/security_officer pueden ver auditoría")
    
    query = {}
    if action: query["action"] = action
    if resource_type: query["resource_type"] = resource_type
    if user_id: query["user_id"] = user_id
    if campaign_id: query["campaign_id"] = campaign_id
    
    logs = await db.audit_logs.find(query, {"_id": 0}).sort("created_at", -1).to_list(limit)
    return logs

@audit_router.get("/actions")
async def get_audit_actions():
    """Get list of auditable actions"""
    return {
        "actions": [
            AuditAction.VIEW_TRANSCRIPT,
            AuditAction.VIEW_INSIGHT,
            AuditAction.EXPORT_DATA,
            AuditAction.REIDENTIFICATION_REQUEST,
            AuditAction.REIDENTIFICATION_APPROVE,
            AuditAction.REIDENTIFICATION_RESOLVE,
            AuditAction.CONSENT_GIVEN,
            AuditAction.CONSENT_REVOKED,
            AuditAction.DATA_DELETED,
            AuditAction.LOGIN
        ]
    }

@audit_router.get("/summary")
async def get_audit_summary(current_user: dict = Depends(get_current_user), days: int = 30):
    if current_user["role"] not in ["admin", "security_officer"]:
        raise HTTPException(status_code=403, detail="Sin permisos")
    
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    
    pipeline = [
        {"$match": {"created_at": {"$gte": cutoff}}},
        {"$group": {"_id": "$action", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    
    by_action = await db.audit_logs.aggregate(pipeline).to_list(50)
    total = await db.audit_logs.count_documents({"created_at": {"$gte": cutoff}})
    
    return {
        "period_days": days,
        "total_events": total,
        "by_action": {item["_id"]: item["count"] for item in by_action}
    }

# ============== REIDENTIFICATION ROUTES (NEW - Phase 3.5) ==============

@reidentification_router.post("/request")
async def create_reidentification_request(
    req_data: ReidentificationRequestCreate,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Create a reidentification request (requires approval)"""
    if current_user["role"] not in ["admin", "facilitator", "security_officer"]:
        raise HTTPException(status_code=403, detail="Sin permisos para solicitar reidentificación")
    
    valid_reasons = [ReidentificationReason.SAFETY_CONCERN, ReidentificationReason.LEGAL_COMPLIANCE, 
                     ReidentificationReason.EXPLICIT_CONSENT, ReidentificationReason.DATA_CORRECTION]
    if req_data.reason_code not in valid_reasons:
        raise HTTPException(status_code=400, detail=f"Razón inválida. Use: {valid_reasons}")
    
    # Check pseudonym exists
    vault_entry = await db.pii_vault.find_one({"pseudonym_id": req_data.pseudonym_id, "is_deleted": False}, {"_id": 0})
    if not vault_entry:
        raise HTTPException(status_code=404, detail="Pseudónimo no encontrado")
    
    reident_req = ReidentificationRequest(
        tenant_id=vault_entry.get("tenant_id", "default"),
        pseudonym_id=req_data.pseudonym_id,
        reason_code=req_data.reason_code,
        justification=req_data.justification,
        campaign_id=req_data.campaign_id,
        requested_by=current_user["id"]
    )
    await db.reidentification_requests.insert_one(serialize_document(reident_req.model_dump()))
    
    # Audit
    await audit_service.log(
        user_id=current_user["id"], user_role=current_user["role"],
        action=AuditAction.REIDENTIFICATION_REQUEST, resource_type="reidentification",
        resource_id=reident_req.id,
        details={"pseudonym_id": req_data.pseudonym_id, "reason": req_data.reason_code}
    )
    
    return {"id": reident_req.id, "status": "pending", "message": "Solicitud creada, requiere aprobación de Data Steward"}

@reidentification_router.get("/pending")
async def get_pending_reidentification_requests(current_user: dict = Depends(get_current_user)):
    """Get pending requests (for Data Steward/Admin)"""
    if current_user["role"] not in ["admin", "data_steward", "security_officer"]:
        raise HTTPException(status_code=403, detail="Sin permisos")
    
    requests = await db.reidentification_requests.find({"status": "pending"}, {"_id": 0}).to_list(50)
    return requests

@reidentification_router.post("/{request_id}/review")
async def review_reidentification_request(
    request_id: str,
    approved: bool,
    notes: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Approve or deny a reidentification request (Data Steward only)"""
    if current_user["role"] not in ["admin", "data_steward"]:
        raise HTTPException(status_code=403, detail="Solo Data Steward puede aprobar")
    
    req = await db.reidentification_requests.find_one({"id": request_id}, {"_id": 0})
    if not req:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    
    if req.get("status") != "pending":
        raise HTTPException(status_code=400, detail="Solicitud ya procesada")
    
    # Cannot approve own request (dual control)
    if req.get("requested_by") == current_user["id"]:
        raise HTTPException(status_code=403, detail="No puede aprobar su propia solicitud (control dual)")
    
    status = "approved" if approved else "denied"
    await db.reidentification_requests.update_one(
        {"id": request_id},
        {"$set": {
            "status": status,
            "reviewed_by": current_user["id"],
            "reviewed_at": datetime.now(timezone.utc).isoformat(),
            "review_notes": notes
        }}
    )
    
    # Audit
    await audit_service.log(
        user_id=current_user["id"], user_role=current_user["role"],
        action=AuditAction.REIDENTIFICATION_APPROVE, resource_type="reidentification",
        resource_id=request_id,
        details={"approved": approved, "notes": notes}
    )
    
    return {"status": status, "message": f"Solicitud {status}"}

@reidentification_router.post("/{request_id}/resolve")
async def resolve_reidentification(request_id: str, current_user: dict = Depends(get_current_user)):
    """Resolve an approved reidentification request"""
    if current_user["role"] not in ["admin", "security_officer"]:
        raise HTTPException(status_code=403, detail="Sin permisos")
    
    req = await db.reidentification_requests.find_one({"id": request_id}, {"_id": 0})
    if not req:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    
    if req.get("status") != "approved":
        raise HTTPException(status_code=400, detail="Solicitud no aprobada")
    
    # Check expiration
    if req.get("expires_at") and req["expires_at"] < datetime.now(timezone.utc).isoformat():
        await db.reidentification_requests.update_one({"id": request_id}, {"$set": {"status": "expired"}})
        raise HTTPException(status_code=400, detail="Solicitud expirada")
    
    # Resolve identity
    tenant_id = req.get("tenant_id", "default")
    user_id = await pii_vault_service.resolve_identity(req["pseudonym_id"], tenant_id, current_user["id"])
    
    if not user_id:
        raise HTTPException(status_code=404, detail="No se pudo resolver identidad")
    
    # Get user info
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "hashed_password": 0})
    
    # Audit
    await audit_service.log(
        user_id=current_user["id"], user_role=current_user["role"],
        action=AuditAction.REIDENTIFICATION_RESOLVE, resource_type="reidentification",
        resource_id=request_id,
        details={"pseudonym_id": req["pseudonym_id"], "resolved": True}
    )
    
    # Return identity (NOT persisted in response)
    return {
        "request_id": request_id,
        "pseudonym_id": req["pseudonym_id"],
        "resolved_user": {
            "id": user.get("id"),
            "full_name": user.get("full_name"),
            "email": user.get("email"),
            "department": user.get("department")
        } if user else None,
        "warning": "Esta información NO debe ser persistida ni compartida"
    }

# ============== PRIVACY ROUTES (NEW - Phase 3.5) ==============

@privacy_router.post("/suppress/{campaign_id}")
async def trigger_suppression_check(campaign_id: str, current_user: dict = Depends(get_current_user)):
    """Trigger small group suppression check for a campaign"""
    if current_user["role"] not in ["admin", "facilitator"]:
        raise HTTPException(status_code=403, detail="Sin permisos")
    
    result = await suppression_service.check_and_suppress_insights(campaign_id)
    return result

@privacy_router.get("/suppression-status/{campaign_id}")
async def get_suppression_status(campaign_id: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["admin", "facilitator", "analyst"]:
        raise HTTPException(status_code=403, detail="Sin permisos")
    
    total = await db.insights.count_documents({"campaign_id": campaign_id})
    suppressed = await db.insights.count_documents({"campaign_id": campaign_id, "is_suppressed": True})
    
    return {
        "campaign_id": campaign_id,
        "total_insights": total,
        "suppressed_insights": suppressed,
        "visible_insights": total - suppressed,
        "threshold": SMALL_GROUP_THRESHOLD
    }

@privacy_router.get("/pii-scan/{transcript_id}")
async def scan_transcript_for_pii(transcript_id: str, current_user: dict = Depends(get_current_user)):
    """Scan a transcript for potential PII (for review before export)"""
    if current_user["role"] not in ["admin", "facilitator"]:
        raise HTTPException(status_code=403, detail="Sin permisos")
    
    transcript = await db.transcripts.find_one({"id": transcript_id}, {"_id": 0})
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcripción no encontrada")
    
    # Scan all messages
    findings = []
    for i, msg in enumerate(transcript.get("messages", [])):
        if msg.get("role") == "user":
            _, redactions = pseudonymization_service.pseudonymize_text(msg.get("content", ""), "scan")
            if redactions:
                findings.append({"message_index": i, "pii_types": [r["type"] for r in redactions]})
    
    return {
        "transcript_id": transcript_id,
        "is_pseudonymized": transcript.get("is_pseudonymized", False),
        "pii_findings": findings,
        "has_pii": len(findings) > 0,
        "recommendation": "Pseudonimizar antes de exportar" if findings else "Seguro para exportar"
    }

# ============== RUNAMAP NETWORK ROUTES (Phase 4) ==============

@network_router.post("/generate")
async def generate_network(
    request_data: GenerateNetworkRequest,
    current_user: dict = Depends(get_current_user)
):
    """Generate network graph from campaign data"""
    if current_user["role"] not in ["admin", "facilitator", "analyst"]:
        raise HTTPException(status_code=403, detail="Sin permisos para análisis de red")
    
    campaign = await db.campaigns.find_one({"id": request_data.campaign_id}, {"_id": 0})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaña no encontrada")
    
    tenant_id = campaign.get("tenant_id", "default")
    
    # Build graph
    nodes, edges = await network_analysis_service.build_graph_from_campaign(
        campaign_id=request_data.campaign_id,
        tenant_id=tenant_id,
        include_participant_theme=request_data.include_participant_theme,
        include_theme_cooccurrence=request_data.include_theme_cooccurrence,
        include_participant_similarity=request_data.include_participant_similarity,
        min_edge_weight=request_data.min_edge_weight
    )
    
    # Calculate metrics
    metrics = network_analysis_service.calculate_metrics(nodes, edges)
    
    # Save snapshot if name provided
    snapshot_id = None
    if request_data.snapshot_name:
        snapshot_id = await network_analysis_service.save_snapshot(
            campaign_id=request_data.campaign_id,
            tenant_id=tenant_id,
            nodes=nodes,
            edges=edges,
            metrics=metrics,
            name=request_data.snapshot_name,
            created_by=current_user["id"]
        )
    
    return GraphResponse(
        nodes=nodes,
        edges=edges,
        metrics=NetworkMetrics(**metrics),
        snapshot_id=snapshot_id
    )

@network_router.get("/campaign/{campaign_id}")
async def get_campaign_network(
    campaign_id: str,
    include_participant_theme: bool = True,
    include_theme_cooccurrence: bool = True,
    include_participant_similarity: bool = True,
    min_edge_weight: float = 1.0,
    current_user: dict = Depends(get_current_user)
):
    """Get network graph for a campaign (without saving snapshot)"""
    if current_user["role"] not in ["admin", "facilitator", "analyst"]:
        raise HTTPException(status_code=403, detail="Sin permisos para análisis de red")
    
    campaign = await db.campaigns.find_one({"id": campaign_id}, {"_id": 0})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaña no encontrada")
    
    tenant_id = campaign.get("tenant_id", "default")
    
    nodes, edges = await network_analysis_service.build_graph_from_campaign(
        campaign_id=campaign_id,
        tenant_id=tenant_id,
        include_participant_theme=include_participant_theme,
        include_theme_cooccurrence=include_theme_cooccurrence,
        include_participant_similarity=include_participant_similarity,
        min_edge_weight=min_edge_weight
    )
    
    metrics = network_analysis_service.calculate_metrics(nodes, edges)
    
    return GraphResponse(
        nodes=nodes,
        edges=edges,
        metrics=NetworkMetrics(**metrics)
    )

@network_router.get("/snapshots/{campaign_id}")
async def list_network_snapshots(
    campaign_id: str,
    current_user: dict = Depends(get_current_user)
):
    """List all network snapshots for a campaign"""
    if current_user["role"] not in ["admin", "facilitator", "analyst"]:
        raise HTTPException(status_code=403, detail="Sin permisos")
    
    snapshots = await db.network_snapshots.find(
        {"campaign_id": campaign_id},
        {"_id": 0}
    ).sort("created_at", -1).to_list(50)
    
    return snapshots

@network_router.get("/snapshot/{snapshot_id}")
async def get_network_snapshot(
    snapshot_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get a specific network snapshot with its nodes and edges"""
    if current_user["role"] not in ["admin", "facilitator", "analyst"]:
        raise HTTPException(status_code=403, detail="Sin permisos")
    
    snapshot = await db.network_snapshots.find_one({"id": snapshot_id}, {"_id": 0})
    if not snapshot:
        raise HTTPException(status_code=404, detail="Snapshot no encontrado")
    
    nodes = await db.network_nodes.find({"snapshot_id": snapshot_id}, {"_id": 0}).to_list(1000)
    edges = await db.network_edges.find({"snapshot_id": snapshot_id}, {"_id": 0}).to_list(5000)
    
    return {
        "snapshot": snapshot,
        "nodes": nodes,
        "edges": edges
    }

@network_router.get("/metrics/{campaign_id}")
async def get_network_metrics(
    campaign_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get network metrics summary for a campaign"""
    if current_user["role"] not in ["admin", "facilitator", "analyst"]:
        raise HTTPException(status_code=403, detail="Sin permisos")
    
    campaign = await db.campaigns.find_one({"id": campaign_id}, {"_id": 0})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaña no encontrada")
    
    tenant_id = campaign.get("tenant_id", "default")
    
    nodes, edges = await network_analysis_service.build_graph_from_campaign(
        campaign_id=campaign_id,
        tenant_id=tenant_id
    )
    
    metrics = network_analysis_service.calculate_metrics(nodes, edges)
    
    return NetworkMetrics(**metrics)

@network_router.get("/brokers/{campaign_id}")
async def get_network_brokers(
    campaign_id: str,
    limit: int = 10,
    node_type: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get top brokers (high betweenness centrality nodes) for a campaign"""
    if current_user["role"] not in ["admin", "facilitator", "analyst"]:
        raise HTTPException(status_code=403, detail="Sin permisos")
    
    campaign = await db.campaigns.find_one({"id": campaign_id}, {"_id": 0})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaña no encontrada")
    
    tenant_id = campaign.get("tenant_id", "default")
    
    nodes, edges = await network_analysis_service.build_graph_from_campaign(
        campaign_id=campaign_id,
        tenant_id=tenant_id
    )
    
    metrics = network_analysis_service.calculate_metrics(nodes, edges)
    
    brokers = metrics.get("top_brokers", [])
    if node_type:
        brokers = [b for b in brokers if b.get("node_type") == node_type]
    
    return brokers[:limit]

@network_router.get("/communities/{campaign_id}")
async def get_network_communities(
    campaign_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get detected communities for a campaign"""
    if current_user["role"] not in ["admin", "facilitator", "analyst"]:
        raise HTTPException(status_code=403, detail="Sin permisos")
    
    campaign = await db.campaigns.find_one({"id": campaign_id}, {"_id": 0})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaña no encontrada")
    
    tenant_id = campaign.get("tenant_id", "default")
    
    nodes, edges = await network_analysis_service.build_graph_from_campaign(
        campaign_id=campaign_id,
        tenant_id=tenant_id
    )
    
    metrics = network_analysis_service.calculate_metrics(nodes, edges)
    
    return {
        "num_communities": metrics.get("num_communities", 0),
        "communities": metrics.get("communities", []),
        "avg_clustering": metrics.get("avg_clustering", 0)
    }

@network_router.delete("/snapshot/{snapshot_id}")
async def delete_network_snapshot(
    snapshot_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a network snapshot"""
    if current_user["role"] not in ["admin"]:
        raise HTTPException(status_code=403, detail="Solo admin puede eliminar snapshots")
    
    snapshot = await db.network_snapshots.find_one({"id": snapshot_id}, {"_id": 0})
    if not snapshot:
        raise HTTPException(status_code=404, detail="Snapshot no encontrado")
    
    await db.network_nodes.delete_many({"snapshot_id": snapshot_id})
    await db.network_edges.delete_many({"snapshot_id": snapshot_id})
    await db.network_snapshots.delete_one({"id": snapshot_id})
    
    return {"message": "Snapshot eliminado", "id": snapshot_id}

@network_router.get("/initiative-leaders/{campaign_id}")
async def get_initiative_leaders_for_network(
    campaign_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get initiative leaders for network visualization"""
    if current_user["role"] not in ["admin", "facilitator", "analyst"]:
        raise HTTPException(status_code=403, detail="Sin permisos")
    
    leaders = await initiative_service.get_initiative_leaders(campaign_id)
    return leaders

# ============== RUNAFLOW INITIATIVE ROUTES (Phase 5) ==============

@initiative_router.post("/", response_model=Initiative)
async def create_initiative(
    data: InitiativeCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a new initiative"""
    if current_user["role"] not in ["admin", "facilitator", "sponsor"]:
        raise HTTPException(status_code=403, detail="Sin permisos para crear iniciativas")
    
    campaign = await db.campaigns.find_one({"id": data.campaign_id}, {"_id": 0})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaña no encontrada")
    
    # Get assigned user name
    assigned_name = None
    if data.assigned_to:
        assigned_user = await db.users.find_one({"id": data.assigned_to}, {"_id": 0})
        if assigned_user:
            assigned_name = assigned_user.get("full_name")
    
    initiative = Initiative(
        tenant_id=campaign.get("tenant_id", "default"),
        campaign_id=data.campaign_id,
        title=data.title,
        description=data.description,
        source_insight_ids=data.source_insight_ids,
        source_community_id=data.source_community_id,
        assigned_to=data.assigned_to,
        assigned_to_name=assigned_name,
        created_by=current_user["id"],
        scoring_method=data.scoring_method,
        impact_score=data.impact_score,
        confidence_score=data.confidence_score,
        ease_score=data.ease_score,
        reach_score=data.reach_score,
        effort_score=data.effort_score,
        tags=data.tags,
        due_date=data.due_date.isoformat() if data.due_date else None
    )
    
    # Calculate score
    initiative.final_score = initiative_service.calculate_score(initiative.model_dump())
    
    await db.initiatives.insert_one(serialize_document(initiative.model_dump()))
    return initiative

@initiative_router.get("/campaign/{campaign_id}")
async def list_initiatives(
    campaign_id: str,
    status: Optional[str] = None,
    assigned_to: Optional[str] = None,
    sort_by: str = "final_score",
    current_user: dict = Depends(get_current_user)
):
    """List initiatives for a campaign"""
    if current_user["role"] not in ["admin", "facilitator", "analyst", "sponsor"]:
        raise HTTPException(status_code=403, detail="Sin permisos")
    
    query = {"campaign_id": campaign_id}
    if status:
        query["status"] = status
    if assigned_to:
        query["assigned_to"] = assigned_to
    
    sort_field = "final_score" if sort_by == "final_score" else "created_at"
    sort_dir = -1
    
    initiatives = await db.initiatives.find(query, {"_id": 0}).sort(sort_field, sort_dir).to_list(200)
    return initiatives

@initiative_router.get("/stats/{campaign_id}")
async def get_initiative_stats(
    campaign_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get initiative statistics for a campaign"""
    if current_user["role"] not in ["admin", "facilitator", "analyst", "sponsor"]:
        raise HTTPException(status_code=403, detail="Sin permisos")
    
    initiatives = await db.initiatives.find({"campaign_id": campaign_id}, {"_id": 0}).to_list(500)
    
    stats = {
        "total": len(initiatives),
        "by_status": defaultdict(int),
        "avg_score": 0.0,
        "completion_rate": 0.0,
        "overdue_count": 0,
        "top_contributors": []
    }
    
    total_score = 0
    completed = 0
    contributor_count = defaultdict(int)
    now = datetime.now(timezone.utc)
    
    for init in initiatives:
        stats["by_status"][init.get("status", "backlog")] += 1
        total_score += init.get("final_score", 0)
        if init.get("status") == "completada":
            completed += 1
        if init.get("due_date"):
            try:
                due = datetime.fromisoformat(init["due_date"].replace("Z", "+00:00"))
                if due < now and init.get("status") not in ["completada", "cancelada"]:
                    stats["overdue_count"] += 1
            except:
                pass
        if init.get("assigned_to"):
            contributor_count[init["assigned_to"]] += 1
    
    stats["by_status"] = dict(stats["by_status"])
    stats["avg_score"] = round(total_score / len(initiatives), 2) if initiatives else 0
    stats["completion_rate"] = round(completed / len(initiatives) * 100, 1) if initiatives else 0
    
    # Top contributors
    for user_id, count in sorted(contributor_count.items(), key=lambda x: -x[1])[:5]:
        user = await db.users.find_one({"id": user_id}, {"_id": 0, "hashed_password": 0})
        if user:
            stats["top_contributors"].append({
                "user_id": user_id,
                "name": user.get("full_name"),
                "initiatives_count": count
            })
    
    return InitiativeStats(**stats)

@initiative_router.get("/{initiative_id}")
async def get_initiative(
    initiative_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get a single initiative"""
    initiative = await db.initiatives.find_one({"id": initiative_id}, {"_id": 0})
    if not initiative:
        raise HTTPException(status_code=404, detail="Iniciativa no encontrada")
    return initiative

@initiative_router.put("/{initiative_id}")
async def update_initiative(
    initiative_id: str,
    data: InitiativeUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update an initiative"""
    if current_user["role"] not in ["admin", "facilitator", "sponsor"]:
        raise HTTPException(status_code=403, detail="Sin permisos")
    
    initiative = await db.initiatives.find_one({"id": initiative_id}, {"_id": 0})
    if not initiative:
        raise HTTPException(status_code=404, detail="Iniciativa no encontrada")
    
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    
    # Handle status transitions
    if "status" in update_data:
        if update_data["status"] == "en_progreso" and initiative.get("status") != "en_progreso":
            update_data["started_at"] = datetime.now(timezone.utc).isoformat()
        elif update_data["status"] == "completada":
            update_data["completed_at"] = datetime.now(timezone.utc).isoformat()
            update_data["progress_percentage"] = 100
    
    # Update assigned user name
    if "assigned_to" in update_data and update_data["assigned_to"]:
        assigned_user = await db.users.find_one({"id": update_data["assigned_to"]}, {"_id": 0})
        if assigned_user:
            update_data["assigned_to_name"] = assigned_user.get("full_name")
    
    # Handle due_date
    if "due_date" in update_data and update_data["due_date"]:
        update_data["due_date"] = update_data["due_date"].isoformat()
    
    # Recalculate score if scoring fields changed
    merged = {**initiative, **update_data}
    update_data["final_score"] = initiative_service.calculate_score(merged)
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.initiatives.update_one({"id": initiative_id}, {"$set": update_data})
    return await db.initiatives.find_one({"id": initiative_id}, {"_id": 0})

@initiative_router.delete("/{initiative_id}")
async def delete_initiative(
    initiative_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete an initiative"""
    if current_user["role"] not in ["admin"]:
        raise HTTPException(status_code=403, detail="Solo admin puede eliminar")
    
    result = await db.initiatives.delete_one({"id": initiative_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Iniciativa no encontrada")
    
    await db.initiative_comments.delete_many({"initiative_id": initiative_id})
    return {"message": "Iniciativa eliminada", "id": initiative_id}

@initiative_router.post("/{initiative_id}/comments")
async def add_initiative_comment(
    initiative_id: str,
    content: str,
    current_user: dict = Depends(get_current_user)
):
    """Add a comment to an initiative"""
    initiative = await db.initiatives.find_one({"id": initiative_id}, {"_id": 0})
    if not initiative:
        raise HTTPException(status_code=404, detail="Iniciativa no encontrada")
    
    comment = InitiativeComment(
        initiative_id=initiative_id,
        user_id=current_user["id"],
        user_name=current_user.get("full_name", "Unknown"),
        content=content
    )
    
    await db.initiative_comments.insert_one(serialize_document(comment.model_dump()))
    await db.initiatives.update_one(
        {"id": initiative_id},
        {"$inc": {"comments_count": 1}}
    )
    
    return comment

@initiative_router.get("/{initiative_id}/comments")
async def get_initiative_comments(
    initiative_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get comments for an initiative"""
    comments = await db.initiative_comments.find(
        {"initiative_id": initiative_id},
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    return comments

# ============== RUNAFLOW RITUAL ROUTES (Phase 5) ==============

@ritual_router.post("/", response_model=Ritual)
async def create_ritual(
    data: RitualCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a new ritual"""
    if current_user["role"] not in ["admin", "facilitator"]:
        raise HTTPException(status_code=403, detail="Sin permisos para crear rituales")
    
    tenant_id = "default"
    if data.campaign_id:
        campaign = await db.campaigns.find_one({"id": data.campaign_id}, {"_id": 0})
        if campaign:
            tenant_id = campaign.get("tenant_id", "default")
    
    ritual = Ritual(
        tenant_id=tenant_id,
        campaign_id=data.campaign_id,
        name=data.name,
        description=data.description,
        ritual_type=data.ritual_type,
        day_of_week=data.day_of_week,
        day_of_month=data.day_of_month,
        time_of_day=data.time_of_day,
        duration_minutes=data.duration_minutes,
        participants=data.participants,
        agenda_template=data.agenda_template,
        is_active=data.is_active,
        created_by=current_user["id"]
    )
    
    # Calculate next occurrence
    next_occ = ritual_service.calculate_next_occurrence(ritual.model_dump())
    if next_occ:
        ritual.next_occurrence = next_occ.isoformat()
    
    await db.rituals.insert_one(serialize_document(ritual.model_dump()))
    return ritual

@ritual_router.get("/")
async def list_rituals(
    campaign_id: Optional[str] = None,
    ritual_type: Optional[str] = None,
    is_active: bool = True,
    current_user: dict = Depends(get_current_user)
):
    """List rituals"""
    if current_user["role"] not in ["admin", "facilitator", "analyst", "sponsor"]:
        raise HTTPException(status_code=403, detail="Sin permisos")
    
    query = {"is_active": is_active}
    if campaign_id:
        query["campaign_id"] = campaign_id
    if ritual_type:
        query["ritual_type"] = ritual_type
    
    rituals = await db.rituals.find(query, {"_id": 0}).sort("next_occurrence", 1).to_list(100)
    return rituals

@ritual_router.get("/{ritual_id}")
async def get_ritual(
    ritual_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get a single ritual"""
    ritual = await db.rituals.find_one({"id": ritual_id}, {"_id": 0})
    if not ritual:
        raise HTTPException(status_code=404, detail="Ritual no encontrado")
    return ritual

@ritual_router.put("/{ritual_id}")
async def update_ritual(
    ritual_id: str,
    data: RitualUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update a ritual"""
    if current_user["role"] not in ["admin", "facilitator"]:
        raise HTTPException(status_code=403, detail="Sin permisos")
    
    ritual = await db.rituals.find_one({"id": ritual_id}, {"_id": 0})
    if not ritual:
        raise HTTPException(status_code=404, detail="Ritual no encontrado")
    
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    # Recalculate next occurrence if schedule changed
    merged = {**ritual, **update_data}
    next_occ = ritual_service.calculate_next_occurrence(merged)
    if next_occ:
        update_data["next_occurrence"] = next_occ.isoformat()
    
    await db.rituals.update_one({"id": ritual_id}, {"$set": update_data})
    return await db.rituals.find_one({"id": ritual_id}, {"_id": 0})

@ritual_router.delete("/{ritual_id}")
async def delete_ritual(
    ritual_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a ritual"""
    if current_user["role"] not in ["admin"]:
        raise HTTPException(status_code=403, detail="Solo admin puede eliminar")
    
    result = await db.rituals.delete_one({"id": ritual_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Ritual no encontrado")
    
    return {"message": "Ritual eliminado", "id": ritual_id}

@ritual_router.post("/{ritual_id}/occurrence")
async def create_ritual_occurrence(
    ritual_id: str,
    scheduled_at: datetime,
    current_user: dict = Depends(get_current_user)
):
    """Create a new occurrence for a ritual"""
    if current_user["role"] not in ["admin", "facilitator"]:
        raise HTTPException(status_code=403, detail="Sin permisos")
    
    ritual = await db.rituals.find_one({"id": ritual_id}, {"_id": 0})
    if not ritual:
        raise HTTPException(status_code=404, detail="Ritual no encontrado")
    
    occurrence = RitualOccurrence(
        ritual_id=ritual_id,
        scheduled_at=scheduled_at.isoformat()
    )
    
    await db.ritual_occurrences.insert_one(serialize_document(occurrence.model_dump()))
    
    # Update ritual stats
    await db.rituals.update_one(
        {"id": ritual_id},
        {"$inc": {"occurrences_count": 1}}
    )
    
    return occurrence

@ritual_router.get("/{ritual_id}/occurrences")
async def get_ritual_occurrences(
    ritual_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get occurrences for a ritual"""
    occurrences = await db.ritual_occurrences.find(
        {"ritual_id": ritual_id},
        {"_id": 0}
    ).sort("scheduled_at", -1).to_list(50)
    return occurrences

@ritual_router.patch("/{ritual_id}/occurrence/{occurrence_id}")
async def update_ritual_occurrence(
    ritual_id: str,
    occurrence_id: str,
    status: Optional[str] = None,
    notes: Optional[str] = None,
    attendees: Optional[List[str]] = None,
    current_user: dict = Depends(get_current_user)
):
    """Update a ritual occurrence"""
    if current_user["role"] not in ["admin", "facilitator"]:
        raise HTTPException(status_code=403, detail="Sin permisos")
    
    update_data = {"updated_at": datetime.now(timezone.utc).isoformat()}
    if status:
        update_data["status"] = status
        if status == "in_progress":
            update_data["started_at"] = datetime.now(timezone.utc).isoformat()
        elif status == "completed":
            update_data["ended_at"] = datetime.now(timezone.utc).isoformat()
    if notes is not None:
        update_data["notes"] = notes
    if attendees is not None:
        update_data["attendees"] = attendees
    
    await db.ritual_occurrences.update_one(
        {"id": occurrence_id, "ritual_id": ritual_id},
        {"$set": update_data}
    )
    
    # Update ritual last_occurrence
    if status == "completed":
        await db.rituals.update_one(
            {"id": ritual_id},
            {"$set": {"last_occurrence": datetime.now(timezone.utc).isoformat()}}
        )
    
    return await db.ritual_occurrences.find_one({"id": occurrence_id}, {"_id": 0})

# ============== TENANT ROUTES ==============

@tenant_router.post("/", response_model=Tenant)
async def create_tenant(tenant_data: TenantCreate, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Solo admin")
    tenant = Tenant(**tenant_data.model_dump())
    await db.tenants.insert_one(serialize_document(tenant.model_dump()))
    return tenant

@tenant_router.get("/")
async def list_tenants(current_user: dict = Depends(get_current_user)):
    tenants = await db.tenants.find({}, {"_id": 0}).to_list(100)
    return tenants

# ============== SCRIPT ROUTES ==============

@script_router.post("/", response_model=Script)
async def create_script(script_data: ScriptCreate, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["admin", "facilitator"]:
        raise HTTPException(status_code=403, detail="Sin permisos")
    script = Script(tenant_id=current_user.get("tenant_id") or "default", name=script_data.name, description=script_data.description, objective=script_data.objective, steps=[s.model_dump() for s in script_data.steps], welcome_message=script_data.welcome_message, closing_message=script_data.closing_message, estimated_duration_minutes=script_data.estimated_duration_minutes, created_by=current_user["id"])
    await db.scripts.insert_one(serialize_document(script.model_dump()))
    return script

@script_router.get("/")
async def list_scripts(current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["admin", "facilitator"]:
        raise HTTPException(status_code=403, detail="Sin permisos")
    scripts = await db.scripts.find({"is_active": True}, {"_id": 0}).to_list(100)
    return scripts

@script_router.get("/{script_id}")
async def get_script(script_id: str, current_user: dict = Depends(get_current_user)):
    script = await db.scripts.find_one({"id": script_id}, {"_id": 0})
    if not script:
        raise HTTPException(status_code=404, detail="No encontrado")
    return script

@script_router.put("/{script_id}")
async def update_script(script_id: str, script_data: ScriptUpdate, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["admin", "facilitator"]:
        raise HTTPException(status_code=403, detail="Sin permisos")
    existing = await db.scripts.find_one({"id": script_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="No encontrado")
    new_version = existing.get("version", 1) + 1
    version_record = ScriptVersion(script_id=script_id, version=existing.get("version", 1), changes=f"v{new_version}", created_by=current_user["id"], snapshot=existing)
    await db.script_versions.insert_one(serialize_document(version_record.model_dump()))
    update_data = {k: v for k, v in script_data.model_dump().items() if v is not None}
    if "steps" in update_data:
        update_data["steps"] = [s.model_dump() if hasattr(s, 'model_dump') else s for s in update_data["steps"]]
    update_data["version"] = new_version
    await db.scripts.update_one({"id": script_id}, {"$set": update_data})
    return await db.scripts.find_one({"id": script_id}, {"_id": 0})

@script_router.post("/{script_id}/duplicate")
async def duplicate_script(script_id: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["admin", "facilitator"]:
        raise HTTPException(status_code=403, detail="Sin permisos")
    existing = await db.scripts.find_one({"id": script_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="No encontrado")
    new_script = Script(tenant_id=existing.get("tenant_id", "default"), name=f"{existing['name']} (Copia)", description=existing.get("description"), objective=existing.get("objective", ""), steps=existing.get("steps", []), welcome_message=existing.get("welcome_message"), closing_message=existing.get("closing_message"), estimated_duration_minutes=existing.get("estimated_duration_minutes", 15), created_by=current_user["id"], parent_id=script_id)
    await db.scripts.insert_one(serialize_document(new_script.model_dump()))
    return new_script

# ============== CAMPAIGN ROUTES ==============

@campaign_router.post("/", response_model=Campaign)
async def create_campaign(campaign_data: CampaignCreate, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["admin", "facilitator"]:
        raise HTTPException(status_code=403, detail="Sin permisos")
    campaign = Campaign(**campaign_data.model_dump(), tenant_id=current_user.get("tenant_id") or "default", created_by=current_user["id"])
    await db.campaigns.insert_one(serialize_document(campaign.model_dump()))
    return campaign

@campaign_router.get("/")
async def list_campaigns(current_user: dict = Depends(get_current_user), status: Optional[str] = None):
    query = {}
    if current_user["role"] == "participant":
        query["status"] = "active"
    elif status:
        query["status"] = status
    campaigns = await db.campaigns.find(query, {"_id": 0}).to_list(100)
    return campaigns

@campaign_router.get("/{campaign_id}")
async def get_campaign(campaign_id: str, current_user: dict = Depends(get_current_user)):
    campaign = await db.campaigns.find_one({"id": campaign_id}, {"_id": 0})
    if not campaign:
        raise HTTPException(status_code=404, detail="No encontrada")
    return campaign

@campaign_router.put("/{campaign_id}")
async def update_campaign(campaign_id: str, campaign_data: CampaignUpdate, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["admin", "facilitator"]:
        raise HTTPException(status_code=403, detail="Sin permisos")
    update_data = {k: v for k, v in campaign_data.model_dump().items() if v is not None}
    for key in ["start_date", "end_date"]:
        if key in update_data and update_data[key]:
            update_data[key] = update_data[key].isoformat()
    await db.campaigns.update_one({"id": campaign_id}, {"$set": update_data})
    return await db.campaigns.find_one({"id": campaign_id}, {"_id": 0})

@campaign_router.patch("/{campaign_id}/status")
async def update_campaign_status(campaign_id: str, status: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["admin", "facilitator"]:
        raise HTTPException(status_code=403, detail="Sin permisos")
    if status not in ["draft", "active", "paused", "closed"]:
        raise HTTPException(status_code=400, detail="Estado inválido")
    await db.campaigns.update_one({"id": campaign_id}, {"$set": {"status": status}})
    return {"message": "Estado actualizado", "status": status}

@campaign_router.get("/{campaign_id}/coverage")
async def get_campaign_coverage(campaign_id: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["admin", "facilitator", "analyst"]:
        raise HTTPException(status_code=403, detail="Sin permisos")
    total_invited = await db.invites.count_documents({"campaign_id": campaign_id})
    total_consented = await db.consents.count_documents({"campaign_id": campaign_id, "accepted": True, "revoked_at": None})
    total_sessions = await db.sessions.count_documents({"campaign_id": campaign_id})
    completed_sessions = await db.sessions.count_documents({"campaign_id": campaign_id, "status": "completed"})
    participation_rate = (total_consented / total_invited * 100) if total_invited > 0 else 0
    completion_rate = (completed_sessions / total_sessions * 100) if total_sessions > 0 else 0
    return CoverageStats(campaign_id=campaign_id, total_invited=total_invited, total_consented=total_consented, total_sessions=total_sessions, completed_sessions=completed_sessions, participation_rate=round(participation_rate, 1), completion_rate=round(completion_rate, 1))

# ============== TAXONOMY ROUTES ==============

@taxonomy_router.post("/")
async def create_category(category_data: TaxonomyCategoryCreate, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["admin", "facilitator"]:
        raise HTTPException(status_code=403, detail="Sin permisos")
    category = TaxonomyCategory(tenant_id=current_user.get("tenant_id") or "default", **category_data.model_dump())
    await db.taxonomy.insert_one(serialize_document(category.model_dump()))
    return category

@taxonomy_router.get("/")
async def list_categories(current_user: dict = Depends(get_current_user), type: Optional[str] = None):
    query = {"is_active": True}
    if type:
        query["type"] = type
    categories = await db.taxonomy.find(query, {"_id": 0}).to_list(200)
    return categories

@taxonomy_router.put("/{category_id}")
async def update_category(category_id: str, category_data: TaxonomyCategoryCreate, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["admin", "facilitator"]:
        raise HTTPException(status_code=403, detail="Sin permisos")
    await db.taxonomy.update_one({"id": category_id}, {"$set": category_data.model_dump()})
    return await db.taxonomy.find_one({"id": category_id}, {"_id": 0})

@taxonomy_router.delete("/{category_id}")
async def delete_category(category_id: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["admin", "facilitator"]:
        raise HTTPException(status_code=403, detail="Sin permisos")
    await db.taxonomy.update_one({"id": category_id}, {"$set": {"is_active": False}})
    return {"message": "Eliminada"}

# ============== INSIGHT ROUTES ==============

@insight_router.post("/")
async def create_insight(insight_data: InsightCreate, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["admin", "facilitator", "analyst"]:
        raise HTTPException(status_code=403, detail="Sin permisos")
    campaign = await db.campaigns.find_one({"id": insight_data.campaign_id}, {"_id": 0})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaña no encontrada")
    insight = Insight(tenant_id=campaign.get("tenant_id", "default"), campaign_id=insight_data.campaign_id, content=insight_data.content, type=insight_data.type, category_id=insight_data.category_id, source_session_id=insight_data.source_session_id, source_quote=insight_data.source_quote, sentiment=insight_data.sentiment, importance=insight_data.importance, extracted_by="manual")
    await db.insights.insert_one(serialize_document(insight.model_dump()))
    if insight_data.category_id:
        await db.taxonomy.update_one({"id": insight_data.category_id}, {"$inc": {"usage_count": 1}})
    return insight

@insight_router.get("/campaign/{campaign_id}")
async def list_campaign_insights(campaign_id: str, current_user: dict = Depends(get_current_user), type: Optional[str] = None, status: Optional[str] = None, sentiment: Optional[str] = None):
    if current_user["role"] not in ["admin", "facilitator", "analyst"]:
        raise HTTPException(status_code=403, detail="Sin permisos")
    
    # Use suppression service to get visible insights
    insights = await suppression_service.get_visible_insights(campaign_id, current_user["role"])
    
    # Apply additional filters
    if type:
        insights = [i for i in insights if i.get("type") == type]
    if status:
        insights = [i for i in insights if i.get("status") == status]
    if sentiment:
        insights = [i for i in insights if i.get("sentiment") == sentiment]
    
    # Sort by importance
    insights.sort(key=lambda x: x.get("importance", 0), reverse=True)
    
    return insights

@insight_router.get("/{insight_id}")
async def get_insight(insight_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    insight = await db.insights.find_one({"id": insight_id}, {"_id": 0})
    if not insight:
        raise HTTPException(status_code=404, detail="No encontrado")
    
    # Audit view
    await audit_service.log(
        user_id=current_user["id"], user_role=current_user["role"],
        action=AuditAction.VIEW_INSIGHT, resource_type="insight",
        resource_id=insight_id, campaign_id=insight.get("campaign_id")
    )
    
    return insight

@insight_router.put("/{insight_id}")
async def update_insight(insight_id: str, insight_data: InsightUpdate, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["admin", "facilitator", "analyst"]:
        raise HTTPException(status_code=403, detail="Sin permisos")
    update_data = {k: v for k, v in insight_data.model_dump().items() if v is not None}
    await db.insights.update_one({"id": insight_id}, {"$set": update_data})
    return await db.insights.find_one({"id": insight_id}, {"_id": 0})

@insight_router.patch("/{insight_id}/validate")
async def validate_insight(insight_id: str, validated: bool, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["admin", "facilitator", "analyst"]:
        raise HTTPException(status_code=403, detail="Sin permisos")
    status = "validated" if validated else "rejected"
    await db.insights.update_one({"id": insight_id}, {"$set": {"status": status, "validated_by": current_user["id"], "validated_at": datetime.now(timezone.utc).isoformat()}})
    return {"message": f"Insight {status}", "status": status}

@insight_router.get("/campaign/{campaign_id}/stats")
async def get_insight_stats(campaign_id: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["admin", "facilitator", "analyst"]:
        raise HTTPException(status_code=403, detail="Sin permisos")
    total = await db.insights.count_documents({"campaign_id": campaign_id})
    suppressed = await db.insights.count_documents({"campaign_id": campaign_id, "is_suppressed": True})
    by_type = {}
    for t in ["theme", "tension", "symbol", "opportunity", "risk"]:
        by_type[t] = await db.insights.count_documents({"campaign_id": campaign_id, "type": t})
    by_status = {}
    for s in ["draft", "validated", "rejected", "needs_review"]:
        by_status[s] = await db.insights.count_documents({"campaign_id": campaign_id, "status": s})
    by_sentiment = {}
    for sent in ["positive", "negative", "neutral", "mixed"]:
        by_sentiment[sent] = await db.insights.count_documents({"campaign_id": campaign_id, "sentiment": sent})
    return InsightStats(campaign_id=campaign_id, total_insights=total, by_type=by_type, by_status=by_status, by_sentiment=by_sentiment, suppressed_count=suppressed)

@insight_router.post("/campaign/{campaign_id}/extract")
async def extract_insights(campaign_id: str, background_tasks: BackgroundTasks, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["admin", "facilitator"]:
        raise HTTPException(status_code=403, detail="Sin permisos")
    campaign = await db.campaigns.find_one({"id": campaign_id}, {"_id": 0})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaña no encontrada")
    transcripts = await db.transcripts.find({"campaign_id": campaign_id, "insights_extracted": {"$ne": True}}, {"_id": 0}).to_list(100)
    if not transcripts:
        return {"message": "No hay transcripciones pendientes", "processed": 0}
    
    async def process_transcripts():
        for t in transcripts:
            await pseudonymization_service.pseudonymize_transcript(t["id"])
            await insight_extraction_service.extract_insights_from_transcript(t["id"], campaign_id, campaign.get("tenant_id", "default"))
        # Trigger suppression check after extraction
        await suppression_service.check_and_suppress_insights(campaign_id)
    
    background_tasks.add_task(process_transcripts)
    return {"message": f"Procesando {len(transcripts)} transcripciones", "queued": len(transcripts)}

# ============== INVITE ROUTES ==============

@invite_router.post("/")
async def create_invite(invite_data: InviteCreate, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["admin", "facilitator"]:
        raise HTTPException(status_code=403, detail="Sin permisos")
    campaign = await db.campaigns.find_one({"id": invite_data.campaign_id}, {"_id": 0})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaña no encontrada")
    invite = Invite(campaign_id=invite_data.campaign_id, tenant_id=campaign.get("tenant_id", "default"), user_id=invite_data.user_id, email=invite_data.email, segment_id=invite_data.segment_id, message=invite_data.message, invited_by=current_user["id"], status="sent", sent_at=datetime.now(timezone.utc))
    await db.invites.insert_one(serialize_document(invite.model_dump()))
    await db.campaigns.update_one({"id": invite_data.campaign_id}, {"$inc": {"invite_count": 1}})
    return invite

@invite_router.post("/bulk")
async def create_bulk_invites(invite_data: InviteBulk, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["admin", "facilitator"]:
        raise HTTPException(status_code=403, detail="Sin permisos")
    campaign = await db.campaigns.find_one({"id": invite_data.campaign_id}, {"_id": 0})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaña no encontrada")
    created = 0
    for user_id in invite_data.user_ids:
        invite = Invite(campaign_id=invite_data.campaign_id, tenant_id=campaign.get("tenant_id", "default"), user_id=user_id, segment_id=invite_data.segment_id, message=invite_data.message, invited_by=current_user["id"], status="sent", sent_at=datetime.now(timezone.utc))
        await db.invites.insert_one(serialize_document(invite.model_dump()))
        created += 1
    for email in invite_data.emails:
        invite = Invite(campaign_id=invite_data.campaign_id, tenant_id=campaign.get("tenant_id", "default"), email=email, segment_id=invite_data.segment_id, message=invite_data.message, invited_by=current_user["id"], status="sent", sent_at=datetime.now(timezone.utc))
        await db.invites.insert_one(serialize_document(invite.model_dump()))
        created += 1
    if created > 0:
        await db.campaigns.update_one({"id": invite_data.campaign_id}, {"$inc": {"invite_count": created}})
    return {"message": "Invitaciones procesadas", "created": created}

@invite_router.get("/campaign/{campaign_id}")
async def list_campaign_invites(campaign_id: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["admin", "facilitator"]:
        raise HTTPException(status_code=403, detail="Sin permisos")
    invites = await db.invites.find({"campaign_id": campaign_id}, {"_id": 0}).to_list(500)
    return invites

# ============== SESSION ROUTES ==============

@session_router.post("/")
async def create_session(session_data: SessionCreate, current_user: dict = Depends(get_current_user)):
    consent = await db.consents.find_one({"user_id": current_user["id"], "campaign_id": session_data.campaign_id, "accepted": True, "revoked_at": None})
    if not consent:
        raise HTTPException(status_code=403, detail="Debe aceptar el consentimiento")
    campaign = await db.campaigns.find_one({"id": session_data.campaign_id}, {"_id": 0})
    if not campaign or campaign.get("status") != "active":
        raise HTTPException(status_code=400, detail="Campaña no activa")
    session = Session(user_id=current_user["id"], campaign_id=session_data.campaign_id, tenant_id=campaign.get("tenant_id", "default"), status="in_progress", started_at=datetime.now(timezone.utc), script_id=campaign.get("script_id"))
    await db.sessions.insert_one(serialize_document(session.model_dump()))
    transcript = Transcript(session_id=session.id, campaign_id=session_data.campaign_id, tenant_id=campaign.get("tenant_id", "default"), user_id=current_user["id"])
    await db.transcripts.insert_one(serialize_document(transcript.model_dump()))
    await db.campaigns.update_one({"id": session_data.campaign_id}, {"$inc": {"session_count": 1}})
    return session

@session_router.get("/")
async def list_sessions(current_user: dict = Depends(get_current_user)):
    query = {"user_id": current_user["id"]} if current_user["role"] == "participant" else {}
    sessions = await db.sessions.find(query, {"_id": 0}).to_list(100)
    return sessions

@session_router.post("/{session_id}/complete")
async def complete_session(session_id: str, current_user: dict = Depends(get_current_user)):
    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    if not session or session["user_id"] != current_user["id"]:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    await db.sessions.update_one({"id": session_id}, {"$set": {"status": "completed", "ended_at": datetime.now(timezone.utc).isoformat()}})
    await db.campaigns.update_one({"id": session["campaign_id"]}, {"$inc": {"completed_sessions": 1}})
    val_service.close_session(session_id)
    return {"message": "Sesión completada"}

# ============== CHAT ROUTES ==============

@chat_router.post("/message")
async def send_chat_message(chat_request: ChatRequest, current_user: dict = Depends(get_current_user)):
    session = await db.sessions.find_one({"id": chat_request.session_id}, {"_id": 0})
    if not session or session["user_id"] != current_user["id"] or session["status"] != "in_progress":
        raise HTTPException(status_code=400, detail="Sesión inválida")
    campaign = await db.campaigns.find_one({"id": session["campaign_id"]}, {"_id": 0})
    campaign_objective = campaign.get("objective", "") if campaign else ""
    script_context = ""
    if session.get("script_id"):
        script = await db.scripts.find_one({"id": session["script_id"]}, {"_id": 0})
        if script and script.get("steps"):
            steps_text = "\n".join([f"- {s.get('question', '')}" for s in script["steps"][:5]])
            script_context = f"\nGuión:\n{steps_text}"
    response = await val_service.send_message(chat_request.session_id, chat_request.message, campaign_objective, script_context)
    now = datetime.now(timezone.utc)
    await db.transcripts.update_one({"session_id": chat_request.session_id}, {"$push": {"messages": {"$each": [{"role": "user", "content": chat_request.message, "timestamp": now.isoformat()}, {"role": "assistant", "content": response, "timestamp": now.isoformat()}]}}})
    return ChatResponse(session_id=chat_request.session_id, message=response, timestamp=now)

@chat_router.get("/history/{session_id}")
async def get_chat_history(session_id: str, current_user: dict = Depends(get_current_user)):
    transcript = await db.transcripts.find_one({"session_id": session_id}, {"_id": 0})
    return {"messages": transcript.get("messages", []) if transcript else []}

# ============== TRANSCRIPT ROUTES ==============

@transcript_router.get("/campaign/{campaign_id}")
async def list_campaign_transcripts(campaign_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    # Transcripts are sensitive - check role carefully
    if current_user["role"] not in ["admin", "security_officer"]:
        raise HTTPException(status_code=403, detail="Transcripciones solo visibles para admin/security_officer")
    
    transcripts = await db.transcripts.find({"campaign_id": campaign_id}, {"_id": 0, "messages": 0}).to_list(500)
    
    # Audit
    await audit_service.log(
        user_id=current_user["id"], user_role=current_user["role"],
        action=AuditAction.VIEW_TRANSCRIPT, resource_type="transcript_list",
        campaign_id=campaign_id, details={"count": len(transcripts)}
    )
    
    return transcripts

@transcript_router.get("/{transcript_id}")
async def get_transcript(transcript_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["admin", "security_officer"]:
        raise HTTPException(status_code=403, detail="Sin permisos")
    transcript = await db.transcripts.find_one({"id": transcript_id}, {"_id": 0})
    if not transcript:
        raise HTTPException(status_code=404, detail="No encontrada")
    
    # Audit
    await audit_service.log(
        user_id=current_user["id"], user_role=current_user["role"],
        action=AuditAction.VIEW_TRANSCRIPT, resource_type="transcript",
        resource_id=transcript_id, campaign_id=transcript.get("campaign_id")
    )
    
    return transcript

@transcript_router.post("/{transcript_id}/pseudonymize")
async def pseudonymize_transcript_endpoint(transcript_id: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["admin", "facilitator"]:
        raise HTTPException(status_code=403, detail="Sin permisos")
    result = await pseudonymization_service.pseudonymize_transcript(transcript_id)
    return result

# ============== VALIDATION ROUTES ==============

@api_router.post("/validations/")
async def create_validation_request(val_data: ValidationRequestCreate, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["admin", "facilitator"]:
        raise HTTPException(status_code=403, detail="Sin permisos")
    insight = await db.insights.find_one({"id": val_data.insight_id}, {"_id": 0})
    if not insight:
        raise HTTPException(status_code=404, detail="Insight no encontrado")
    consents = await db.consents.find({"campaign_id": insight["campaign_id"], "accepted": True, "revoked_at": None}, {"_id": 0}).to_list(10)
    if not consents:
        raise HTTPException(status_code=400, detail="No hay participantes disponibles")
    created = []
    for consent in consents[:3]:
        validation = ValidationRequest(insight_id=val_data.insight_id, campaign_id=insight["campaign_id"], tenant_id=insight.get("tenant_id", "default"), user_id=consent["user_id"])
        await db.validations.insert_one(serialize_document(validation.model_dump()))
        created.append(validation)
    await db.insights.update_one({"id": val_data.insight_id}, {"$set": {"status": "needs_review"}})
    return created[0] if created else None

@api_router.get("/validations/pending")
async def get_pending_validations(current_user: dict = Depends(get_current_user)):
    validations = await db.validations.find({"user_id": current_user["id"], "status": "pending"}, {"_id": 0}).to_list(50)
    enriched = []
    for v in validations:
        insight = await db.insights.find_one({"id": v["insight_id"]}, {"_id": 0})
        if insight:
            enriched.append({**v, "insight": insight})
    return enriched

@api_router.post("/validations/{validation_id}/respond")
async def respond_validation(validation_id: str, response: ValidationResponse, current_user: dict = Depends(get_current_user)):
    validation = await db.validations.find_one({"id": validation_id}, {"_id": 0})
    if not validation or validation["user_id"] != current_user["id"]:
        raise HTTPException(status_code=404, detail="No encontrada")
    status = "validated" if response.validated else "rejected"
    await db.validations.update_one({"id": validation_id}, {"$set": {"status": status, "response": response.comment, "responded_at": datetime.now(timezone.utc).isoformat()}})
    all_validations = await db.validations.find({"insight_id": validation["insight_id"]}, {"_id": 0}).to_list(10)
    validated_count = sum(1 for v in all_validations if v.get("status") == "validated")
    rejected_count = sum(1 for v in all_validations if v.get("status") == "rejected")
    if validated_count >= 2:
        await db.insights.update_one({"id": validation["insight_id"]}, {"$set": {"status": "validated"}})
    elif rejected_count >= 2:
        await db.insights.update_one({"id": validation["insight_id"]}, {"$set": {"status": "rejected"}})
    return {"message": "Respuesta registrada", "status": status}

# ============== DASHBOARD ==============

@api_router.get("/dashboard/stats")
async def get_dashboard_stats(current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["admin", "facilitator", "analyst"]:
        raise HTTPException(status_code=403, detail="Sin permisos")
    return {
        "campaigns": {"total": await db.campaigns.count_documents({}), "active": await db.campaigns.count_documents({"status": "active"})},
        "sessions": {"total": await db.sessions.count_documents({}), "completed": await db.sessions.count_documents({"status": "completed"})},
        "users": await db.users.count_documents({}),
        "active_consents": await db.consents.count_documents({"accepted": True, "revoked_at": None}),
        "scripts": await db.scripts.count_documents({"is_active": True}),
        "invites": await db.invites.count_documents({}),
        "insights": await db.insights.count_documents({}),
        "audit_events_24h": await db.audit_logs.count_documents({"created_at": {"$gte": (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()}})
    }

# ============== HEALTH ==============

@api_router.get("/")
async def root():
    return {"message": "DigiKawsay API v0.3.5", "status": "healthy", "compliance": "Phase 3.5"}

@api_router.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}

# ============== INCLUDE ROUTERS ==============

api_router.include_router(auth_router)
api_router.include_router(tenant_router)
api_router.include_router(user_router)
api_router.include_router(campaign_router)
api_router.include_router(script_router)
api_router.include_router(segment_router)
api_router.include_router(invite_router)
api_router.include_router(session_router)
api_router.include_router(consent_router)
api_router.include_router(chat_router)
api_router.include_router(insight_router)
api_router.include_router(taxonomy_router)
api_router.include_router(transcript_router)
api_router.include_router(audit_router)
api_router.include_router(privacy_router)
api_router.include_router(reidentification_router)
api_router.include_router(network_router)
api_router.include_router(initiative_router)
api_router.include_router(ritual_router)

app.include_router(api_router)

app.add_middleware(CORSMiddleware, allow_credentials=True, allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','), allow_methods=["*"], allow_headers=["*"])

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
