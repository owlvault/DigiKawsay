from fastapi import FastAPI, APIRouter, HTTPException, Depends, status, Query, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import re
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from emergentintegrations.llm.chat import LlmChat, UserMessage
import asyncio
import hashlib

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

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Security
security = HTTPBearer()

# Create the main app
app = FastAPI(title="DigiKawsay API", version="0.3.0")

# Create routers
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

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ============== PYDANTIC MODELS ==============

class TimestampMixin(BaseModel):
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# --- Tenant Models ---
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

# --- User Models ---
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

# --- Script Models ---
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

# --- Segment Models ---
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

# --- Invitation Models ---
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

# --- Campaign Models ---
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

# --- Consent Models ---
class ConsentCreate(BaseModel):
    campaign_id: str
    accepted: bool
    consent_text: Optional[str] = None

class Consent(TimestampMixin):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    campaign_id: str
    tenant_id: str
    accepted: bool
    consent_text: Optional[str] = None
    revoked_at: Optional[datetime] = None

# --- Session Models ---
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

# --- Chat Models ---
class ChatMessage(BaseModel):
    role: str
    content: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ChatRequest(BaseModel):
    session_id: str
    message: str

class ChatResponse(BaseModel):
    session_id: str
    message: str
    timestamp: datetime

# --- Transcript Models ---
class Transcript(TimestampMixin):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    campaign_id: str
    tenant_id: str
    user_id: str
    messages: List[Dict[str, Any]] = []
    is_pseudonymized: bool = False
    pseudonymized_at: Optional[datetime] = None
    insights_extracted: bool = False

# --- Taxonomy Models (NEW - Phase 3) ---
class TaxonomyCategoryCreate(BaseModel):
    name: str
    type: str  # theme, tension, symbol, opportunity, risk
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

# --- Insight Models (NEW - Phase 3) ---
class InsightCreate(BaseModel):
    campaign_id: str
    content: str
    type: str = "theme"  # theme, tension, symbol, opportunity, risk
    category_id: Optional[str] = None
    source_session_id: Optional[str] = None
    source_quote: Optional[str] = None
    sentiment: Optional[str] = None  # positive, negative, neutral, mixed
    importance: int = 5  # 1-10

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
    status: str = "draft"  # draft, validated, rejected, needs_review
    extracted_by: str = "ai"  # ai, manual
    validated_by: Optional[str] = None
    validated_at: Optional[datetime] = None
    occurrence_count: int = 1
    related_insights: List[str] = []

# --- Validation Models (NEW - Phase 3) ---
class ValidationRequestCreate(BaseModel):
    insight_id: str
    message: Optional[str] = None

class ValidationRequest(TimestampMixin):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    insight_id: str
    campaign_id: str
    tenant_id: str
    user_id: str  # participant to validate
    status: str = "pending"  # pending, validated, rejected, skipped
    response: Optional[str] = None
    responded_at: Optional[datetime] = None

class ValidationResponse(BaseModel):
    validated: bool
    comment: Optional[str] = None

# --- Coverage/Analytics Models ---
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
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
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

# ============== PSEUDONYMIZATION SERVICE (NEW - Phase 3) ==============

