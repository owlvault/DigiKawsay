"""Validation utilities."""

import re
import uuid
import string
import random
from typing import Tuple

from app.config import settings


def validate_password_strength(password: str) -> Tuple[bool, str]:
    """Validate password strength.
    
    Returns:
        Tuple of (is_valid, message)
    """
    if len(password) < settings.PASSWORD_MIN_LENGTH:
        return False, f"La contraseña debe tener al menos {settings.PASSWORD_MIN_LENGTH} caracteres"
    
    if not re.search(r'[A-Za-z]', password):
        return False, "La contraseña debe contener al menos una letra"
    
    if not re.search(r'\d', password):
        return False, "La contraseña debe contener al menos un número"
    
    return True, "Contraseña válida"


def generate_pseudonym() -> str:
    """Generate a unique pseudonym for anonymization."""
    return f"P-{uuid.uuid4().hex[:8].upper()}"


def generate_invite_code(length: int = 8) -> str:
    """Generate a random invite code."""
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choices(chars, k=length))


def sanitize_email_for_log(email: str) -> str:
    """Sanitize email for logging (show only first 2 chars)."""
    if '@' in email:
        local, domain = email.split('@')
        return f"{local[:2]}***@{domain}"
    return email[:2] + "***"
