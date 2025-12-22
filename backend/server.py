from fastapi import FastAPI, APIRouter, HTTPException, Depends, status
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
app = FastAPI(title="DigiKawsay API", version="0.1.0")

# Create routers
api_router = APIRouter(prefix="/api")
auth_router = APIRouter(prefix="/auth", tags=["Authentication"])
tenant_router = APIRouter(prefix="/tenants", tags=["Tenants"])
user_router = APIRouter(prefix="/users", tags=["Users"])
campaign_router = APIRouter(prefix="/campaigns", tags=["Campaigns"])
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
class UserRole(str):
    ADMIN = "admin"
    FACILITATOR = "facilitator"
    ANALYST = "analyst"
    PARTICIPANT = "participant"
    SPONSOR = "sponsor"

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: str = "participant"
    tenant_id: Optional[str] = None

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
    is_active: bool = True
    pseudonym_id: Optional[str] = None

class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    tenant_id: Optional[str] = None
    is_active: bool

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

# --- Campaign Models ---
class CampaignStatus(str):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    CLOSED = "closed"

class CampaignCreate(BaseModel):
    name: str
    description: Optional[str] = None
    objective: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    script_id: Optional[str] = None

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
class SessionStatus(str):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ABANDONED = "abandoned"

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

# --- Chat Models ---
class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
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

# ============== VAL CHAT SERVICE ==============

class VALChatService:
    def __init__(self):
        self.api_key = os.environ.get('EMERGENT_LLM_KEY')
        self.active_chats: Dict[str, LlmChat] = {}
    
    def get_system_prompt(self, campaign_objective: str = "") -> str:
        return f"""Eres VAL, una facilitadora conversacional experta en coaching ontológico e Investigación Acción Participativa (IAP).

Tu rol es:
1. Facilitar diálogos reflexivos y generativos
2. Escuchar activamente y hacer preguntas poderosas
3. Ayudar a los participantes a explorar sus experiencias y perspectivas
4. Mantener un espacio seguro y confidencial
5. Extraer insights valiosos de las conversaciones

Objetivo de la campaña: {campaign_objective or "Explorar experiencias organizacionales"}

Principios de facilitación:
- Usa preguntas abiertas que inviten a la reflexión
- Valida las emociones y experiencias compartidas
- Busca patrones y temas emergentes
- Mantén la neutralidad y evita juicios
- Fomenta la profundización en los temas importantes

Responde siempre en español de manera cálida y profesional. Limita tus respuestas a 2-3 párrafos máximo."""

    async def get_or_create_chat(self, session_id: str, campaign_objective: str = "") -> LlmChat:
        if session_id not in self.active_chats:
            chat = LlmChat(
                api_key=self.api_key,
                session_id=session_id,
                system_message=self.get_system_prompt(campaign_objective)
            )
            chat.with_model("gemini", "gemini-2.5-flash")
            self.active_chats[session_id] = chat
        return self.active_chats[session_id]
    
    async def send_message(self, session_id: str, message: str, campaign_objective: str = "") -> str:
        chat = await self.get_or_create_chat(session_id, campaign_objective)
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
    doc["created_at"] = doc["created_at"].isoformat()
    doc["updated_at"] = doc["updated_at"].isoformat()
    
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
        is_active=current_user.get("is_active", True)
    )

# ============== TENANT ROUTES ==============