class PseudonymizationService:
    def __init__(self):
        self.name_patterns = [
            r'\b[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+\b',  # Full names
            r'\b(?:Sr\.|Sra\.|Dr\.|Dra\.|Ing\.)\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+\b',  # Titles
        ]
        self.email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        self.phone_pattern = r'\b(?:\+?[0-9]{1,3}[-.\s]?)?(?:\([0-9]{2,3}\)[-.\s]?)?[0-9]{3,4}[-.\s]?[0-9]{3,4}\b'
    
    def generate_pseudonym_hash(self, text: str, salt: str = "") -> str:
        hash_input = f"{text}{salt}".encode()
        return f"[PARTICIPANTE-{hashlib.sha256(hash_input).hexdigest()[:6].upper()}]"
    
    def pseudonymize_text(self, text: str, session_id: str = "") -> str:
        result = text
        
        # Replace emails
        for match in re.finditer(self.email_pattern, result):
            pseudo = self.generate_pseudonym_hash(match.group(), session_id)
            result = result.replace(match.group(), f"[EMAIL-{pseudo[-8:-1]}]")
        
        # Replace phone numbers
        for match in re.finditer(self.phone_pattern, result):
            result = result.replace(match.group(), "[TELÉFONO]")
        
        # Replace names (simplified - in production would use NER)
        for pattern in self.name_patterns:
            for match in re.finditer(pattern, result):
                pseudo = self.generate_pseudonym_hash(match.group(), session_id)
                result = result.replace(match.group(), pseudo)
        
        return result
    
    async def pseudonymize_transcript(self, transcript_id: str) -> bool:
        transcript = await db.transcripts.find_one({"id": transcript_id}, {"_id": 0})
        if not transcript or transcript.get("is_pseudonymized"):
            return False
        
        session_id = transcript.get("session_id", "")
        pseudonymized_messages = []
        
        for msg in transcript.get("messages", []):
            new_msg = msg.copy()
            if msg.get("role") == "user":
                new_msg["content"] = self.pseudonymize_text(msg.get("content", ""), session_id)
            pseudonymized_messages.append(new_msg)
        
        await db.transcripts.update_one(
            {"id": transcript_id},
            {
                "$set": {
                    "messages": pseudonymized_messages,
                    "is_pseudonymized": True,
                    "pseudonymized_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
            }
        )
        return True

pseudonymization_service = PseudonymizationService()

# ============== INSIGHT EXTRACTION SERVICE (NEW - Phase 3) ==============

class InsightExtractionService:
    def __init__(self):
        self.api_key = os.environ.get('EMERGENT_LLM_KEY')
    
    async def extract_insights_from_transcript(self, transcript_id: str, campaign_id: str, tenant_id: str) -> List[Dict]:
        transcript = await db.transcripts.find_one({"id": transcript_id}, {"_id": 0})
        if not transcript:
            return []
        
        # Get campaign objective for context
        campaign = await db.campaigns.find_one({"id": campaign_id}, {"_id": 0})
        objective = campaign.get("objective", "") if campaign else ""
        
        # Prepare conversation text
        conversation = "\n".join([
            f"{'Participante' if m['role'] == 'user' else 'VAL'}: {m['content']}"
            for m in transcript.get("messages", [])
        ])
        
        if not conversation:
            return []
        
        # Use LLM to extract insights
        extraction_prompt = f"""Analiza la siguiente conversación de una campaña de diagnóstico organizacional.
        
Objetivo de la campaña: {objective}

Conversación:
{conversation}

Extrae los insights más relevantes en formato JSON. Para cada insight incluye:
- content: descripción del hallazgo (máx 200 caracteres)
- type: uno de [theme, tension, symbol, opportunity, risk]
- sentiment: uno de [positive, negative, neutral, mixed]
- importance: número del 1 al 10
- source_quote: cita textual que respalda el insight (máx 150 caracteres)

Responde SOLO con un array JSON válido, sin explicaciones adicionales. Máximo 5 insights."""

        try:
            chat = LlmChat(
                api_key=self.api_key,
                session_id=f"extraction-{transcript_id}",
                system_message="Eres un experto en análisis cualitativo organizacional. Extraes insights de conversaciones de forma precisa y estructurada."
            )
            chat.with_model("gemini", "gemini-2.5-flash")
            
            response = await chat.send_message(UserMessage(text=extraction_prompt))
            
            # Parse JSON response
            import json
            # Clean response
            response_clean = response.strip()
            if response_clean.startswith("```json"):
                response_clean = response_clean[7:]
            if response_clean.startswith("```"):
                response_clean = response_clean[3:]
            if response_clean.endswith("```"):
                response_clean = response_clean[:-3]
            
            insights_data = json.loads(response_clean.strip())
            
            created_insights = []
            for data in insights_data:
                insight = Insight(
                    tenant_id=tenant_id,
                    campaign_id=campaign_id,
                    content=data.get("content", "")[:500],
                    type=data.get("type", "theme"),
                    sentiment=data.get("sentiment"),
                    importance=min(max(int(data.get("importance", 5)), 1), 10),
                    source_session_id=transcript.get("session_id"),
                    source_quote=data.get("source_quote", "")[:300],
                    extracted_by="ai"
                )
                doc = serialize_document(insight.model_dump())
                await db.insights.insert_one(doc)
                created_insights.append(insight.model_dump())
            
            # Mark transcript as processed
            await db.transcripts.update_one(
                {"id": transcript_id},
                {"$set": {"insights_extracted": True, "updated_at": datetime.now(timezone.utc).isoformat()}}
            )
            
            return created_insights
            
        except Exception as e:
            logger.error(f"Error extracting insights: {e}")
            return []

insight_extraction_service = InsightExtractionService()

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
            chat = LlmChat(
                api_key=self.api_key,
                session_id=session_id,
                system_message=self.get_system_prompt(campaign_objective, script_context)
            )
            chat.with_model("gemini", "gemini-2.5-flash")
            self.active_chats[session_id] = chat
        return self.active_chats[session_id]
    
    async def send_message(self, session_id: str, message: str, campaign_objective: str = "", script_context: str = "") -> str:
        chat = await self.get_or_create_chat(session_id, campaign_objective, script_context)
        user_message = UserMessage(text=message)
        response = await chat.send_message(user_message)
        return response
    
    def close_session(self, session_id: str):
        if session_id in self.active_chats:
            del self.active_chats[session_id]

val_service = VALChatService()

# ============== AUTH ROUTES ==============

@auth_router.post("/register", response_model=TokenResponse)
async def register(user_data: UserCreate):
    existing = await db.users.find_one({"email": user_data.email})
    if existing:
        raise HTTPException(status_code=400, detail="El email ya está registrado")
    
    user_dict = user_data.model_dump()
    password = user_dict.pop("password")
    user_obj = User(**user_dict)
    user_obj.pseudonym_id = generate_pseudonym()
    
    doc = user_obj.model_dump()
    doc["hashed_password"] = get_password_hash(password)
    doc = serialize_document(doc)
    
    await db.users.insert_one(doc)
    
    access_token = create_access_token(data={"sub": user_obj.id})
    return TokenResponse(
        access_token=access_token,
        user=UserResponse(**{k: v for k, v in user_obj.model_dump().items() if k in UserResponse.model_fields})
    )

@auth_router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin):
    user = await db.users.find_one({"email": credentials.email}, {"_id": 0})
    if not user or not verify_password(credentials.password, user.get("hashed_password", "")):
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
    
    access_token = create_access_token(data={"sub": user["id"]})
    return TokenResponse(
        access_token=access_token,
        user=UserResponse(**{k: user.get(k) for k in UserResponse.model_fields})
    )

