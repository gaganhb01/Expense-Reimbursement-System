"""
Notification Service
Handles creation and management of user notifications
"""

from sqlalchemy.orm import Session
from typing import Optional

from src.models.notification import Notification, NotificationType
from src.models.expense import Expense
from src.models.user import User, UserRole
from src.utils.logger import setup_logger

logger = setup_logger()


class NotificationService:
    """Service for managing notifications"""
    
    async def notify_approval_required(self, db: Session, expense: Expense):
        """
        Notify appropriate approvers that an expense needs approval
        
        Args:
            db: Database session
            expense: Expense object needing approval
        """
        # Determine which role needs to approve based on expense current_approver_level
        # Map level to role that should approve
        level_to_role_map = {
            "manager": UserRole.MANAGER,
            "finance": UserRole.FINANCE,
        }
        
        # Determine target role from current_approver_level (set in the workflow)
        target_level = expense.current_approver_level
        target_role = level_to_role_map.get(target_level)
        
        if not target_role:
            logger.warning(f"Cannot determine target role for approval level: {target_level}")
            return
        
        # Get all active users with that role
        approvers = db.query(User).filter(
            User.role == target_role,
            User.is_active == True
        ).all()
        
        if not approvers:
            logger.warning(f"No active {target_role.value} users found to notify for expense {expense.expense_number}")
            return
        
        # Create notification for each approver
        for approver in approvers:
            notification = Notification(
                user_id=approver.id,
                type=NotificationType.APPROVAL_REQUIRED,
                title="New Expense Requires Approval",
                message=f"Expense {expense.expense_number} from {expense.employee.full_name} requires your approval. "
                        f"Category: {expense.category.value}, Amount: ₹{expense.amount}. "
                        f"AI Recommendation: {expense.ai_recommendation}",
                expense_id=expense.id
            )
            db.add(notification)
        
        db.commit()
        logger.info(f"Notified {len(approvers)} {target_role.value}s for expense {expense.expense_number}")
    
    async def notify_expense_approved(
        self,
        db: Session,
        expense: Expense,
        approver_name: str,
        comments: Optional[str] = None
    ):
        """
        Notify employee that their expense was approved
        
        Args:
            db: Database session
            expense: Approved expense
            approver_name: Name of person who approved
            comments: Optional approval comments
        """
        message = f"Your expense claim {expense.expense_number} has been approved by {approver_name}."
        if comments:
            message += f" Comments: {comments}"
        
        notification = Notification(
            user_id=expense.employee_id,
            type=NotificationType.EXPENSE_APPROVED,
            title="Expense Approved",
            message=message,
            expense_id=expense.id
        )
        db.add(notification)
        db.commit()
        
        logger.info(f"Notified user {expense.employee_id} about expense {expense.expense_number} approval")
    
    async def notify_expense_rejected(
        self,
        db: Session,
        expense: Expense,
        rejection_reason: str
    ):
        """
        Notify employee that their expense was rejected
        
        Args:
            db: Database session
            expense: Rejected expense
            rejection_reason: AI-generated rejection reason
        """
        notification = Notification(
            user_id=expense.employee_id,
            type=NotificationType.EXPENSE_REJECTED,
            title="Expense Claim Rejected",
            message=rejection_reason,
            expense_id=expense.id
        )
        db.add(notification)
        db.commit()
        
        logger.info(f"Notified user {expense.employee_id} about expense {expense.expense_number} rejection")
    
    async def notify_expense_status(
        self,
        db: Session,
        expense: Expense,
        new_status: str,
        message: str
    ):
        """
        Generic notification for expense status change
        
        Args:
            db: Database session
            expense: Expense object
            new_status: New status value
            message: Notification message
        """
        notification_type_map = {
            "approved": NotificationType.EXPENSE_APPROVED,
            "rejected": NotificationType.EXPENSE_REJECTED,
        }
        
        notification = Notification(
            user_id=expense.employee_id,
            type=notification_type_map.get(new_status, NotificationType.SYSTEM),
            title=f"Expense {new_status.title()}",
            message=message,
            expense_id=expense.id
        )
        db.add(notification)
        db.commit()
        
        logger.info(f"Notified user {expense.employee_id} about expense {expense.expense_number} status: {new_status}")


# Create singleton instance
notification_service = NotificationService()