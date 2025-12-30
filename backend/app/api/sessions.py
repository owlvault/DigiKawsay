"""Session and Chat routes."""

from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException

from app.database import get_database
from app.utils.serializers import serialize_document
from app.core.dependencies import get_current_user
from app.services.chat_service import val_service
from app.models import (
    Session, SessionCreate, ChatRequest, ChatResponse, Transcript
)

session_router = APIRouter(prefix="/sessions", tags=["Sessions"])
chat_router = APIRouter(prefix="/chat", tags=["Chat"])


# ============== SESSION ROUTES ==============

@session_router.post("/", response_model=Session)
async def create_session(
    session_data: SessionCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a new chat session."""
    db = get_database()
    
    # Verify consent
    consent = await db.consents.find_one({
        "user_id": current_user["id"],
        "campaign_id": session_data.campaign_id,
        "accepted": True,
        "revoked_at": None
    })
    if not consent:
        raise HTTPException(
            status_code=403,
            detail="Requiere consentimiento activo"
        )
    
    campaign = await db.campaigns.find_one({"id": session_data.campaign_id}, {"_id": 0})
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaña no encontrada")
    
    session = Session(
        user_id=current_user["id"],
        campaign_id=session_data.campaign_id,
        tenant_id=campaign.get("tenant_id", "default"),
        script_id=session_data.script_id,
        segment_id=session_data.segment_id
    )
    await db.sessions.insert_one(serialize_document(session.model_dump()))
    
    # Create transcript
    transcript = Transcript(
        session_id=session.id,
        user_id=current_user["id"],
        campaign_id=session_data.campaign_id,
        tenant_id=campaign.get("tenant_id", "default")
    )
    await db.transcripts.insert_one(serialize_document(transcript.model_dump()))
    
    # Update campaign stats
    await db.campaigns.update_one(
        {"id": session_data.campaign_id},
        {"$inc": {"session_count": 1}}
    )
    
    return session


@session_router.get("/")
async def list_sessions(
    campaign_id: Optional[str] = None,
    status: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """List sessions."""
    db = get_database()
    query = {}
    
    if current_user["role"] in ["admin", "facilitator"]:
        if campaign_id:
            query["campaign_id"] = campaign_id
        if status:
            query["status"] = status
    else:
        query["user_id"] = current_user["id"]
    
    sessions = await db.sessions.find(query, {"_id": 0}).to_list(100)
    return sessions


@session_router.get("/{session_id}")
async def get_session(
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get a specific session."""
    db = get_database()
    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    
    if (session["user_id"] != current_user["id"] 
        and current_user["role"] not in ["admin", "facilitator"]):
        raise HTTPException(status_code=403, detail="Sin permisos")
    
    return session


@session_router.post("/{session_id}/start")
async def start_session(
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Start a session."""
    db = get_database()
    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    if not session or session["user_id"] != current_user["id"]:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    
    await db.sessions.update_one(
        {"id": session_id},
        {"$set": {
            "status": "in_progress",
            "started_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    return {"message": "Sesión iniciada"}


@session_router.post("/{session_id}/complete")
async def complete_session(
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Complete a session."""
    db = get_database()
    session = await db.sessions.find_one({"id": session_id}, {"_id": 0})
    if not session or session["user_id"] != current_user["id"]:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    
    await db.sessions.update_one(
        {"id": session_id},
        {"$set": {
            "status": "completed",
            "ended_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    await db.campaigns.update_one(
        {"id": session["campaign_id"]},
        {"$inc": {"completed_sessions": 1}}
    )
    val_service.close_session(session_id)
    return {"message": "Sesión completada"}


# ============== CHAT ROUTES ==============

@chat_router.post("/message")
async def send_chat_message(
    chat_request: ChatRequest,
    current_user: dict = Depends(get_current_user)
):
    """Send a message to VAL."""
    db = get_database()
    session = await db.sessions.find_one({"id": chat_request.session_id}, {"_id": 0})
    
    if (not session 
        or session["user_id"] != current_user["id"] 
        or session["status"] != "in_progress"):
        raise HTTPException(status_code=400, detail="Sesión inválida")
    
    campaign = await db.campaigns.find_one({"id": session["campaign_id"]}, {"_id": 0})
    campaign_objective = campaign.get("objective", "") if campaign else ""
    
    script_context = ""
    if session.get("script_id"):
        script = await db.scripts.find_one({"id": session["script_id"]}, {"_id": 0})
        if script and script.get("steps"):
            steps_text = "\n".join([f"- {s.get('question', '')}" for s in script["steps"][:5]])
            script_context = f"\nGuión:\n{steps_text}"
    
    response = await val_service.send_message(
        chat_request.session_id,
        chat_request.message,
        campaign_objective,
        script_context
    )
    
    now = datetime.now(timezone.utc)
    await db.transcripts.update_one(
        {"session_id": chat_request.session_id},
        {"$push": {"messages": {"$each": [
            {"role": "user", "content": chat_request.message, "timestamp": now.isoformat()},
            {"role": "assistant", "content": response, "timestamp": now.isoformat()}
        ]}}}
    )
    
    return ChatResponse(
        session_id=chat_request.session_id,
        message=response,
        timestamp=now
    )


@chat_router.get("/history/{session_id}")
async def get_chat_history(
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get chat history for a session."""
    db = get_database()
    transcript = await db.transcripts.find_one({"session_id": session_id}, {"_id": 0})
    return {"messages": transcript.get("messages", []) if transcript else []}
