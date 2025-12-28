"""Application configuration and settings."""

import os
from typing import List
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    APP_NAME: str = "DigiKawsay"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # MongoDB
    MONGO_URL: str = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
    DB_NAME: str = os.environ.get('DB_NAME', 'test_database')
    
    # JWT Authentication
    SECRET_KEY: str = os.environ.get('JWT_SECRET_KEY', 'default_secret_key_change_in_prod')
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    
    # Security - Hardening (Phase 8)
    SESSION_TIMEOUT_MINUTES: int = 30
    PASSWORD_MIN_LENGTH: int = 8
    MAX_LOGIN_ATTEMPTS: int = 5
    LOGIN_LOCKOUT_MINUTES: int = 15
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 30
    LOGIN_RATE_LIMIT_PER_MINUTE: int = 10
    
    # Privacy & Compliance
    SMALL_GROUP_THRESHOLD: int = 5
    PII_VAULT_ENCRYPTION_KEY: str = os.environ.get('PII_VAULT_KEY', 'default_vault_key_change_in_prod')
    
    # CORS
    CORS_ORIGINS: str = os.environ.get('CORS_ORIGINS', '*')
    
    @property
    def cors_origins_list(self) -> List[str]:
        return self.CORS_ORIGINS.split(',')
    
    # LLM Integration
    EMERGENT_LLM_KEY: str = os.environ.get('EMERGENT_LLM_KEY', '')
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Global settings instance
settings = get_settings()
