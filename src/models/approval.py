"""
Approval Model
Represents approval workflow for expenses
"""

from sqlalchemy import Column, Integer, String, DateTime, Enum, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from src.config.database import Base


class ApprovalStatus(str, enum.Enum):
    """Approval status"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ApprovalLevel(str, enum.Enum):
    """Approval levels - HR REMOVED"""
    MANAGER = "manager"
    FINANCE = "finance"
    # ✅ HR REMOVED - Direct flow: MANAGER → FINANCE


class Approval(Base):
    """Approval model"""
    __tablename__ = "approvals"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Expense and Approver
    expense_id = Column(Integer, ForeignKey("expenses.id"), nullable=False)
    approver_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Approval details
    level = Column(Enum(ApprovalLevel), nullable=False)
    status = Column(Enum(ApprovalStatus), default=ApprovalStatus.PENDING)
    
    # Comments
    comments = Column(Text, nullable=True)
    
    # ✅ AI Analysis Summary
    ai_summary = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    reviewed_at = Column(DateTime, nullable=True)
    
    # Relationships
    expense = relationship("Expense", back_populates="approvals")
    approver = relationship("User", back_populates="approvals", foreign_keys=[approver_id])
    
    def __repr__(self):
        return f"<Approval {self.level.value} - {self.status.value}>"