"""
Audit Log Model
Tracks all user actions for compliance and auditing
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from datetime import datetime

from src.config.database import Base


class AuditLog(Base):
    """Audit log model"""
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # User who performed the action
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Action details
    action = Column(String, nullable=False)  # e.g., "create_expense", "approve_expense"
    entity_type = Column(String, nullable=False)  # e.g., "expense", "user"
    entity_id = Column(Integer, nullable=True)
    
    # Details
    description = Column(Text, nullable=False)
    changes = Column(JSON, nullable=True)  # Before/after values
    
    # Request information
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    
    # Related expense (if applicable)
    expense_id = Column(Integer, ForeignKey("expenses.id"), nullable=True)
    
    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="audit_logs")
    expense = relationship("Expense", back_populates="audit_logs")
    
    def __repr__(self):
        return f"<AuditLog {self.action} by User {self.user_id}>"