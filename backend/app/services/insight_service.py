"""Insight Extraction Service."""

import json
import logging
import os
from typing import Dict, List, Any

from emergentintegrations.llm.chat import LlmChat, UserMessage

from app.config import settings
from app.database import get_database
from app.utils.serializers import serialize_document
from app.models.insight import Insight

logger = logging.getLogger(__name__)


class InsightExtractionService:
    """Service for extracting insights from transcripts using AI."""
    
    def __init__(self):
        self.api_key = settings.EMERGENT_LLM_KEY or os.environ.get('EMERGENT_LLM_KEY')
    
    async def extract_insights_from_transcript(
        self,
        transcript_id: str,
        campaign_id: str,
        tenant_id: str
    ) -> List[Dict]:
        """Extract insights from a transcript using AI."""
        db = get_database()
        
        transcript = await db.transcripts.find_one(
            {"id": transcript_id},
            {"_id": 0}
        )
        if not transcript:
            return []
        
        campaign = await db.campaigns.find_one(
            {"id": campaign_id},
            {"_id": 0}
        )
        objective = campaign.get("objective", "") if campaign else ""
        
        conversation = "\n".join([
            f"{'Participante' if m['role'] == 'user' else 'VAL'}: {m['content']}"
            for m in transcript.get("messages", [])
        ])
        
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
            chat = LlmChat(
                api_key=self.api_key,
                session_id=f"extraction-{transcript_id}",
                system_message="Eres un experto en análisis cualitativo organizacional."
            )
            chat.with_model("gemini", "gemini-2.5-flash")
            response = await chat.send_message(UserMessage(text=extraction_prompt))
            
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
                await db.insights.insert_one(
                    serialize_document(insight.model_dump())
                )
                created_insights.append(insight.model_dump())
            
            # Mark transcript as processed
            await db.transcripts.update_one(
                {"id": transcript_id},
                {"$set": {"insights_extracted": True}}
            )
            
            return created_insights
            
        except Exception as e:
            logger.error(f"Error extracting insights: {e}")
            return []


# Global service instance
insight_extraction_service = InsightExtractionService()
