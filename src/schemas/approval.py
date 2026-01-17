"""
Approval Schemas
Pydantic models for approval workflow
"""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ApprovalCreate(BaseModel):
    """Schema for creating approval/rejection"""
    comments: Optional[str] = None


class ApprovalResponse(BaseModel):
    """Schema for approval response"""
    id: int
    expense_id: int
    approver_id: int
    level: str
    status: str
    comments: Optional[str] = None
    created_at: datetime
    reviewed_at: Optional[datetime] = None

    class Config:
        from_attributes = True