@auth_router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    return UserResponse(**{k: current_user.get(k) for k in UserResponse.model_fields})

# ============== USER ROUTES ==============

@user_router.get("/", response_model=List[UserResponse])
async def list_users(current_user: dict = Depends(get_current_user), role: Optional[str] = None, department: Optional[str] = None):
    if current_user["role"] not in ["admin", "facilitator"]:
        raise HTTPException(status_code=403, detail="No tiene permisos")
    
    query = {}
    if role: query["role"] = role
    if department: query["department"] = department
    
    users = await db.users.find(query, {"_id": 0, "hashed_password": 0}).to_list(500)
    return [UserResponse(**{k: u.get(k) for k in UserResponse.model_fields}) for u in users]

# ============== TENANT ROUTES ==============

@tenant_router.post("/", response_model=Tenant)
async def create_tenant(tenant_data: TenantCreate, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Solo administradores pueden crear tenants")
    tenant = Tenant(**tenant_data.model_dump())
    await db.tenants.insert_one(serialize_document(tenant.model_dump()))
    return tenant

@tenant_router.get("/", response_model=List[Tenant])
async def list_tenants(current_user: dict = Depends(get_current_user)):
    tenants = await db.tenants.find({}, {"_id": 0}).to_list(100)
    return tenants

# ============== SCRIPT ROUTES ==============

@script_router.post("/", response_model=Script)
async def create_script(script_data: ScriptCreate, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["admin", "facilitator"]:
        raise HTTPException(status_code=403, detail="No tiene permisos")
    
    script = Script(
        tenant_id=current_user.get("tenant_id") or "default",
        name=script_data.name,
        description=script_data.description,
        objective=script_data.objective,
        steps=[s.model_dump() for s in script_data.steps],
        welcome_message=script_data.welcome_message,
        closing_message=script_data.closing_message,
        estimated_duration_minutes=script_data.estimated_duration_minutes,
        created_by=current_user["id"]
    )
    await db.scripts.insert_one(serialize_document(script.model_dump()))
    return script

@script_router.get("/", response_model=List[Script])
async def list_scripts(current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["admin", "facilitator"]:
        raise HTTPException(status_code=403, detail="No tiene permisos")
    scripts = await db.scripts.find({"is_active": True}, {"_id": 0}).to_list(100)
    return scripts

@script_router.get("/{script_id}", response_model=Script)
async def get_script(script_id: str, current_user: dict = Depends(get_current_user)):
    script = await db.scripts.find_one({"id": script_id}, {"_id": 0})
    if not script:
        raise HTTPException(status_code=404, detail="Guión no encontrado")
    return script

@script_router.put("/{script_id}", response_model=Script)
async def update_script(script_id: str, script_data: ScriptUpdate, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["admin", "facilitator"]:
        raise HTTPException(status_code=403, detail="No tiene permisos")
    
    existing = await db.scripts.find_one({"id": script_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Guión no encontrado")
    
    new_version = existing.get("version", 1) + 1
    version_record = ScriptVersion(script_id=script_id, version=existing.get("version", 1), changes=f"v{new_version}", created_by=current_user["id"], snapshot=existing)
    await db.script_versions.insert_one(serialize_document(version_record.model_dump()))
    
    update_data = {k: v for k, v in script_data.model_dump().items() if v is not None}
    if "steps" in update_data:
        update_data["steps"] = [s.model_dump() if hasattr(s, 'model_dump') else s for s in update_data["steps"]]
    update_data["version"] = new_version
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.scripts.update_one({"id": script_id}, {"$set": update_data})
    updated = await db.scripts.find_one({"id": script_id}, {"_id": 0})
    return updated

@script_router.post("/{script_id}/duplicate", response_model=Script)
async def duplicate_script(script_id: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["admin", "facilitator"]:
        raise HTTPException(status_code=403, detail="No tiene permisos")
    
    existing = await db.scripts.find_one({"id": script_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Guión no encontrado")
    
    new_script = Script(
        tenant_id=existing.get("tenant_id", "default"),
        name=f"{existing['name']} (Copia)",
        description=existing.get("description"),
        objective=existing.get("objective", ""),
        steps=existing.get("steps", []),
        welcome_message=existing.get("welcome_message"),
        closing_message=existing.get("closing_message"),
        estimated_duration_minutes=existing.get("estimated_duration_minutes", 15),
        created_by=current_user["id"],
        parent_id=script_id
    )
    await db.scripts.insert_one(serialize_document(new_script.model_dump()))
    return new_script

# ============== CAMPAIGN ROUTES ==============

@campaign_router.post("/", response_model=Campaign)
async def create_campaign(campaign_data: CampaignCreate, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["admin", "facilitator"]:
        raise HTTPException(status_code=403, detail="No tiene permisos")
    
    campaign = Campaign(**campaign_data.model_dump(), tenant_id=current_user.get("tenant_id") or "default", created_by=current_user["id"])
    await db.campaigns.insert_one(serialize_document(campaign.model_dump()))
    return campaign

@campaign_router.get("/", response_model=List[Campaign])
async def list_campaigns(current_user: dict = Depends(get_current_user), status: Optional[str] = None):
    query = {}
    if current_user["role"] == "participant":
        query["status"] = "active"
    elif status:
        query["status"] = status
    campaigns = await db.campaigns.find(query, {"_id": 0}).to_list(100)
    return campaigns

@campaign_router.get("/{campaign_id}", response_model=Campaign)
async def get_campaign(campaign_id: str, current_user: dict = Depends(get_current_user)):
    campaign = await db.campaigns.find_one({"id": campaign_id}, {"_id": 0})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaña no encontrada")
    return campaign

@campaign_router.put("/{campaign_id}", response_model=Campaign)
async def update_campaign(campaign_id: str, campaign_data: CampaignUpdate, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["admin", "facilitator"]:
        raise HTTPException(status_code=403, detail="No tiene permisos")
    
    update_data = {k: v for k, v in campaign_data.model_dump().items() if v is not None}
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    for key in ["start_date", "end_date"]:
        if key in update_data and update_data[key]:
            update_data[key] = update_data[key].isoformat()
    
    await db.campaigns.update_one({"id": campaign_id}, {"$set": update_data})
    updated = await db.campaigns.find_one({"id": campaign_id}, {"_id": 0})
    return updated

@campaign_router.patch("/{campaign_id}/status")
async def update_campaign_status(campaign_id: str, status: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["admin", "facilitator"]:
        raise HTTPException(status_code=403, detail="No tiene permisos")
    
    valid_statuses = ["draft", "active", "paused", "closed"]
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Estado inválido")
    
    await db.campaigns.update_one({"id": campaign_id}, {"$set": {"status": status, "updated_at": datetime.now(timezone.utc).isoformat()}})
    return {"message": "Estado actualizado", "status": status}

@campaign_router.get("/{campaign_id}/coverage", response_model=CoverageStats)
async def get_campaign_coverage(campaign_id: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["admin", "facilitator", "analyst"]:
        raise HTTPException(status_code=403, detail="No tiene permisos")
    
    total_invited = await db.invites.count_documents({"campaign_id": campaign_id})
    total_consented = await db.consents.count_documents({"campaign_id": campaign_id, "accepted": True, "revoked_at": None})
    total_sessions = await db.sessions.count_documents({"campaign_id": campaign_id})
    completed_sessions = await db.sessions.count_documents({"campaign_id": campaign_id, "status": "completed"})
    
    participation_rate = (total_consented / total_invited * 100) if total_invited > 0 else 0
    completion_rate = (completed_sessions / total_sessions * 100) if total_sessions > 0 else 0
    
    return CoverageStats(
        campaign_id=campaign_id,
        total_invited=total_invited,
        total_consented=total_consented,
        total_sessions=total_sessions,
        completed_sessions=completed_sessions,
        participation_rate=round(participation_rate, 1),
        completion_rate=round(completion_rate, 1)
    )

# ============== TAXONOMY ROUTES (NEW - Phase 3) ==============

@taxonomy_router.post("/", response_model=TaxonomyCategory)
async def create_category(category_data: TaxonomyCategoryCreate, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["admin", "facilitator"]:
        raise HTTPException(status_code=403, detail="No tiene permisos")
    
    category = TaxonomyCategory(tenant_id=current_user.get("tenant_id") or "default", **category_data.model_dump())
    await db.taxonomy.insert_one(serialize_document(category.model_dump()))
    return category

@taxonomy_router.get("/", response_model=List[TaxonomyCategory])
async def list_categories(current_user: dict = Depends(get_current_user), type: Optional[str] = None):
    query = {"is_active": True}
    if type:
        query["type"] = type
    categories = await db.taxonomy.find(query, {"_id": 0}).to_list(200)
    return categories

@taxonomy_router.put("/{category_id}", response_model=TaxonomyCategory)
async def update_category(category_id: str, category_data: TaxonomyCategoryCreate, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["admin", "facilitator"]:
        raise HTTPException(status_code=403, detail="No tiene permisos")
    
    update_data = category_data.model_dump()
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.taxonomy.update_one({"id": category_id}, {"$set": update_data})
    updated = await db.taxonomy.find_one({"id": category_id}, {"_id": 0})
    return updated

@taxonomy_router.delete("/{category_id}")
async def delete_category(category_id: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["admin", "facilitator"]:
        raise HTTPException(status_code=403, detail="No tiene permisos")
    await db.taxonomy.update_one({"id": category_id}, {"$set": {"is_active": False}})
    return {"message": "Categoría eliminada"}

# ============== INSIGHT ROUTES (NEW - Phase 3) ==============

@insight_router.post("/", response_model=Insight)
async def create_insight(insight_data: InsightCreate, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["admin", "facilitator", "analyst"]:
        raise HTTPException(status_code=403, detail="No tiene permisos")
    
    campaign = await db.campaigns.find_one({"id": insight_data.campaign_id}, {"_id": 0})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaña no encontrada")
    
    insight = Insight(
        tenant_id=campaign.get("tenant_id", "default"),
        campaign_id=insight_data.campaign_id,
        content=insight_data.content,
        type=insight_data.type,
        category_id=insight_data.category_id,
        source_session_id=insight_data.source_session_id,
        source_quote=insight_data.source_quote,
        sentiment=insight_data.sentiment,
        importance=insight_data.importance,
        extracted_by="manual"
    )
    await db.insights.insert_one(serialize_document(insight.model_dump()))
    
    if insight_data.category_id:
        await db.taxonomy.update_one({"id": insight_data.category_id}, {"$inc": {"usage_count": 1}})
    
    return insight

@insight_router.get("/campaign/{campaign_id}", response_model=List[Insight])
async def list_campaign_insights(
    campaign_id: str,
    current_user: dict = Depends(get_current_user),
    type: Optional[str] = None,
    status: Optional[str] = None,
    sentiment: Optional[str] = None
):
    if current_user["role"] not in ["admin", "facilitator", "analyst"]:
        raise HTTPException(status_code=403, detail="No tiene permisos")
    
    query = {"campaign_id": campaign_id}
    if type: query["type"] = type
    if status: query["status"] = status
    if sentiment: query["sentiment"] = sentiment
    
    insights = await db.insights.find(query, {"_id": 0}).sort("importance", -1).to_list(500)
    return insights

@insight_router.get("/{insight_id}", response_model=Insight)
async def get_insight(insight_id: str, current_user: dict = Depends(get_current_user)):
    insight = await db.insights.find_one({"id": insight_id}, {"_id": 0})
    if not insight:
        raise HTTPException(status_code=404, detail="Insight no encontrado")
    return insight

@insight_router.put("/{insight_id}", response_model=Insight)
async def update_insight(insight_id: str, insight_data: InsightUpdate, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["admin", "facilitator", "analyst"]:
        raise HTTPException(status_code=403, detail="No tiene permisos")
    
    update_data = {k: v for k, v in insight_data.model_dump().items() if v is not None}
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.insights.update_one({"id": insight_id}, {"$set": update_data})
    updated = await db.insights.find_one({"id": insight_id}, {"_id": 0})
    return updated

@insight_router.patch("/{insight_id}/validate")
async def validate_insight(insight_id: str, validated: bool, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["admin", "facilitator", "analyst"]:
        raise HTTPException(status_code=403, detail="No tiene permisos")
    
    status = "validated" if validated else "rejected"
    await db.insights.update_one(
        {"id": insight_id},
        {"$set": {
            "status": status,
            "validated_by": current_user["id"],
            "validated_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    return {"message": f"Insight {status}", "status": status}

@insight_router.get("/campaign/{campaign_id}/stats", response_model=InsightStats)
async def get_insight_stats(campaign_id: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["admin", "facilitator", "analyst"]:
        raise HTTPException(status_code=403, detail="No tiene permisos")
    
    total = await db.insights.count_documents({"campaign_id": campaign_id})
    
    by_type = {}
    for t in ["theme", "tension", "symbol", "opportunity", "risk"]:
        by_type[t] = await db.insights.count_documents({"campaign_id": campaign_id, "type": t})
    
    by_status = {}
    for s in ["draft", "validated", "rejected", "needs_review"]:
        by_status[s] = await db.insights.count_documents({"campaign_id": campaign_id, "status": s})
    
    by_sentiment = {}
    for sent in ["positive", "negative", "neutral", "mixed"]:
        by_sentiment[sent] = await db.insights.count_documents({"campaign_id": campaign_id, "sentiment": sent})
    
    # Top categories
    pipeline = [
        {"$match": {"campaign_id": campaign_id, "category_id": {"$ne": None}}},
        {"$group": {"_id": "$category_id", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 5}
    ]
    top_cats = await db.insights.aggregate(pipeline).to_list(5)
    top_categories = []
    for tc in top_cats:
        cat = await db.taxonomy.find_one({"id": tc["_id"]}, {"_id": 0})
        if cat:
            top_categories.append({"id": tc["_id"], "name": cat.get("name"), "count": tc["count"]})
    
    return InsightStats(
        campaign_id=campaign_id,
        total_insights=total,
        by_type=by_type,
        by_status=by_status,
        by_sentiment=by_sentiment,
        top_categories=top_categories
    )

@insight_router.post("/campaign/{campaign_id}/extract")
async def extract_insights(campaign_id: str, background_tasks: BackgroundTasks, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["admin", "facilitator"]:
        raise HTTPException(status_code=403, detail="No tiene permisos")
    
    campaign = await db.campaigns.find_one({"id": campaign_id}, {"_id": 0})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaña no encontrada")
    
    # Get unprocessed transcripts
    transcripts = await db.transcripts.find({
        "campaign_id": campaign_id,
        "insights_extracted": {"$ne": True}
    }, {"_id": 0}).to_list(100)
    
    if not transcripts:
        return {"message": "No hay transcripciones pendientes de procesar", "processed": 0}
    
    # Process in background
    async def process_transcripts():
        total_insights = 0
        for t in transcripts:
            # First pseudonymize
            await pseudonymization_service.pseudonymize_transcript(t["id"])
            # Then extract
            insights = await insight_extraction_service.extract_insights_from_transcript(
                t["id"], campaign_id, campaign.get("tenant_id", "default")
            )
            total_insights += len(insights)
        
        await db.campaigns.update_one(
            {"id": campaign_id},
            {"$set": {"insights_extracted": True, "updated_at": datetime.now(timezone.utc).isoformat()}}
        )
    
    background_tasks.add_task(process_transcripts)
    
    return {"message": f"Procesando {len(transcripts)} transcripciones", "queued": len(transcripts)}

# ============== VALIDATION ROUTES (NEW - Phase 3) ==============

@api_router.post("/validations/", response_model=ValidationRequest)
async def create_validation_request(val_data: ValidationRequestCreate, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["admin", "facilitator"]:
        raise HTTPException(status_code=403, detail="No tiene permisos")
    
    insight = await db.insights.find_one({"id": val_data.insight_id}, {"_id": 0})
    if not insight:
        raise HTTPException(status_code=404, detail="Insight no encontrado")
    
    # Get a participant from the campaign
    consents = await db.consents.find({
        "campaign_id": insight["campaign_id"],
        "accepted": True,
        "revoked_at": None
    }, {"_id": 0}).to_list(10)
    
    if not consents:
        raise HTTPException(status_code=400, detail="No hay participantes disponibles")
    
    # Create validation request for each participant
    created = []
    for consent in consents[:3]:  # Max 3 validators per insight
        validation = ValidationRequest(
            insight_id=val_data.insight_id,
            campaign_id=insight["campaign_id"],
            tenant_id=insight.get("tenant_id", "default"),
            user_id=consent["user_id"]
        )
        await db.validations.insert_one(serialize_document(validation.model_dump()))
        created.append(validation)
    
    await db.insights.update_one({"id": val_data.insight_id}, {"$set": {"status": "needs_review"}})
    
    return created[0] if created else None

@api_router.get("/validations/pending")
async def get_pending_validations(current_user: dict = Depends(get_current_user)):
    validations = await db.validations.find({
        "user_id": current_user["id"],
        "status": "pending"
    }, {"_id": 0}).to_list(50)
    
    # Enrich with insight data
    enriched = []
    for v in validations:
        insight = await db.insights.find_one({"id": v["insight_id"]}, {"_id": 0})
        if insight:
            enriched.append({**v, "insight": insight})
    
    return enriched

@api_router.post("/validations/{validation_id}/respond")
async def respond_validation(validation_id: str, response: ValidationResponse, current_user: dict = Depends(get_current_user)):
    validation = await db.validations.find_one({"id": validation_id}, {"_id": 0})
    if not validation:
        raise HTTPException(status_code=404, detail="Validación no encontrada")
    
    if validation["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="No tiene acceso")
    
    status = "validated" if response.validated else "rejected"
    await db.validations.update_one(
        {"id": validation_id},
        {"$set": {
            "status": status,
            "response": response.comment,
            "responded_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # Check if insight should be updated
    all_validations = await db.validations.find({"insight_id": validation["insight_id"]}, {"_id": 0}).to_list(10)
    validated_count = sum(1 for v in all_validations if v.get("status") == "validated")
    rejected_count = sum(1 for v in all_validations if v.get("status") == "rejected")
    
    if validated_count >= 2:
        await db.insights.update_one({"id": validation["insight_id"]}, {"$set": {"status": "validated"}})
    elif rejected_count >= 2:
        await db.insights.update_one({"id": validation["insight_id"]}, {"$set": {"status": "rejected"}})
    
    return {"message": "Respuesta registrada", "status": status}

# ============== TRANSCRIPT ROUTES (NEW - Phase 3) ==============

@transcript_router.get("/campaign/{campaign_id}")
async def list_campaign_transcripts(campaign_id: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["admin", "facilitator", "analyst"]:
        raise HTTPException(status_code=403, detail="No tiene permisos")
    
    transcripts = await db.transcripts.find(
        {"campaign_id": campaign_id},
        {"_id": 0, "messages": 0}  # Exclude messages for list view
    ).to_list(500)
    
    return transcripts

@transcript_router.get("/{transcript_id}")
async def get_transcript(transcript_id: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["admin", "facilitator", "analyst"]:
        raise HTTPException(status_code=403, detail="No tiene permisos")
    
    transcript = await db.transcripts.find_one({"id": transcript_id}, {"_id": 0})
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcripción no encontrada")
    return transcript

@transcript_router.post("/{transcript_id}/pseudonymize")
async def pseudonymize_transcript(transcript_id: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["admin", "facilitator"]:
        raise HTTPException(status_code=403, detail="No tiene permisos")
    
    success = await pseudonymization_service.pseudonymize_transcript(transcript_id)
    if success:
        return {"message": "Transcripción pseudonimizada"}
    return {"message": "La transcripción ya estaba pseudonimizada o no existe"}

# ============== INVITE ROUTES ==============

@invite_router.post("/", response_model=Invite)
async def create_invite(invite_data: InviteCreate, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["admin", "facilitator"]:
        raise HTTPException(status_code=403, detail="No tiene permisos")
    
    campaign = await db.campaigns.find_one({"id": invite_data.campaign_id}, {"_id": 0})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaña no encontrada")
    
    invite = Invite(
        campaign_id=invite_data.campaign_id,
        tenant_id=campaign.get("tenant_id", "default"),
        user_id=invite_data.user_id,
        email=invite_data.email,
        segment_id=invite_data.segment_id,
        message=invite_data.message,
        invited_by=current_user["id"],
        status="sent",
        sent_at=datetime.now(timezone.utc)
    )
    await db.invites.insert_one(serialize_document(invite.model_dump()))
    await db.campaigns.update_one({"id": invite_data.campaign_id}, {"$inc": {"invite_count": 1}})
    return invite

@invite_router.post("/bulk")
async def create_bulk_invites(invite_data: InviteBulk, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["admin", "facilitator"]:
        raise HTTPException(status_code=403, detail="No tiene permisos")
    
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

@invite_router.get("/campaign/{campaign_id}", response_model=List[Invite])
async def list_campaign_invites(campaign_id: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["admin", "facilitator"]:
        raise HTTPException(status_code=403, detail="No tiene permisos")
    invites = await db.invites.find({"campaign_id": campaign_id}, {"_id": 0}).to_list(500)
    return invites

# ============== CONSENT ROUTES ==============

@consent_router.post("/", response_model=Consent)
async def create_consent(consent_data: ConsentCreate, current_user: dict = Depends(get_current_user)):
    campaign = await db.campaigns.find_one({"id": consent_data.campaign_id}, {"_id": 0})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaña no encontrada")
    
    existing = await db.consents.find_one({"user_id": current_user["id"], "campaign_id": consent_data.campaign_id, "revoked_at": None})
    if existing:
        raise HTTPException(status_code=400, detail="Ya existe consentimiento")
    
    consent = Consent(user_id=current_user["id"], campaign_id=consent_data.campaign_id, tenant_id=campaign.get("tenant_id", "default"), accepted=consent_data.accepted, consent_text=consent_data.consent_text or "Acepto participar...")
    await db.consents.insert_one(serialize_document(consent.model_dump()))
    
    if consent_data.accepted:
        await db.campaigns.update_one({"id": consent_data.campaign_id}, {"$inc": {"participant_count": 1}})
    
    return consent

@consent_router.get("/my-consents", response_model=List[Consent])
async def get_my_consents(current_user: dict = Depends(get_current_user)):
    consents = await db.consents.find({"user_id": current_user["id"], "revoked_at": None}, {"_id": 0}).to_list(100)
    return consents

# ============== SESSION ROUTES ==============

@session_router.post("/", response_model=Session)
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

@session_router.get("/", response_model=List[Session])
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

@chat_router.post("/message", response_model=ChatResponse)
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
    await db.transcripts.update_one(
        {"session_id": chat_request.session_id},
        {"$push": {"messages": {"$each": [
            {"role": "user", "content": chat_request.message, "timestamp": now.isoformat()},
            {"role": "assistant", "content": response, "timestamp": now.isoformat()}
        ]}}}
    )
    
    return ChatResponse(session_id=chat_request.session_id, message=response, timestamp=now)

@chat_router.get("/history/{session_id}")
async def get_chat_history(session_id: str, current_user: dict = Depends(get_current_user)):
    transcript = await db.transcripts.find_one({"session_id": session_id}, {"_id": 0})
    return {"messages": transcript.get("messages", []) if transcript else []}

# ============== DASHBOARD ==============

@api_router.get("/dashboard/stats")
async def get_dashboard_stats(current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["admin", "facilitator", "analyst"]:
        raise HTTPException(status_code=403, detail="No tiene permisos")
    
    return {
        "campaigns": {
            "total": await db.campaigns.count_documents({}),
            "active": await db.campaigns.count_documents({"status": "active"})
        },
        "sessions": {
            "total": await db.sessions.count_documents({}),
            "completed": await db.sessions.count_documents({"status": "completed"})
        },
        "users": await db.users.count_documents({}),
        "active_consents": await db.consents.count_documents({"accepted": True, "revoked_at": None}),
        "scripts": await db.scripts.count_documents({"is_active": True}),
        "invites": await db.invites.count_documents({}),
        "insights": await db.insights.count_documents({})
    }

# ============== HEALTH CHECK ==============

@api_router.get("/")
async def root():
    return {"message": "DigiKawsay API v0.3.0", "status": "healthy"}

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

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
