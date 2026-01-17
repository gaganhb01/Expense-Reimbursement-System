"""
Notification Model
Represents notifications sent to users
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from src.config.database import Base


class NotificationType(str, enum.Enum):
    """Notification types"""
    EXPENSE_SUBMITTED = "expense_submitted"
    EXPENSE_APPROVED = "expense_approved"
    EXPENSE_REJECTED = "expense_rejected"
    APPROVAL_REQUIRED = "approval_required"
    COMMENT_ADDED = "comment_added"
    SYSTEM = "system"


class Notification(Base):
    """Notification model"""
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # User
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Notification details
    type = Column(Enum(NotificationType), nullable=False)
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    
    # Related expense (optional)
    expense_id = Column(Integer, ForeignKey("expenses.id"), nullable=True)
    
    # Status
    is_read = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    read_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="notifications")
    
    # ✅ ADD THIS: Expense relationship for eager loading
    expense = relationship("Expense", foreign_keys=[expense_id], lazy="select")
    
    def __repr__(self):
        return f"<Notification {self.type.value} - User {self.user_id}>"