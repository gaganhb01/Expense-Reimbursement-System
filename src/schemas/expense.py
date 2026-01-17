"""
Enhanced Expense Schemas with Multi-Bill and Trip Support - Pydantic V2
"""

from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, List
from datetime import datetime, date
from enum import Enum


class ExpenseCategoryEnum(str, Enum):
    """Expense categories"""
    travel = "travel"
    food = "food"
    medical = "medical"
    accommodation = "accommodation"
    communication = "communication"
    other = "other"


class TravelModeEnum(str, Enum):
    """Travel modes"""
    bus = "bus"
    train = "train"
    flight_economy = "flight_economy"
    flight_business = "flight_business"
    cab = "cab"
    own_vehicle = "own_vehicle"


class ExpenseStatusEnum(str, Enum):
    """Expense status enumeration"""
    DRAFT = "draft"
    SUBMITTED = "submitted"
    MANAGER_REVIEW = "manager_review"
    HR_REVIEW = "hr_review"
    FINANCE_REVIEW = "finance_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    PAID = "paid"


class BillItemCreate(BaseModel):
    """Individual bill item for multi-bill upload"""
    category: ExpenseCategoryEnum
    amount: float = Field(gt=0, description="Amount must be positive")
    expense_date: date
    description: str = Field(min_length=10, max_length=500)
    travel_mode: Optional[TravelModeEnum] = None
    travel_from: Optional[str] = None
    travel_to: Optional[str] = None
    vendor_name: Optional[str] = None
    
    @model_validator(mode='after')
    def validate_travel_fields(self):
        """Ensure travel fields are provided for travel category"""
        if self.category == ExpenseCategoryEnum.travel:
            if self.travel_mode is None:
                raise ValueError("travel_mode is required for travel expenses")
        return self


class MultiBillExpenseCreate(BaseModel):
    """Create expense claim with multiple bills"""
    trip_start_date: Optional[date] = Field(None, description="Trip start date (for multi-day trips)")
    trip_end_date: Optional[date] = Field(None, description="Trip end date (for multi-day trips)")
    trip_purpose: Optional[str] = Field(None, max_length=500, description="Purpose of trip")
    bills: List[BillItemCreate] = Field(min_items=1, description="List of bills to claim")
    
    @model_validator(mode='after')
    def validate_dates(self):
        """Validate trip dates and bill dates"""
        # Validate trip end date is after start date
        if self.trip_end_date and self.trip_start_date:
            if self.trip_end_date < self.trip_start_date:
                raise ValueError("trip_end_date must be after or equal to trip_start_date")
        
        # Validate all bill dates fall within trip dates
        if self.trip_start_date and self.trip_end_date:
            for bill in self.bills:
                if not (self.trip_start_date <= bill.expense_date <= self.trip_end_date):
                    raise ValueError(
                        f"Bill dated {bill.expense_date} falls outside trip dates "
                        f"({self.trip_start_date} to {self.trip_end_date})"
                    )
        return self


class PerDayBreakdown(BaseModel):
    """Per-day expense breakdown"""
    date: date
    total_amount: float
    food_amount: float = 0.0
    travel_amount: float = 0.0
    accommodation_amount: float = 0.0
    other_amount: float = 0.0
    bill_count: int = 0
    exceeds_daily_limit: bool = False
    daily_limit_violation: Optional[str] = None


class ExpenseWithTrip(BaseModel):
    """Enhanced expense response with trip info"""
    id: int
    expense_number: str
    employee_id: int
    
    # Trip information
    trip_start_date: Optional[date] = None
    trip_end_date: Optional[date] = None
    trip_purpose: Optional[str] = None
    trip_duration_days: Optional[int] = None
    
    # Totals
    total_amount: float
    bill_count: int
    
    # Per-day breakdown
    per_day_breakdown: Optional[List[PerDayBreakdown]] = None
    average_per_day: Optional[float] = None
    
    # Validation
    is_within_limits: bool
    is_within_daily_limits: bool = True
    validation_errors: Optional[List[str]] = None
    
    # AI Analysis
    ai_summary: Optional[str] = None
    ai_recommendation: Optional[str] = None
    ai_confidence_score: Optional[float] = None
    
    # Status
    status: str
    current_approver_level: Optional[str] = None
    
    # Timestamps
    created_at: datetime
    submitted_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class BillFileInfo(BaseModel):
    """Information about an uploaded bill file"""
    filename: str
    file_path: str
    category: ExpenseCategoryEnum
    amount: float
    expense_date: date
    ocr_text: Optional[str] = None
    ai_extracted_info: Optional[dict] = None


class MultiExpenseResponse(BaseModel):
    """Response for multi-bill expense submission"""
    success: bool
    message: str
    expense: ExpenseWithTrip
    bills_processed: int
    bills_info: List[BillFileInfo]
    warnings: Optional[List[str]] = None


# ============================================================================
# BASIC EXPENSE SCHEMAS (for backward compatibility)
# ============================================================================

class ExpenseBase(BaseModel):
    """Base expense schema"""
    category: ExpenseCategoryEnum
    amount: float = Field(..., gt=0)
    expense_date: datetime
    description: str = Field(..., min_length=10, max_length=1000)
    travel_mode: Optional[TravelModeEnum] = None
    travel_from: Optional[str] = None
    travel_to: Optional[str] = None


class ExpenseCreate(ExpenseBase):
    """Schema for creating a new expense"""
    pass


class ExpenseResponse(ExpenseBase):
    """Schema for expense response"""
    id: int
    expense_number: str
    employee_id: int
    bill_file_name: str
    bill_number: Optional[str] = None
    vendor_name: Optional[str] = None
    
    # AI Analysis
    ai_analysis: Optional[dict] = None
    ai_summary: Optional[str] = None
    ai_recommendation: Optional[str] = None
    ai_confidence_score: Optional[float] = None
    is_valid_bill: Optional[bool] = None
    has_gst: Optional[bool] = None
    has_required_stamps: Optional[bool] = None
    
    # Validation
    is_within_limits: bool
    validation_errors: Optional[List[str]] = None
    
    # Status
    status: ExpenseStatusEnum
    current_approver_level: Optional[str] = None
    
    # Timestamps
    created_at: datetime
    submitted_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    
    # Rejection
    rejection_reason: Optional[str] = None
    rejected_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ExpenseListResponse(BaseModel):
    """Schema for list of expenses"""
    total: int
    expenses: List[ExpenseResponse]