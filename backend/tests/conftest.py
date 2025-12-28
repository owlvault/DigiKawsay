"""Pytest configuration and fixtures."""

import pytest
import asyncio
from typing import Generator, AsyncGenerator
from httpx import AsyncClient
from motor.motor_asyncio import AsyncIOMotorClient

from app.config import settings
from app.database import get_database


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def db() -> AsyncGenerator:
    """Get test database."""
    database = get_database()
    yield database


@pytest.fixture
async def test_user(db) -> dict:
    """Create a test user."""
    from app.utils.auth import get_password_hash
    import uuid
    
    user = {
        "id": str(uuid.uuid4()),
        "email": "test@example.com",
        "full_name": "Test User",
        "hashed_password": get_password_hash("test123"),
        "role": "admin",
        "is_active": True,
    }
    await db.users.insert_one(user)
    yield user
    await db.users.delete_one({"id": user["id"]})


@pytest.fixture
def auth_headers(test_user) -> dict:
    """Get authentication headers."""
    from app.utils.auth import create_access_token
    
    token = create_access_token(data={"sub": test_user["id"]})
    return {"Authorization": f"Bearer {token}"}
