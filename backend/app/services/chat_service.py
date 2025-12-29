"""VAL Chat Service for conversational AI."""

import os
from typing import Dict, Optional

from emergentintegrations.llm.chat import LlmChat, UserMessage

from app.config import settings


class VALChatService:
    """Service for VAL conversational AI."""
    
    def __init__(self):
        self.api_key = settings.EMERGENT_LLM_KEY or os.environ.get('EMERGENT_LLM_KEY')
        self.active_chats: Dict[str, LlmChat] = {}
    
    def get_system_prompt(
        self,
        campaign_objective: str = "",
        script_context: str = ""
    ) -> str:
        """Generate the system prompt for VAL."""
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
    
    async def get_or_create_chat(
        self,
        session_id: str,
        campaign_objective: str = "",
        script_context: str = ""
    ) -> LlmChat:
        """Get existing chat or create a new one."""
        if session_id not in self.active_chats:
            chat = LlmChat(
                api_key=self.api_key,
                session_id=session_id,
                system_message=self.get_system_prompt(
                    campaign_objective,
                    script_context
                )
            )
            chat.with_model("gemini", "gemini-2.5-flash")
            self.active_chats[session_id] = chat
        return self.active_chats[session_id]
    
    async def send_message(
        self,
        session_id: str,
        message: str,
        campaign_objective: str = "",
        script_context: str = ""
    ) -> str:
        """Send a message and get VAL's response."""
        chat = await self.get_or_create_chat(
            session_id,
            campaign_objective,
            script_context
        )
        response = await chat.send_message(UserMessage(text=message))
        return response
    
    def close_session(self, session_id: str):
        """Close a chat session."""
        if session_id in self.active_chats:
            del self.active_chats[session_id]


# Global service instance
val_service = VALChatService()
