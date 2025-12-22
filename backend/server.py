from fastapi import FastAPI, APIRouter, HTTPException, Depends, status, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from emergentintegrations.llm.chat import LlmChat, UserMessage
import asyncio

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
app = FastAPI(title="DigiKawsay API", version="0.2.0")

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

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ============== PYDANTIC MODELS ==============

# --- Base Models ---
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

# --- Script Models (NEW - Phase 2) ---
class ScriptStep(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    order: int
    question: str
    description: Optional[str] = None
    type: str = "open"  # open, multiple_choice, scale
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
    parent_id: Optional[str] = None  # For version tracking

class ScriptVersion(TimestampMixin):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    script_id: str
    version: int
    changes: str
    created_by: str
    snapshot: Dict[str, Any] = {}

# --- Segment Models (NEW - Phase 2) ---
class SegmentCreate(BaseModel):
    name: str
    description: Optional[str] = None
    criteria: Optional[Dict[str, Any]] = None  # e.g., {"department": "Engineering", "role": "participant"}
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

# --- Invitation Models (NEW - Phase 2) ---
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
    status: str = "pending"  # pending, sent, accepted, declined, expired
    sent_at: Optional[datetime] = None
    responded_at: Optional[datetime] = None
    message: Optional[str] = None
    invited_by: str

# --- Campaign Models (Updated) ---
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

# --- Coverage/Analytics Models (NEW - Phase 2) ---
class CoverageStats(BaseModel):
    campaign_id: str
    total_invited: int = 0
    total_consented: int = 0
    total_sessions: int = 0
    completed_sessions: int = 0
    participation_rate: float = 0.0
    completion_rate: float = 0.0
    segments: List[Dict[str, Any]] = []

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
    """Helper to serialize datetime objects for MongoDB"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    return obj

def serialize_document(doc: dict) -> dict:
    """Serialize all datetime fields in a document"""
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

# ============== VAL CHAT SERVICE ==============

class VALChatService:
    def __init__(self):
        self.api_key = os.environ.get('EMERGENT_LLM_KEY')
        self.active_chats: Dict[str, LlmChat] = {}
    
    def get_system_prompt(self, campaign_objective: str = "", script_context: str = "") -> str:
        base_prompt = f"""Eres VAL, una facilitadora conversacional experta en coaching ontológico e Investigación Acción Participativa (IAP).

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
        return base_prompt

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
        user=UserResponse(
            id=user_obj.id,
            email=user_obj.email,
            full_name=user_obj.full_name,
            role=user_obj.role,
            tenant_id=user_obj.tenant_id,
            department=user_obj.department,
            position=user_obj.position,
            is_active=user_obj.is_active
        )
    )

@auth_router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin):
    user = await db.users.find_one({"email": credentials.email}, {"_id": 0})
    if not user or not verify_password(credentials.password, user.get("hashed_password", "")):
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
    
    access_token = create_access_token(data={"sub": user["id"]})
    return TokenResponse(
        access_token=access_token,
        user=UserResponse(
            id=user["id"],
            email=user["email"],
            full_name=user["full_name"],
            role=user["role"],
            tenant_id=user.get("tenant_id"),
            department=user.get("department"),
            position=user.get("position"),
            is_active=user.get("is_active", True)
        )
    )

@auth_router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    return UserResponse(
        id=current_user["id"],
        email=current_user["email"],
        full_name=current_user["full_name"],
        role=current_user["role"],
        tenant_id=current_user.get("tenant_id"),
        department=current_user.get("department"),
        position=current_user.get("position"),
        is_active=current_user.get("is_active", True)
    )

# ============== USER ROUTES ==============

@user_router.get("/", response_model=List[UserResponse])
async def list_users(
    current_user: dict = Depends(get_current_user),
    role: Optional[str] = None,
    department: Optional[str] = None
):
    if current_user["role"] not in ["admin", "facilitator"]:
        raise HTTPException(status_code=403, detail="No tiene permisos")
    
    query = {}
    if role:
        query["role"] = role
    if department:
        query["department"] = department
    
    users = await db.users.find(query, {"_id": 0, "hashed_password": 0}).to_list(500)
    return [UserResponse(**u) for u in users]

# ============== TENANT ROUTES ==============

