"""
User Model
Represents system users with role-based access control
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from src.config.database import Base


class UserRole(str, enum.Enum):
    """User roles"""
    EMPLOYEE = "employee"
    MANAGER = "manager"
    HR = "hr"
    FINANCE = "finance"
    ADMIN = "admin"


class UserGrade(str, enum.Enum):
    """Employee grades with different expense limits"""
    A = "A"
    B = "B"
    C = "C"
    D = "D"


class User(Base):
    """User model"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=False)
    employee_id = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    
    # Role and Grade
    role = Column(Enum(UserRole), default=UserRole.EMPLOYEE, nullable=False)
    grade = Column(Enum(UserGrade), default=UserGrade.A, nullable=False)
    
    # Department and Contact
    department = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    
    # Permissions
    is_active = Column(Boolean, default=True)
    can_claim_expenses = Column(Boolean, default=True)
    
    # ✅✅✅ NEW: Secure Authentication System ✅✅✅
    
    # Invitation system (for new users created by admin)
    invitation_token = Column(String(255), unique=True, nullable=True, index=True)
    invitation_sent_at = Column(DateTime, nullable=True)
    invitation_expires_at = Column(DateTime, nullable=True)
    password_set_at = Column(DateTime, nullable=True)
    is_password_set = Column(Boolean, default=False, nullable=False)
    
    # Password reset system (forgot password with OTP)
    reset_token = Column(String(255), nullable=True, index=True)
    reset_token_expires_at = Column(DateTime, nullable=True)
    last_password_reset = Column(DateTime, nullable=True)
    
    # Account status tracking
    account_status = Column(String(50), default='pending_setup', nullable=False)
    # Values: 'pending_setup' (new user, not activated)
    #         'active' (user set password, can login)
    #         'suspended' (account temporarily disabled)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    
    # Relationships
    expenses = relationship("Expense", back_populates="employee", foreign_keys="Expense.employee_id")
    approvals = relationship("Approval", back_populates="approver", foreign_keys="Approval.approver_id")
    notifications = relationship("Notification", back_populates="user")
    audit_logs = relationship("AuditLog", back_populates="user")
    
    def __repr__(self):
        return f"<User {self.username} ({self.role.value})>"
    
    def has_permission(self, permission: str) -> bool:
        """Check if user has specific permission"""
        permission_map = {
            "claim_expense": self.can_claim_expenses and self.is_active,
            "approve_expense": self.role in [UserRole.MANAGER, UserRole.HR, UserRole.FINANCE, UserRole.ADMIN],
            "view_all_expenses": self.role in [UserRole.MANAGER, UserRole.HR, UserRole.FINANCE, UserRole.ADMIN],
            "manage_users": self.role == UserRole.ADMIN,
            "view_reports": self.role in [UserRole.MANAGER, UserRole.HR, UserRole.FINANCE, UserRole.ADMIN],
        }
        return permission_map.get(permission, False)
    
    def get_expense_limits(self) -> dict:
        """Get expense limits based on user grade"""
        from src.config.settings import settings
        return settings.EXPENSE_RULES.get(self.grade.value, {})
    
    # ✅ NEW: Helper methods for authentication
    
    def is_invitation_valid(self) -> bool:
        """Check if invitation link is still valid"""
        if not self.invitation_token:
            return False
        if not self.invitation_expires_at:
            return False
        return self.invitation_expires_at > datetime.utcnow()
    
    def is_reset_token_valid(self) -> bool:
        """Check if password reset token (OTP) is still valid"""
        if not self.reset_token:
            return False
        if not self.reset_token_expires_at:
            return False
        return self.reset_token_expires_at > datetime.utcnow()
    
    def can_login(self) -> bool:
        """Check if user can login"""
        return (
            self.is_active and 
            self.is_password_set and 
            self.account_status == 'active'
        )