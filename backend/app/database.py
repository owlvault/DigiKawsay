"""Database connection and utilities."""

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from typing import Optional
import logging

from app.config import settings

logger = logging.getLogger(__name__)

# Global database client and instance
_client: Optional[AsyncIOMotorClient] = None
_db: Optional[AsyncIOMotorDatabase] = None


def get_client() -> AsyncIOMotorClient:
    """Get MongoDB client instance."""
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(settings.MONGO_URL)
    return _client


def get_database() -> AsyncIOMotorDatabase:
    """Get database instance."""
    global _db
    if _db is None:
        client = get_client()
        _db = client[settings.DB_NAME]
    return _db


async def init_database():
    """Initialize database connection and create indexes."""
    db = get_database()
    
    indexes_created = 0
    indexes_failed = 0
    
    async def safe_create_index(collection, index_spec, **kwargs):
        nonlocal indexes_created, indexes_failed
        try:
            await db[collection].create_index(index_spec, **kwargs)
            indexes_created += 1
        except Exception:
            indexes_failed += 1
    
    # Users collection
    await safe_create_index("users", "email", unique=True)
    await safe_create_index("users", "tenant_id")
    await safe_create_index("users", "role")
    await safe_create_index("users", [("email", 1), ("is_active", 1)])
    
    # Sessions collection
    await safe_create_index("sessions", "participant_id")
    await safe_create_index("sessions", "campaign_id")
    await safe_create_index("sessions", "status")
    await safe_create_index("sessions", [("campaign_id", 1), ("status", 1)])
    await safe_create_index("sessions", "created_at")
    
    # Campaigns collection
    await safe_create_index("campaigns", "tenant_id")
    await safe_create_index("campaigns", "status")
    await safe_create_index("campaigns", [("tenant_id", 1), ("status", 1)])
    
    # Insights collection
    await safe_create_index("insights", "campaign_id")
    await safe_create_index("insights", "tenant_id")
    await safe_create_index("insights", "category")
    await safe_create_index("insights", "status")
    await safe_create_index("insights", [("campaign_id", 1), ("status", 1)])
    
    # Audit logs collection
    await safe_create_index("audit_logs", "user_id")
    await safe_create_index("audit_logs", "action")
    await safe_create_index("audit_logs", "resource_type")
    await safe_create_index("audit_logs", "tenant_id")
    await safe_create_index("audit_logs", "timestamp")
    await safe_create_index("audit_logs", [("tenant_id", 1), ("timestamp", -1)])
    await safe_create_index("audit_logs", [("user_id", 1), ("action", 1)])
    
    # PII Vault collection
    await safe_create_index("pii_vault", "pseudonym", unique=True, sparse=True)
    await safe_create_index("pii_vault", "tenant_id")
    
    # Consent policies
    await safe_create_index("consent_policies", "tenant_id")
    await safe_create_index("consent_policies", [("tenant_id", 1), ("is_active", 1)])
    
    # Scripts collection
    await safe_create_index("scripts", "campaign_id")
    await safe_create_index("scripts", [("campaign_id", 1), ("version", -1)])
    
    # Network snapshots
    await safe_create_index("network_snapshots", "campaign_id")
    await safe_create_index("network_snapshots", "created_at")
    
    # Initiatives
    await safe_create_index("initiatives", "campaign_id")
    await safe_create_index("initiatives", "status")
    await safe_create_index("initiatives", [("campaign_id", 1), ("priority_score", -1)])
    
    # Rituals
    await safe_create_index("rituals", "campaign_id")
    await safe_create_index("rituals", "status")
    
    # Access policies
    await safe_create_index("access_policies", "tenant_id")
    await safe_create_index("access_policies", [("tenant_id", 1), ("is_active", 1)])
    
    # Login attempts tracking
    await safe_create_index("login_attempts", "email")
    await safe_create_index("login_attempts", "ip_address")
    await safe_create_index("login_attempts", "timestamp")
    await safe_create_index("login_attempts", [("email", 1), ("timestamp", -1)])
    await safe_create_index("login_attempts", "timestamp", expireAfterSeconds=2592000)
    
    logger.info(f"MongoDB indexes initialized: {indexes_created} created, {indexes_failed} skipped")
    return indexes_created, indexes_failed


async def close_database():
    """Close database connection."""
    global _client
    if _client is not None:
        _client.close()
        _client = None
        logger.info("Database connection closed")


# Shortcut for direct database access
db = get_database()
