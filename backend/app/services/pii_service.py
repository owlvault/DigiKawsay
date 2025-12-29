"""PII Vault and Pseudonymization services."""

import re
import uuid
import hashlib
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple

from app.config import settings
from app.database import get_database
from app.utils.serializers import serialize_document
from app.utils.validators import generate_pseudonym
from app.models.compliance import PIIVaultEntry


def encrypt_identity(identity: str) -> str:
    """Simple encryption for vault - in production use proper encryption."""
    return hashlib.sha256(
        f"{identity}{settings.PII_VAULT_ENCRYPTION_KEY}".encode()
    ).hexdigest()


class PIIVaultService:
    """Service for managing PII vault mappings."""
    
    @staticmethod
    async def create_mapping(
        user_id: str,
        tenant_id: str,
        campaign_id: Optional[str] = None
    ) -> str:
        """Create a new pseudonym mapping in the vault."""
        db = get_database()
        
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
        """Get existing pseudonym for user."""
        db = get_database()
        
        encrypted_id = encrypt_identity(user_id)
        entry = await db.pii_vault.find_one({
            "encrypted_identity": encrypted_id,
            "tenant_id": tenant_id,
            "is_deleted": False
        }, {"_id": 0})
        return entry.get("pseudonym_id") if entry else None
    
    @staticmethod
    async def resolve_identity(
        pseudonym_id: str,
        tenant_id: str,
        requester_id: str
    ) -> Optional[str]:
        """Resolve pseudonym to identity - REQUIRES APPROVED REIDENTIFICATION REQUEST."""
        db = get_database()
        
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
            {"$set": {
                "status": "resolved",
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        # Return user info (need to look up by encrypted identity)
        users = await db.users.find({}, {"_id": 0, "hashed_password": 0}).to_list(1000)
        for user in users:
            if encrypt_identity(user["id"]) == entry["encrypted_identity"]:
                return user["id"]
        
        return None
    
    @staticmethod
    async def delete_mapping(pseudonym_id: str, tenant_id: str):
        """Soft delete a mapping (for consent revocation with delete_all)."""
        db = get_database()
        
        await db.pii_vault.update_one(
            {"pseudonym_id": pseudonym_id, "tenant_id": tenant_id},
            {"$set": {
                "is_deleted": True,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )


class PseudonymizationService:
    """Service for pseudonymizing text content."""
    
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
    
    def _generate_replacement(
        self,
        match_type: str,
        original: str,
        session_id: str
    ) -> str:
        """Generate a replacement string for detected PII."""
        hash_val = hashlib.sha256(
            f"{original}{session_id}".encode()
        ).hexdigest()[:6].upper()
        
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
    
    def pseudonymize_text(
        self,
        text: str,
        session_id: str = ""
    ) -> Tuple[str, List[Dict]]:
        """Enhanced pseudonymization with tracking of redactions."""
        result = text
        redactions = []
        
        for pattern_name, pattern in self.patterns.items():
            for match in re.finditer(pattern, result):
                original = match.group()
                replacement = self._generate_replacement(
                    pattern_name, original, session_id
                )
                redactions.append({
                    "type": pattern_name,
                    "original_hash": hashlib.sha256(original.encode()).hexdigest()[:8],
                    "replacement": replacement
                })
                result = result.replace(original, replacement, 1)
        
        return result, redactions
    
    async def pseudonymize_transcript(
        self,
        transcript_id: str
    ) -> Dict[str, Any]:
        """Pseudonymize transcript and store mapping in vault."""
        db = get_database()
        
        transcript = await db.transcripts.find_one(
            {"id": transcript_id},
            {"_id": 0}
        )
        
        if not transcript or transcript.get("is_pseudonymized"):
            return {"success": False, "reason": "Already pseudonymized or not found"}
        
        session_id = transcript.get("session_id", "")
        user_id = transcript.get("user_id")
        tenant_id = transcript.get("tenant_id", "default")
        
        # Create or get pseudonym in vault
        pseudonym_id = await pii_vault_service.get_pseudonym(user_id, tenant_id)
        if not pseudonym_id:
            pseudonym_id = await pii_vault_service.create_mapping(
                user_id, tenant_id, transcript.get("campaign_id")
            )
        
        pseudonymized_messages = []
        total_redactions = []
        
        for msg in transcript.get("messages", []):
            new_msg = msg.copy()
            if msg.get("role") == "user":
                new_content, redactions = self.pseudonymize_text(
                    msg.get("content", ""), session_id
                )
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


class SuppressionService:
    """Service for small group suppression."""
    
    @staticmethod
    async def check_and_suppress_insights(
        campaign_id: str,
        threshold: int = None
    ) -> Dict[str, Any]:
        """Check insights for small group suppression."""
        db = get_database()
        threshold = threshold or settings.SMALL_GROUP_THRESHOLD
        
        # Get all insights grouped by source characteristics
        insights = await db.insights.find(
            {"campaign_id": campaign_id},
            {"_id": 0}
        ).to_list(1000)
        
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
            unique_sources = len(set(
                i.get("source_session_id")
                for i in group_insights
                if i.get("source_session_id")
            ))
            
            should_suppress = unique_sources < threshold and unique_sources > 0
            
            for insight in group_insights:
                if should_suppress and not insight.get("is_suppressed"):
                    await db.insights.update_one(
                        {"id": insight["id"]},
                        {"$set": {
                            "is_suppressed": True,
                            "updated_at": datetime.now(timezone.utc).isoformat()
                        }}
                    )
                    suppressed += 1
                elif not should_suppress and insight.get("is_suppressed"):
                    await db.insights.update_one(
                        {"id": insight["id"]},
                        {"$set": {
                            "is_suppressed": False,
                            "updated_at": datetime.now(timezone.utc).isoformat()
                        }}
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
    async def get_visible_insights(
        campaign_id: str,
        user_role: str
    ) -> List[Dict]:
        """Get insights respecting suppression rules."""
        db = get_database()
        query = {"campaign_id": campaign_id}
        
        # Only admins and security officers can see suppressed insights
        if user_role not in ["admin", "security_officer"]:
            query["is_suppressed"] = {"$ne": True}
        
        insights = await db.insights.find(query, {"_id": 0}).to_list(500)
        return insights


# Global service instances
pii_vault_service = PIIVaultService()
pseudonymization_service = PseudonymizationService()
suppression_service = SuppressionService()
