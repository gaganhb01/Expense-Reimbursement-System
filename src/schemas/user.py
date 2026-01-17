"""
User Schemas
Pydantic models for user-related requests and responses
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class UserRoleEnum(str, Enum):
    """User role enumeration"""
    EMPLOYEE = "employee"
    MANAGER = "manager"
    HR = "hr"
    FINANCE = "finance"
    ADMIN = "admin"


class UserGradeEnum(str, Enum):
    """User grade enumeration"""
    A = "A"
    B = "B"
    C = "C"
    D = "D"


class UserBase(BaseModel):
    """Base user schema with common fields"""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    full_name: str = Field(..., min_length=1, max_length=200)
    employee_id: str = Field(..., min_length=3, max_length=50)
    department: str
    phone: Optional[str] = None


class UserCreate(UserBase):
    """Schema for creating a new user"""
    password: str = Field(..., min_length=8)
    role: UserRoleEnum = UserRoleEnum.EMPLOYEE
    grade: UserGradeEnum = UserGradeEnum.A
    can_claim_expenses: bool = True


class UserUpdate(BaseModel):
    """Schema for updating user information"""
    full_name: Optional[str] = None
    department: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[UserRoleEnum] = None
    grade: Optional[UserGradeEnum] = None
    can_claim_expenses: Optional[bool] = None
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    """Schema for user response"""
    id: int
    role: UserRoleEnum
    grade: UserGradeEnum
    is_active: bool
    can_claim_expenses: bool
    created_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True