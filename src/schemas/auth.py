"""
Authentication Schemas
Pydantic models for authentication requests and responses
"""

from pydantic import BaseModel
from typing import Optional


class Token(BaseModel):
    """JWT token response"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Data extracted from JWT token"""
    username: Optional[str] = None
    user_id: Optional[int] = None


class UserLogin(BaseModel):
    """Login request schema"""
    username: str
    password: str