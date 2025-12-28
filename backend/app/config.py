"""Application configuration and settings."""

import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore"  # Ignore extra fields from .env
    )
    
    # Application
    APP_NAME: str = "DigiKawsay"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # MongoDB
    MONGO_URL: str = "mongodb://localhost:27017"
    DB_NAME: str = "test_database"
    
    # JWT Authentication
    JWT_SECRET_KEY: str = "default_secret_key_change_in_prod"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    
    # Aliases for compatibility
    @property
    def SECRET_KEY(self) -> str:
        return self.JWT_SECRET_KEY
    
    @property
    def ALGORITHM(self) -> str:
        return self.JWT_ALGORITHM
    
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
    PII_VAULT_KEY: str = "default_vault_key_change_in_prod"
    
    @property
    def PII_VAULT_ENCRYPTION_KEY(self) -> str:
        return self.PII_VAULT_KEY
    
    # CORS
    CORS_ORIGINS: str = "*"
    
    @property
    def cors_origins_list(self) -> List[str]:
        return self.CORS_ORIGINS.split(',')
    
    # LLM Integration
    EMERGENT_LLM_KEY: str = ""


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Global settings instance
settings = get_settings()
