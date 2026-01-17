"""
Expense Model
Represents expense claims submitted by employees
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Enum, ForeignKey, Text, Boolean, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from src.config.database import Base


class ExpenseCategory(str, enum.Enum):
    """Expense categories"""
    TRAVEL = "travel"
    FOOD = "food"
    MEDICAL = "medical"
    ACCOMMODATION = "accommodation"
    COMMUNICATION = "communication"
    OTHER = "other"


class ExpenseStatus(str, enum.Enum):
    """Expense status"""
    DRAFT = "draft"
    SUBMITTED = "submitted"
    MANAGER_REVIEW = "manager_review"
    HR_REVIEW = "hr_review"
    FINANCE_REVIEW = "finance_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    PAID = "paid"


class TravelMode(str, enum.Enum):
    """Travel modes"""
    BUS = "bus"
    TRAIN = "train"
    FLIGHT_ECONOMY = "flight_economy"
    FLIGHT_BUSINESS = "flight_business"
    CAB = "cab"
    OWN_VEHICLE = "own_vehicle"


class Expense(Base):
    """Expense model"""
    __tablename__ = "expenses"
    
    id = Column(Integer, primary_key=True, index=True)
    expense_number = Column(String, unique=True, index=True, nullable=False)
    
    # Employee information
    employee_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Expense details
    category = Column(Enum(ExpenseCategory), nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String, default="INR")
    expense_date = Column(DateTime, nullable=False)
    description = Column(Text, nullable=False)
    
    # Travel specific fields
    travel_mode = Column(Enum(TravelMode), nullable=True)
    travel_from = Column(String, nullable=True)
    travel_to = Column(String, nullable=True)
    
    # Bill information
    bill_file_path = Column(String, nullable=False)
    bill_file_name = Column(String, nullable=False)
    bill_number = Column(String, nullable=True)
    vendor_name = Column(String, nullable=True)
    
    # ✅✅✅ Self-Declaration Support (NEW) ✅✅✅
    is_self_declaration = Column(Boolean, default=False, nullable=False)
    declaration_reason = Column(Text, nullable=True)
    no_bill_category = Column(String(100), nullable=True)
    
    # AI Analysis
    ai_analysis = Column(JSON, nullable=True)  # Stores AI-generated analysis
    ai_summary = Column(Text, nullable=True)
    ai_recommendation = Column(String, nullable=True)  # approve, reject, review
    ai_confidence_score = Column(Float, nullable=True)
    is_valid_bill = Column(Boolean, nullable=True)
    has_gst = Column(Boolean, nullable=True)
    has_required_stamps = Column(Boolean, nullable=True)
    
    # Validation
    is_within_limits = Column(Boolean, default=False)
    validation_errors = Column(JSON, nullable=True)
    
    # ✅✅✅ Duplicate Detection (NEW) ✅✅✅
    file_hash = Column(String(64), nullable=True, index=True)  # SHA-256 hash for exact duplicate detection
    duplicate_check_status = Column(String(20), default='not_checked')  # not_checked, clean, suspected, confirmed_duplicate
    duplicate_of_expense_id = Column(Integer, ForeignKey('expenses.id'), nullable=True)  # Reference to original expense
    duplicate_detected_at = Column(DateTime, nullable=True)  # When duplicate was detected
    
    # Status and workflow
    status = Column(Enum(ExpenseStatus), default=ExpenseStatus.DRAFT)
    current_approver_level = Column(String, nullable=True)  # manager, hr, finance
    
    # Rejection
    rejection_reason = Column(Text, nullable=True)
    rejected_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    rejected_at = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    submitted_at = Column(DateTime, nullable=True)
    approved_at = Column(DateTime, nullable=True)
    paid_at = Column(DateTime, nullable=True)
    
    # Relationships
    employee = relationship("User", back_populates="expenses", foreign_keys=[employee_id])
    approvals = relationship("Approval", back_populates="expense", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="expense")
    
    def __repr__(self):
        return f"<Expense {self.expense_number} - {self.category.value} - {self.status.value}>"
    
    def get_next_approver_level(self) -> str:
        """Get the next approver level based on current status"""
        workflow = {
            ExpenseStatus.SUBMITTED: "manager",
            ExpenseStatus.MANAGER_REVIEW: "hr",
            ExpenseStatus.HR_REVIEW: "finance",
        }
        return workflow.get(self.status)
    
    def can_be_approved_by(self, user_role: str) -> bool:
        """Check if expense can be approved by given role"""
        approval_map = {
            ExpenseStatus.MANAGER_REVIEW: ["manager", "admin"],
            ExpenseStatus.HR_REVIEW: ["hr", "admin"],
            ExpenseStatus.FINANCE_REVIEW: ["finance", "admin"],
        }
        return user_role in approval_map.get(self.status, [])