@tenant_router.post("/", response_model=Tenant)
async def create_tenant(tenant_data: TenantCreate, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["admin"]:
        raise HTTPException(status_code=403, detail="Solo administradores pueden crear tenants")
    
    tenant = Tenant(**tenant_data.model_dump())
    doc = serialize_document(tenant.model_dump())
    await db.tenants.insert_one(doc)
    return tenant

@tenant_router.get("/", response_model=List[Tenant])
async def list_tenants(current_user: dict = Depends(get_current_user)):
    tenants = await db.tenants.find({}, {"_id": 0}).to_list(100)
    return tenants

@tenant_router.get("/{tenant_id}", response_model=Tenant)
async def get_tenant(tenant_id: str, current_user: dict = Depends(get_current_user)):
    tenant = await db.tenants.find_one({"id": tenant_id}, {"_id": 0})
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant no encontrado")
    return tenant

# ============== SCRIPT ROUTES (NEW - Phase 2) ==============

@script_router.post("/", response_model=Script)
async def create_script(script_data: ScriptCreate, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["admin", "facilitator"]:
        raise HTTPException(status_code=403, detail="No tiene permisos para crear guiones")
    
    steps_data = [step.model_dump() for step in script_data.steps]
    
    script = Script(
        tenant_id=current_user.get("tenant_id") or "default",
        name=script_data.name,
        description=script_data.description,
        objective=script_data.objective,
        steps=steps_data,
        welcome_message=script_data.welcome_message,
        closing_message=script_data.closing_message,
        estimated_duration_minutes=script_data.estimated_duration_minutes,
        created_by=current_user["id"]
    )
    
    doc = serialize_document(script.model_dump())
    await db.scripts.insert_one(doc)
    
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
    
    # Create new version
    new_version = existing.get("version", 1) + 1
    
    # Save version history
    version_record = ScriptVersion(
        script_id=script_id,
        version=existing.get("version", 1),
        changes=f"Actualizado a versión {new_version}",
        created_by=current_user["id"],
        snapshot=existing
    )
    await db.script_versions.insert_one(serialize_document(version_record.model_dump()))
    
    # Update script
    update_data = {k: v for k, v in script_data.model_dump().items() if v is not None}
    if "steps" in update_data:
        update_data["steps"] = [s.model_dump() if hasattr(s, 'model_dump') else s for s in update_data["steps"]]
    
    update_data["version"] = new_version
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.scripts.update_one(
        {"id": script_id},
        {"$set": update_data}
    )
    
    updated = await db.scripts.find_one({"id": script_id}, {"_id": 0})
    return updated

@script_router.get("/{script_id}/versions")
async def get_script_versions(script_id: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["admin", "facilitator"]:
        raise HTTPException(status_code=403, detail="No tiene permisos")
    
    versions = await db.script_versions.find(
        {"script_id": script_id}, 
        {"_id": 0}
    ).sort("version", -1).to_list(50)
    
    return {"script_id": script_id, "versions": versions}

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
    
    doc = serialize_document(new_script.model_dump())
    await db.scripts.insert_one(doc)
    
    return new_script

# ============== CAMPAIGN ROUTES ==============

@campaign_router.post("/", response_model=Campaign)
async def create_campaign(campaign_data: CampaignCreate, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["admin", "facilitator"]:
        raise HTTPException(status_code=403, detail="No tiene permisos para crear campañas")
    
    campaign = Campaign(
        **campaign_data.model_dump(),
        tenant_id=current_user.get("tenant_id") or "default",
        created_by=current_user["id"]
    )
    
    doc = serialize_document(campaign.model_dump())
    await db.campaigns.insert_one(doc)
    return campaign

@campaign_router.get("/", response_model=List[Campaign])
async def list_campaigns(
    current_user: dict = Depends(get_current_user),
    status: Optional[str] = None
):
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
    
    existing = await db.campaigns.find_one({"id": campaign_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Campaña no encontrada")
    
    update_data = {k: v for k, v in campaign_data.model_dump().items() if v is not None}
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    # Serialize datetime fields
    for key in ["start_date", "end_date"]:
        if key in update_data and update_data[key]:
            update_data[key] = update_data[key].isoformat()
    
    await db.campaigns.update_one(
        {"id": campaign_id},
        {"$set": update_data}
    )
    
    updated = await db.campaigns.find_one({"id": campaign_id}, {"_id": 0})
    return updated

@campaign_router.patch("/{campaign_id}/status")
async def update_campaign_status(campaign_id: str, status: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["admin", "facilitator"]:
        raise HTTPException(status_code=403, detail="No tiene permisos")
    
    valid_statuses = ["draft", "active", "paused", "closed"]
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Estado inválido. Use: {valid_statuses}")
    
    result = await db.campaigns.update_one(
        {"id": campaign_id},
        {"$set": {"status": status, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Campaña no encontrada")
    
    return {"message": "Estado actualizado", "status": status}

@campaign_router.get("/{campaign_id}/coverage", response_model=CoverageStats)
async def get_campaign_coverage(campaign_id: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["admin", "facilitator", "analyst"]:
        raise HTTPException(status_code=403, detail="No tiene permisos")
    
    campaign = await db.campaigns.find_one({"id": campaign_id}, {"_id": 0})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaña no encontrada")
    
    # Count invites
    total_invited = await db.invites.count_documents({"campaign_id": campaign_id})
    
    # Count consents
    total_consented = await db.consents.count_documents({
        "campaign_id": campaign_id, 
        "accepted": True, 
        "revoked_at": None
    })
    
    # Count sessions
    total_sessions = await db.sessions.count_documents({"campaign_id": campaign_id})
    completed_sessions = await db.sessions.count_documents({
        "campaign_id": campaign_id, 
        "status": "completed"
    })
    
    # Calculate rates
    participation_rate = (total_consented / total_invited * 100) if total_invited > 0 else 0
    completion_rate = (completed_sessions / total_sessions * 100) if total_sessions > 0 else 0
    
    # Get segment stats
    segments = await db.segments.find({"campaign_id": campaign_id}, {"_id": 0}).to_list(50)
    segment_stats = []
    for seg in segments:
        seg_consents = await db.consents.count_documents({
            "campaign_id": campaign_id,
            "accepted": True,
            "revoked_at": None
        })
        segment_stats.append({
            "id": seg["id"],
            "name": seg["name"],
            "target": seg.get("target_count", 0),
            "current": seg.get("current_count", 0),
            "completion_rate": seg.get("completion_rate", 0)
        })
    
    return CoverageStats(
        campaign_id=campaign_id,
        total_invited=total_invited,
        total_consented=total_consented,
        total_sessions=total_sessions,
        completed_sessions=completed_sessions,
        participation_rate=round(participation_rate, 1),
        completion_rate=round(completion_rate, 1),
        segments=segment_stats
    )

# ============== SEGMENT ROUTES (NEW - Phase 2) ==============

@segment_router.post("/", response_model=Segment)
async def create_segment(
    campaign_id: str,
    segment_data: SegmentCreate,
    current_user: dict = Depends(get_current_user)
):
    if current_user["role"] not in ["admin", "facilitator"]:
        raise HTTPException(status_code=403, detail="No tiene permisos")
    
    campaign = await db.campaigns.find_one({"id": campaign_id}, {"_id": 0})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaña no encontrada")
    
    segment = Segment(
        campaign_id=campaign_id,
        tenant_id=campaign.get("tenant_id", "default"),
        **segment_data.model_dump()
    )
    
    doc = serialize_document(segment.model_dump())
    await db.segments.insert_one(doc)
    
    return segment

@segment_router.get("/campaign/{campaign_id}", response_model=List[Segment])
async def list_campaign_segments(campaign_id: str, current_user: dict = Depends(get_current_user)):
    segments = await db.segments.find({"campaign_id": campaign_id}, {"_id": 0}).to_list(50)
    return segments

@segment_router.delete("/{segment_id}")
async def delete_segment(segment_id: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["admin", "facilitator"]:
        raise HTTPException(status_code=403, detail="No tiene permisos")
    
    result = await db.segments.delete_one({"id": segment_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Segmento no encontrado")
    
    return {"message": "Segmento eliminado"}

# ============== INVITATION ROUTES (NEW - Phase 2) ==============

@invite_router.post("/", response_model=Invite)
async def create_invite(invite_data: InviteCreate, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["admin", "facilitator"]:
        raise HTTPException(status_code=403, detail="No tiene permisos")
    
    campaign = await db.campaigns.find_one({"id": invite_data.campaign_id}, {"_id": 0})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaña no encontrada")
    
    # Check for existing invite
    query = {"campaign_id": invite_data.campaign_id}
    if invite_data.user_id:
        query["user_id"] = invite_data.user_id
    elif invite_data.email:
        query["email"] = invite_data.email
    
    existing = await db.invites.find_one(query)
    if existing:
        raise HTTPException(status_code=400, detail="Ya existe una invitación para este usuario/email")
    
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
    
    doc = serialize_document(invite.model_dump())
    await db.invites.insert_one(doc)
    
    # Update campaign invite count
    await db.campaigns.update_one(
        {"id": invite_data.campaign_id},
        {"$inc": {"invite_count": 1}}
    )
    
    return invite

@invite_router.post("/bulk")
async def create_bulk_invites(invite_data: InviteBulk, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["admin", "facilitator"]:
        raise HTTPException(status_code=403, detail="No tiene permisos")
    
    campaign = await db.campaigns.find_one({"id": invite_data.campaign_id}, {"_id": 0})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaña no encontrada")
    
    created = 0
    skipped = 0
    
    # Process user IDs
    for user_id in invite_data.user_ids:
        existing = await db.invites.find_one({
            "campaign_id": invite_data.campaign_id,
            "user_id": user_id
        })
        if existing:
            skipped += 1
            continue
        
        invite = Invite(
            campaign_id=invite_data.campaign_id,
            tenant_id=campaign.get("tenant_id", "default"),
            user_id=user_id,
            segment_id=invite_data.segment_id,
            message=invite_data.message,
            invited_by=current_user["id"],
            status="sent",
            sent_at=datetime.now(timezone.utc)
        )
        await db.invites.insert_one(serialize_document(invite.model_dump()))
        created += 1
    
    # Process emails
    for email in invite_data.emails:
        existing = await db.invites.find_one({
            "campaign_id": invite_data.campaign_id,
            "email": email
        })
        if existing:
            skipped += 1
            continue
        
        invite = Invite(
            campaign_id=invite_data.campaign_id,
            tenant_id=campaign.get("tenant_id", "default"),
            email=email,
            segment_id=invite_data.segment_id,
            message=invite_data.message,
            invited_by=current_user["id"],
            status="sent",
            sent_at=datetime.now(timezone.utc)
        )
        await db.invites.insert_one(serialize_document(invite.model_dump()))
        created += 1
    
    # Update campaign invite count
    if created > 0:
        await db.campaigns.update_one(
            {"id": invite_data.campaign_id},
            {"$inc": {"invite_count": created}}
        )
    
    return {"message": f"Invitaciones procesadas", "created": created, "skipped": skipped}

@invite_router.get("/campaign/{campaign_id}", response_model=List[Invite])
async def list_campaign_invites(
    campaign_id: str, 
    current_user: dict = Depends(get_current_user),
    status: Optional[str] = None
):
    if current_user["role"] not in ["admin", "facilitator"]:
        raise HTTPException(status_code=403, detail="No tiene permisos")
    
    query = {"campaign_id": campaign_id}
    if status:
        query["status"] = status
    
    invites = await db.invites.find(query, {"_id": 0}).to_list(500)
    return invites

@invite_router.get("/my-invites", response_model=List[Invite])
async def get_my_invites(current_user: dict = Depends(get_current_user)):
    invites = await db.invites.find({
        "$or": [
            {"user_id": current_user["id"]},
            {"email": current_user["email"]}
        ],
        "status": {"$in": ["pending", "sent"]}
    }, {"_id": 0}).to_list(50)
    return invites

@invite_router.patch("/{invite_id}/respond")
async def respond_to_invite(
    invite_id: str, 
    accepted: bool,
    current_user: dict = Depends(get_current_user)
):
    invite = await db.invites.find_one({"id": invite_id}, {"_id": 0})
    if not invite:
        raise HTTPException(status_code=404, detail="Invitación no encontrada")
    
    # Verify user owns the invite
    if invite.get("user_id") != current_user["id"] and invite.get("email") != current_user["email"]:
        raise HTTPException(status_code=403, detail="No tiene acceso a esta invitación")
    
    new_status = "accepted" if accepted else "declined"
    await db.invites.update_one(
        {"id": invite_id},
        {
            "$set": {
                "status": new_status,
                "responded_at": datetime.now(timezone.utc).isoformat(),
                "user_id": current_user["id"]  # Link user if invite was by email
            }
        }
    )
    
    return {"message": f"Invitación {new_status}", "status": new_status}

# ============== CONSENT ROUTES ==============

@consent_router.post("/", response_model=Consent)
async def create_consent(consent_data: ConsentCreate, current_user: dict = Depends(get_current_user)):
    campaign = await db.campaigns.find_one({"id": consent_data.campaign_id}, {"_id": 0})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaña no encontrada")
    
    existing = await db.consents.find_one({
        "user_id": current_user["id"],
        "campaign_id": consent_data.campaign_id,
        "revoked_at": None
    })
    
    if existing:
        raise HTTPException(status_code=400, detail="Ya existe un consentimiento activo para esta campaña")
    
    consent = Consent(
        user_id=current_user["id"],
        campaign_id=consent_data.campaign_id,
        tenant_id=campaign.get("tenant_id", "default"),
        accepted=consent_data.accepted,
        consent_text=consent_data.consent_text or "Acepto participar en esta campaña de diálogo y autorizo el uso de mis respuestas de forma anonimizada para fines de análisis organizacional."
    )
    
    doc = serialize_document(consent.model_dump())
    await db.consents.insert_one(doc)
    
    if consent_data.accepted:
        await db.campaigns.update_one(
            {"id": consent_data.campaign_id},
            {"$inc": {"participant_count": 1}}
        )
        # Update invite status if exists
        await db.invites.update_one(
            {"campaign_id": consent_data.campaign_id, "user_id": current_user["id"]},
            {"$set": {"status": "accepted", "responded_at": datetime.now(timezone.utc).isoformat()}}
        )
    
    return consent

@consent_router.get("/my-consents", response_model=List[Consent])
async def get_my_consents(current_user: dict = Depends(get_current_user)):
    consents = await db.consents.find(
        {"user_id": current_user["id"], "revoked_at": None},
        {"_id": 0}
    ).to_list(100)
    return consents

@consent_router.post("/{consent_id}/revoke")
async def revoke_consent(consent_id: str, current_user: dict = Depends(get_current_user)):
    consent = await db.consents.find_one({"id": consent_id, "user_id": current_user["id"]}, {"_id": 0})
    if not consent:
        raise HTTPException(status_code=404, detail="Consentimiento no encontrado")
    
    await db.consents.update_one(
        {"id": consent_id},
        {"$set": {"revoked_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    # Update campaign participant count
    await db.campaigns.update_one(
        {"id": consent["campaign_id"]},
        {"$inc": {"participant_count": -1}}
    )
    
    return {"message": "Consentimiento revocado exitosamente"}

# ============== SESSION ROUTES ==============

@session_router.post("/", response_model=Session)
async def create_session(session_data: SessionCreate, current_user: dict = Depends(get_current_user)):
    consent = await db.consents.find_one({
        "user_id": current_user["id"],
        "campaign_id": session_data.campaign_id,
        "accepted": True,
        "revoked_at": None
    })
    
    if not consent:
        raise HTTPException(
            status_code=403,
            detail="Debe aceptar el consentimiento antes de iniciar una sesión"
        )
    
    campaign = await db.campaigns.find_one({"id": session_data.campaign_id}, {"_id": 0})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaña no encontrada")
    
    if campaign.get("status") != "active":
        raise HTTPException(status_code=400, detail="La campaña no está activa")
    
    session = Session(
        user_id=current_user["id"],
        campaign_id=session_data.campaign_id,
        tenant_id=campaign.get("tenant_id", "default"),
        status="in_progress",
        started_at=datetime.now(timezone.utc),
        script_id=campaign.get("script_id")
    )
    
    doc = serialize_document(session.model_dump())
    await db.sessions.insert_one(doc)
    
    # Create transcript
    transcript = Transcript(
        session_id=session.id,
        campaign_id=session_data.campaign_id,
        tenant_id=campaign.get("tenant_id", "default"),
        user_id=current_user["id"]
    )
    await db.transcripts.insert_one(serialize_document(transcript.model_dump()))
    
    # Update campaign session count
    await db.campaigns.update_one(
        {"id": session_data.campaign_id},
        {"$inc": {"session_count": 1}}
    )
    
    return session

@session_router.get("/", response_model=List[Session])
async def list_sessions(current_user: dict = Depends(get_current_user)):
    query = {"user_id": current_user["id"]}
    if current_user["role"] in ["admin", "facilitator"]:
        query = {}
    
    sessions = await db.sessions.find(query, {"_id": 0}).to_list(100)
    return sessions

@session_router.get("/{session_id}", response_model=Session)
async def get_session(session_id: str, current_user: dict = Depends(get_current_user)):
    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    
    if current_user["role"] == "participant" and session["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="No tiene acceso a esta sesión")
    
    return session

@session_router.post("/{session_id}/complete")
async def complete_session(session_id: str, current_user: dict = Depends(get_current_user)):
    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    
    if session["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="No tiene acceso a esta sesión")
    
    await db.sessions.update_one(
        {"id": session_id},
        {
            "$set": {
                "status": "completed",
                "ended_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    # Update campaign completed sessions count
    await db.campaigns.update_one(
        {"id": session["campaign_id"]},
        {"$inc": {"completed_sessions": 1}}
    )
    
    val_service.close_session(session_id)
    
    return {"message": "Sesión completada exitosamente"}

# ============== CHAT ROUTES ==============

@chat_router.post("/message", response_model=ChatResponse)
async def send_chat_message(chat_request: ChatRequest, current_user: dict = Depends(get_current_user)):
    session = await db.sessions.find_one({"id": chat_request.session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    
    if session["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="No tiene acceso a esta sesión")
    
    if session["status"] != "in_progress":
        raise HTTPException(status_code=400, detail="La sesión no está activa")
    
    # Get campaign and script context
    campaign = await db.campaigns.find_one({"id": session["campaign_id"]}, {"_id": 0})
    campaign_objective = campaign.get("objective", "") if campaign else ""
    
    script_context = ""
    if session.get("script_id"):
        script = await db.scripts.find_one({"id": session["script_id"]}, {"_id": 0})
        if script and script.get("steps"):
            steps_text = "\n".join([f"- {s.get('question', '')}" for s in script["steps"][:5]])
            script_context = f"\nGuión de preguntas sugeridas:\n{steps_text}"
    
    # Send to VAL
    response = await val_service.send_message(
        chat_request.session_id,
        chat_request.message,
        campaign_objective,
        script_context
    )
    
    # Save to transcript
    now = datetime.now(timezone.utc)
    user_msg = {"role": "user", "content": chat_request.message, "timestamp": now.isoformat()}
    assistant_msg = {"role": "assistant", "content": response, "timestamp": now.isoformat()}
    
    await db.transcripts.update_one(
        {"session_id": chat_request.session_id},
        {
            "$push": {"messages": {"$each": [user_msg, assistant_msg]}},
            "$set": {"updated_at": now.isoformat()}
        }
    )
    
    return ChatResponse(
        session_id=chat_request.session_id,
        message=response,
        timestamp=now
    )

@chat_router.get("/history/{session_id}")
async def get_chat_history(session_id: str, current_user: dict = Depends(get_current_user)):
    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    
    if current_user["role"] == "participant" and session["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="No tiene acceso a esta sesión")
    
    transcript = await db.transcripts.find_one({"session_id": session_id}, {"_id": 0})
    if not transcript:
        return {"messages": []}
    
    return {"messages": transcript.get("messages", [])}

# ============== DASHBOARD ROUTES ==============

@api_router.get("/dashboard/stats")
async def get_dashboard_stats(current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["admin", "facilitator", "analyst"]:
        raise HTTPException(status_code=403, detail="No tiene permisos")
    
    total_campaigns = await db.campaigns.count_documents({})
    active_campaigns = await db.campaigns.count_documents({"status": "active"})
    total_sessions = await db.sessions.count_documents({})
    completed_sessions = await db.sessions.count_documents({"status": "completed"})
    total_users = await db.users.count_documents({})
    total_consents = await db.consents.count_documents({"accepted": True, "revoked_at": None})
    total_scripts = await db.scripts.count_documents({"is_active": True})
    total_invites = await db.invites.count_documents({})
    
    return {
        "campaigns": {
            "total": total_campaigns,
            "active": active_campaigns
        },
        "sessions": {
            "total": total_sessions,
            "completed": completed_sessions
        },
        "users": total_users,
        "active_consents": total_consents,
        "scripts": total_scripts,
        "invites": total_invites
    }

# ============== HEALTH CHECK ==============

@api_router.get("/")
async def root():
    return {"message": "DigiKawsay API v0.2.0", "status": "healthy"}

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