@tenant_router.post("/", response_model=Tenant)
async def create_tenant(tenant_data: TenantCreate, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["admin"]:
        raise HTTPException(status_code=403, detail="Solo administradores pueden crear tenants")
    
    tenant = Tenant(**tenant_data.model_dump())
    doc = tenant.model_dump()
    doc["created_at"] = doc["created_at"].isoformat()
    doc["updated_at"] = doc["updated_at"].isoformat()
    
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

# ============== CAMPAIGN ROUTES ==============

@campaign_router.post("/", response_model=Campaign)
async def create_campaign(campaign_data: CampaignCreate, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["admin", "facilitator"]:
        raise HTTPException(status_code=403, detail="No tiene permisos para crear campañas")
    
    campaign = Campaign(
        **campaign_data.model_dump(),
        tenant_id=current_user.get("tenant_id", "default"),
        created_by=current_user["id"]
    )
    
    doc = campaign.model_dump()
    doc["created_at"] = doc["created_at"].isoformat()
    doc["updated_at"] = doc["updated_at"].isoformat()
    if doc.get("start_date"):
        doc["start_date"] = doc["start_date"].isoformat()
    if doc.get("end_date"):
        doc["end_date"] = doc["end_date"].isoformat()
    
    await db.campaigns.insert_one(doc)
    return campaign

@campaign_router.get("/", response_model=List[Campaign])
async def list_campaigns(current_user: dict = Depends(get_current_user)):
    query = {}
    if current_user["role"] == "participant":
        query["status"] = "active"
    
    campaigns = await db.campaigns.find(query, {"_id": 0}).to_list(100)
    return campaigns

@campaign_router.get("/{campaign_id}", response_model=Campaign)
async def get_campaign(campaign_id: str, current_user: dict = Depends(get_current_user)):
    campaign = await db.campaigns.find_one({"id": campaign_id}, {"_id": 0})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaña no encontrada")
    return campaign

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

# ============== CONSENT ROUTES ==============

@consent_router.post("/", response_model=Consent)
async def create_consent(consent_data: ConsentCreate, current_user: dict = Depends(get_current_user)):
    # Check if campaign exists
    campaign = await db.campaigns.find_one({"id": consent_data.campaign_id}, {"_id": 0})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaña no encontrada")
    
    # Check for existing consent
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
    
    doc = consent.model_dump()
    doc["created_at"] = doc["created_at"].isoformat()
    doc["updated_at"] = doc["updated_at"].isoformat()
    
    await db.consents.insert_one(doc)
    
    # Update campaign participant count
    if consent_data.accepted:
        await db.campaigns.update_one(
            {"id": consent_data.campaign_id},
            {"$inc": {"participant_count": 1}}
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
    
    return {"message": "Consentimiento revocado exitosamente"}

# ============== SESSION ROUTES ==============

@session_router.post("/", response_model=Session)
async def create_session(session_data: SessionCreate, current_user: dict = Depends(get_current_user)):
    # Verify consent exists
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
    
    # Get campaign
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
        started_at=datetime.now(timezone.utc)
    )
    
    doc = session.model_dump()
    doc["created_at"] = doc["created_at"].isoformat()
    doc["updated_at"] = doc["updated_at"].isoformat()
    doc["started_at"] = doc["started_at"].isoformat() if doc["started_at"] else None
    
    await db.sessions.insert_one(doc)
    
    # Create transcript
    transcript = Transcript(
        session_id=session.id,
        campaign_id=session_data.campaign_id,
        tenant_id=campaign.get("tenant_id", "default"),
        user_id=current_user["id"]
    )
    transcript_doc = transcript.model_dump()
    transcript_doc["created_at"] = transcript_doc["created_at"].isoformat()
    transcript_doc["updated_at"] = transcript_doc["updated_at"].isoformat()
    await db.transcripts.insert_one(transcript_doc)
    
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
    
    # Close VAL chat
    val_service.close_session(session_id)
    
    return {"message": "Sesión completada exitosamente"}

# ============== CHAT ROUTES ==============

@chat_router.post("/message", response_model=ChatResponse)
async def send_chat_message(chat_request: ChatRequest, current_user: dict = Depends(get_current_user)):
    # Verify session
    session = await db.sessions.find_one({"id": chat_request.session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    
    if session["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="No tiene acceso a esta sesión")
    
    if session["status"] != "in_progress":
        raise HTTPException(status_code=400, detail="La sesión no está activa")
    
    # Get campaign objective
    campaign = await db.campaigns.find_one({"id": session["campaign_id"]}, {"_id": 0})
    campaign_objective = campaign.get("objective", "") if campaign else ""
    
    # Send to VAL
    response = await val_service.send_message(
        chat_request.session_id,
        chat_request.message,
        campaign_objective
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
        "active_consents": total_consents
    }

# ============== HEALTH CHECK ==============

@api_router.get("/")
async def root():
    return {"message": "DigiKawsay API v0.1.0", "status": "healthy"}

@api_router.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}

# ============== INCLUDE ROUTERS ==============

api_router.include_router(auth_router)
api_router.include_router(tenant_router)
api_router.include_router(user_router)
api_router.include_router(campaign_router)
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
