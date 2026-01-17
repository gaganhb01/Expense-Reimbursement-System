"""
Expense Service
Business logic for expense management
"""

from sqlalchemy.orm import Session
from datetime import datetime

from src.models.expense import Expense
from src.services.notification_service import notification_service
from src.services.validation_service import validation_service
from src.services.elasticsearch_service import elasticsearch_service
from src.utils.logger import setup_logger

logger = setup_logger()


class ExpenseService:
    """Service for expense-related business logic"""
    
    def __init__(self):
        """Initialize with dependent services"""
        self.validation_service = validation_service
        self.notification_service = notification_service
        self.elasticsearch_service = elasticsearch_service
    
    async def submit_expense(
        self,
        db: Session,
        expense: Expense
    ):
        """
        Submit expense for approval
        
        Args:
            db: Database session
            expense: Expense object to submit
        """
        # Update status to submitted
        expense.status = "submitted"
        expense.submitted_at = datetime.utcnow()
        expense.current_approver_level = "manager"
        
        db.commit()
        db.refresh(expense)
        
        # Index in Elasticsearch for searchability
        if self.elasticsearch_service:
            await self.elasticsearch_service.index_expense(expense)
        
        # Notify appropriate approvers
        await self.notification_service.notify_approval_required(db, expense)
        
        logger.info(
            f"Expense {expense.expense_number} submitted for approval by "
            f"employee {expense.employee_id}"
        )
    
    async def approve_expense(
        self,
        db: Session,
        expense: Expense,
        approver_name: str,
        comments: str = None
    ):
        """
        Approve an expense and move to next level
        
        Args:
            db: Database session
            expense: Expense to approve
            approver_name: Name of approver
            comments: Optional approval comments
        """
        # Determine next status
        status_flow = {
            "manager_review": "hr_review",
            "hr_review": "finance_review",
            "finance_review": "approved"
        }
        
        next_status = status_flow.get(expense.status.value)
        
        if not next_status:
            logger.warning(f"Cannot approve expense in status: {expense.status.value}")
            return
        
        # Update expense
        expense.status = next_status
        
        if next_status == "approved":
            expense.approved_at = datetime.utcnow()
            expense.current_approver_level = None
        else:
            expense.current_approver_level = next_status.replace("_review", "")
        
        db.commit()
        db.refresh(expense)
        
        # Update in Elasticsearch
        if self.elasticsearch_service:
            await self.elasticsearch_service.update_expense(expense)
        
        # Notify employee about approval
        await self.notification_service.notify_expense_approved(
            db, expense, approver_name, comments
        )
        
        # If not final approval, notify next approvers
        if next_status != "approved":
            await self.notification_service.notify_approval_required(db, expense)
        
        logger.info(
            f"Expense {expense.expense_number} approved by {approver_name}. "
            f"New status: {next_status}"
        )
    
    async def reject_expense(
        self,
        db: Session,
        expense: Expense,
        rejection_reason: str
    ):
        """
        Reject an expense
        
        Args:
            db: Database session
            expense: Expense to reject
            rejection_reason: AI-generated rejection reason
        """
        # Update expense
        expense.status = "rejected"
        expense.rejection_reason = rejection_reason
        expense.rejected_at = datetime.utcnow()
        expense.current_approver_level = None
        
        db.commit()
        db.refresh(expense)
        
        # Update in Elasticsearch
        if self.elasticsearch_service:
            await self.elasticsearch_service.update_expense(expense)
        
        # Notify employee about rejection
        await self.notification_service.notify_expense_rejected(
            db, expense, rejection_reason
        )
        
        logger.info(f"Expense {expense.expense_number} rejected")
    
    async def delete_expense(
        self,
        db: Session,
        expense: Expense
    ):
        """
        Delete an expense and remove from search index
        
        Args:
            db: Database session
            expense: Expense to delete
        """
        expense_id = expense.id
        expense_number = expense.expense_number
        
        # Delete from database
        db.delete(expense)
        db.commit()
        
        # Delete from Elasticsearch
        if self.elasticsearch_service:
            await self.elasticsearch_service.delete_expense(expense_id)
        
        logger.info(f"Expense {expense_number} deleted")
    
    def validate_expense_claim(
        self,
        category: str,
        amount: float,
        user_grade: str,
        travel_mode: str = None
    ) -> tuple:
        """
        Validate expense against grade rules
        
        Args:
            category: Expense category
            amount: Claimed amount
            user_grade: Employee grade
            travel_mode: Travel mode if applicable
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        return self.validation_service.validate_expense_limits(
            category=category,
            amount=amount,
            user_grade=user_grade,
            travel_mode=travel_mode
        )


# Create singleton instance
expense_service = ExpenseService()