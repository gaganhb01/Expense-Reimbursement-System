"""
Approval Routes
Expense approval workflow endpoints with FINANCE NOTIFICATIONS
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from src.config.database import get_db
from src.services.auth_service import auth_service
from src.services.ai_service import ai_service
from src.models.user import User, UserRole
from src.models.expense import Expense, ExpenseStatus
from src.models.approval import Approval, ApprovalStatus, ApprovalLevel
from src.models.notification import Notification, NotificationType
from src.schemas.expense import ExpenseResponse
from src.schemas.approval import ApprovalCreate
from src.utils.logger import setup_logger

logger = setup_logger()
router = APIRouter()


@router.get("/pending")
async def get_pending_approvals(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_service.get_current_user)
):
    """
    Get pending approvals for current user's role
    
    FIXED: Queries approvals table with uppercase enum values
    UPDATED: Response reordered with important fields first
    """
    # Determine approval level based on user role
    level_map = {
        UserRole.MANAGER: "MANAGER",
        UserRole.FINANCE: "FINANCE"
    }
    
    approval_level = level_map.get(current_user.role)
    
    if not approval_level:
        return {
            "expenses": [],
            "count": 0,
            "message": "No approval rights"
        }
    
    # Query approvals table for pending approvals at this level
    pending_approvals = db.query(Approval).filter(
        Approval.level == approval_level,
        Approval.status == "PENDING"
    ).order_by(Approval.created_at.desc()).offset(skip).limit(limit).all()
    
    # Get expense IDs
    expense_ids = [a.expense_id for a in pending_approvals]
    
    # Get full expense details
    expenses = db.query(Expense).filter(
        Expense.id.in_(expense_ids)
    ).order_by(Expense.created_at.desc()).all()
    
    logger.info(f"{current_user.username} ({current_user.role.value}) viewing {len(expenses)} pending approvals")
    
    # ✅ FORMAT EXPENSES WITH IMPORTANT FIELDS FIRST
    formatted_expenses = []
    for expense in expenses:
        formatted_expense = {
            # ✅ PRIMARY IDENTIFIERS - ALWAYS FIRST
            "id": expense.id,
            "expense_number": expense.expense_number,
            "employee_id": expense.employee_id,
            
            # BILL DETAILS - MOST IMPORTANT
            "bill_number": expense.bill_number,
            "vendor_name": expense.vendor_name,
            "bill_file_name": expense.bill_file_name,
            "bill_file_path": expense.bill_file_path,
            
            # FINANCIAL DETAILS
            "amount": expense.amount,
            "currency": expense.currency,
            "category": expense.category,
            
            # STATUS
            "status": expense.status,
            "current_approver_level": expense.current_approver_level,
            
            # DATES
            "expense_date": expense.expense_date,
            "submitted_at": expense.submitted_at,
            "created_at": expense.created_at,
            "updated_at": expense.updated_at,
            "approved_at": expense.approved_at,
            "rejected_at": expense.rejected_at,
            
            # DESCRIPTION
            "description": expense.description,
            
            # TRAVEL DETAILS
            "travel_mode": expense.travel_mode,
            "travel_from": expense.travel_from,
            "travel_to": expense.travel_to,
            
            # AI ANALYSIS
            "ai_recommendation": expense.ai_recommendation,
            "ai_confidence_score": expense.ai_confidence_score,
            "ai_summary": expense.ai_summary,
            "ai_analysis": expense.ai_analysis,
            "is_valid_bill": expense.is_valid_bill,
            "is_within_limits": expense.is_within_limits,
            "validation_errors": expense.validation_errors,
            
            # GST & STAMPS
            "has_gst": expense.has_gst,
            "has_required_stamps": expense.has_required_stamps,
            
            # DUPLICATE DETECTION
            "file_hash": expense.file_hash,
            "duplicate_check_status": expense.duplicate_check_status,
            "duplicate_of_expense_id": expense.duplicate_of_expense_id,
            "duplicate_detected_at": expense.duplicate_detected_at,
            
            # REJECTION INFO
            "rejection_reason": expense.rejection_reason,
            "rejected_by": expense.rejected_by,
            
            # PAYMENT
            "paid_at": expense.paid_at,
        }
        formatted_expenses.append(formatted_expense)
    
    return {
        "expenses": formatted_expenses,
        "count": len(formatted_expenses),
        "level": approval_level.lower()
    }


@router.post("/{expense_id}/approve")
async def approve_expense(
    expense_id: int,
    approval_data: ApprovalCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_service.get_current_user)
):
    """
    Approve an expense claim with FINANCE NOTIFICATIONS
    
    FIXED: Finance users get notified when manager approves
    UPDATED: HR approval removed - MANAGER → FINANCE flow
    """
    logger.info(f"User {current_user.username} attempting to approve expense ID {expense_id}")
    
    # Get expense
    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    
    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Expense not found"
        )
    
    # Get employee details for notifications
    employee = db.query(User).filter(User.id == expense.employee_id).first()
    
    logger.info(f"Found expense {expense.expense_number} from {employee.full_name if employee else 'Unknown'} with current status: {expense.status}")
    
    # ✅ UPDATED: HR removed from level_map
    level_map = {
        UserRole.MANAGER: "MANAGER",
        UserRole.FINANCE: "FINANCE"
    }
    
    approval_level = level_map.get(current_user.role)
    
    if not approval_level:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have approval rights"
        )
    
    logger.info(f"User role level: {approval_level}")
    
    # Get ANY pending approval at this level (not just for current user)
    approval = db.query(Approval).filter(
        Approval.expense_id == expense_id,
        Approval.level == approval_level,
        Approval.status == "PENDING"
    ).first()
    
    if not approval:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No pending approval found at {approval_level} level"
        )
    
    logger.info(f"Found pending approval at {approval_level} level")
    
    # Update approval - set approver to current user and mark as approved
    approval.approver_id = current_user.id
    approval.status = "APPROVED"
    approval.comments = approval_data.comments
    approval.reviewed_at = datetime.utcnow()
    
    # ✅ UPDATED: Simplified workflow - MANAGER → FINANCE (no HR)
    if approval_level == "MANAGER":
        # Manager approved → Go directly to Finance
        logger.info("📋 Manager approved - finding finance users to notify...")
        
        # ✅✅✅ CRITICAL FIX: Get ALL active finance users
        finance_users = db.query(User).filter(
            User.role == UserRole.FINANCE,
            User.is_active == True
        ).all()
        
        logger.info(f"📧 Found {len(finance_users)} finance users to notify")
        
        if finance_users:
            # Pick first finance user for approval record
            primary_finance = finance_users[0]
            
            # Create Finance approval
            finance_approval = Approval(
                expense_id=expense.id,
                approver_id=primary_finance.id,
                level="FINANCE",
                status="PENDING"
            )
            db.add(finance_approval)
            
            # ✅ UPDATE EXPENSE TABLE
            expense.current_approver_level = "FINANCE"
            logger.info(f"✅ Moving expense to FINANCE approval")
            
            # ✅✅✅ SEND NOTIFICATIONS TO ALL FINANCE USERS
            for finance_user in finance_users:
                try:
                    notification_message = (
                        f"📋 New Expense Awaiting Your Review\n\n"
                        f"Employee: {employee.full_name if employee else 'Unknown'} ({employee.username if employee else 'N/A'})\n"
                        f"Expense Number: {expense.expense_number}\n"
                        f"Amount: ₹{expense.amount:,.2f}\n"
                        f"Category: {expense.category.upper() if isinstance(expense.category, str) else expense.category}\n"
                        f"Bill Number: {expense.bill_number or 'N/A'}\n"
                        f"Vendor: {expense.vendor_name or 'N/A'}\n"
                        f"Description: {expense.description}\n\n"
                        f"✅ Manager Approved: {current_user.full_name}\n"
                    )
                    
                    if approval_data.comments:
                        notification_message += f"💬 Manager Comment: {approval_data.comments}\n\n"
                    
                    notification_message += f"Please review and process this expense claim."
                    
                    notification = Notification(
                        user_id=finance_user.id,
                        type=NotificationType.EXPENSE_SUBMITTED,
                        title=f"New Expense Awaiting Your Review - {expense.expense_number}",
                        message=notification_message,
                        expense_id=expense.id
                    )
                    db.add(notification)
                    logger.info(f"✅ Notification created for finance user {finance_user.username} (ID: {finance_user.id})")
                except Exception as e:
                    logger.error(f"❌ Failed to create notification for {finance_user.username}: {e}")
            
            # Commit notifications
            db.commit()
            logger.info(f"📧 Sent {len(finance_users)} notifications to finance users")
            
        else:
            # No Finance → Fully approved
            # ✅ UPDATE EXPENSE TABLE TO APPROVED
            expense.status = "approved"
            expense.approved_at = datetime.utcnow()
            expense.current_approver_level = None
            logger.warning(f"⚠️ No finance users found - expense fully approved")
            
    elif approval_level == "FINANCE":
        # Finance approved → Fully approved
        # ✅ UPDATE EXPENSE TABLE TO APPROVED
        expense.status = "approved"
        expense.approved_at = datetime.utcnow()
        expense.current_approver_level = None
        logger.info(f"✅ Expense fully approved at FINANCE level")
    
    # ✅ COMMIT ALL CHANGES
    db.commit()
    db.refresh(expense)
    db.refresh(approval)
    
    logger.info(f"✅ SUCCESS: Expense {expense.expense_number} updated")
    logger.info(f"   - Status: {expense.status}")
    logger.info(f"   - Current level: {expense.current_approver_level}")
    logger.info(f"   - Approved at: {expense.approved_at}")
    
    # ✅ NEW: Send approval email to employee
    try:
        from src.services.email_service import email_service
        
        if employee:
            email_service.send_approval_notification(
                to_email=employee.email,
                employee_name=employee.full_name,
                expense_data={
                    "id": expense.id,
                    "expense_number": expense.expense_number,
                    "bill_number": expense.bill_number,
                    "vendor_name": expense.vendor_name,
                    "amount": expense.amount,
                    "category": expense.category,
                    "description": expense.description,
                    "status": expense.status
                },
                approver_name=current_user.full_name,
                approver_level=approval_level,
                comments=approval_data.comments
            )
            logger.info(f"📧 Approval email sent to {employee.email}")
    except Exception as e:
        logger.warning(f"Failed to send approval email: {e}")
    
    # Create notification for employee
    try:
        message = f"Your expense claim {expense.expense_number} has been approved by {current_user.full_name}"
        if expense.status == "approved":
            message += ". Your reimbursement is ready for processing."
        else:
            message += f" at {approval_level} level."
        
        if approval_data.comments:
            message += f" Comment: {approval_data.comments}"
        
        notification = Notification(
            user_id=expense.employee_id,
            type=NotificationType.EXPENSE_APPROVED,
            title=f"Expense Approved by {approval_level}",
            message=message,
            expense_id=expense.id
        )
        db.add(notification)
        db.commit()
        logger.info(f"✅ Notification sent to employee")
    except Exception as e:
        logger.warning(f"Notification creation failed: {e}")
    
    # Log audit
    try:
        from src.models.audit_log import AuditLog
        audit_log = AuditLog(
            user_id=current_user.id,
            action="approve_expense",
            entity_type="expense",
            entity_id=expense.id,
            expense_id=expense.id,
            description=f"Approved expense {expense.expense_number} at {approval_level} level",
            changes={
                "level": approval_level,
                "status": expense.status,
                "current_approver_level": expense.current_approver_level,
                "comments": approval_data.comments
            }
        )
        db.add(audit_log)
        db.commit()
        logger.info(f"✅ Audit log created")
    except Exception as e:
        logger.warning(f"Audit log creation failed: {e}")
    
    # Build response message
    message = f"Expense approved at {approval_level} level"
    if expense.status == "approved":
        message = "Expense fully approved and ready for reimbursement"
    elif expense.current_approver_level:
        message = f"Expense approved at {approval_level} level. Now pending {expense.current_approver_level} approval"
    
    return {
        "success": True,
        "message": message,
        "expense_number": expense.expense_number,
        "current_status": expense.status,
        "current_approver_level": expense.current_approver_level,
        "approved_at": expense.approved_at.isoformat() if expense.approved_at else None
    }


@router.post("/{expense_id}/reject")
async def reject_expense(
    expense_id: int,
    approval_data: ApprovalCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_service.get_current_user)
):
    """
    Reject an expense claim
    
    FIXED: Any manager can reject + Updates expenses table
    UPDATED: HR approval removed
    """
    logger.info(f"User {current_user.username} attempting to reject expense ID {expense_id}")
    
    # Get expense
    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    
    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Expense not found"
        )
    
    logger.info(f"Found expense {expense.expense_number} with current status: {expense.status}")
    
    # ✅ UPDATED: HR removed from level_map
    level_map = {
        UserRole.MANAGER: "MANAGER",
        UserRole.FINANCE: "FINANCE"
    }
    
    approval_level = level_map.get(current_user.role)
    
    if not approval_level:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have approval rights"
        )
    
    logger.info(f"User role level: {approval_level}")
    
    # Get ANY pending approval at this level (not just for current user)
    approval = db.query(Approval).filter(
        Approval.expense_id == expense_id,
        Approval.level == approval_level,
        Approval.status == "PENDING"
    ).first()
    
    if not approval:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No pending approval found at {approval_level} level"
        )
    
    logger.info(f"Found pending approval at {approval_level} level")
    
    # Generate AI rejection reason if ai_service is available
    try:
        rejection_reason = await ai_service.generate_rejection_reason(
            expense_data={
                "expense_number": expense.expense_number,
                "category": expense.category,
                "amount": expense.amount,
                "description": expense.description,
            },
            ai_analysis=expense.ai_analysis or {},
            reviewer_comments=approval_data.comments
        )
    except Exception as e:
        logger.warning(f"AI rejection reason generation failed: {e}")
        rejection_reason = f"Rejected by {approval_level}: {approval_data.comments}"
    
    # Build AI analysis summary for rejection
    ai_summary = ""
    if expense.ai_analysis:
        ai_data = expense.ai_analysis
        ai_summary = f"📊 AI Analysis:\n"
        ai_summary += f"• Authenticity: {'✅ Authentic' if ai_data.get('is_authentic') else '❌ Not Authentic'}\n"
        ai_summary += f"• Confidence: {ai_data.get('confidence_score', 0)}%\n"
        ai_summary += f"• AI Recommendation: {ai_data.get('recommendation', 'N/A')}\n"
        
        # Add red flags if present
        red_flags = ai_data.get('red_flags', [])
        if red_flags:
            ai_summary += f"• Red Flags: {len(red_flags)} issue(s) found\n"
            for i, flag in enumerate(red_flags[:3], 1):
                ai_summary += f"  {i}. {flag}\n"
        
        # Add AI summary if present
        if ai_data.get('summary'):
            ai_summary += f"\n💡 Summary: {ai_data.get('summary')}\n"
    
    # Update approval - set approver to current user and mark as rejected
    approval.approver_id = current_user.id
    approval.status = "REJECTED"
    approval.comments = approval_data.comments
    approval.ai_summary = ai_summary.strip() if ai_summary else expense.ai_summary
    approval.reviewed_at = datetime.utcnow()
    
    # ✅ CRITICAL: UPDATE THE EXPENSE TABLE!
    logger.info(f"Updating expense {expense.expense_number} status from '{expense.status}' to 'rejected'")
    
    expense.status = "rejected"
    expense.rejection_reason = rejection_reason
    expense.rejected_by = current_user.id
    expense.rejected_at = datetime.utcnow()
    expense.current_approver_level = None
    
    # ✅ COMMIT ALL CHANGES
    db.commit()
    db.refresh(expense)
    db.refresh(approval)
    
    logger.info(f"✅ SUCCESS: Expense {expense.expense_number} updated to status: {expense.status}")
    logger.info(f"✅ Rejection reason: {expense.rejection_reason}")
    logger.info(f"✅ Rejected at: {expense.rejected_at}")
    
    # ✅ NEW: Send rejection email to employee
    try:
        from src.services.email_service import email_service
        
        # Get employee
        employee = db.query(User).filter(User.id == expense.employee_id).first()
        
        if employee:
            email_service.send_rejection_notification(
                to_email=employee.email,
                employee_name=employee.full_name,
                expense_data={
                    "id": expense.id,
                    "expense_number": expense.expense_number,
                    "bill_number": expense.bill_number,
                    "vendor_name": expense.vendor_name,
                    "amount": expense.amount,
                    "category": expense.category,
                    "description": expense.description
                },
                rejector_name=current_user.full_name,
                rejector_level=approval_level,
                rejection_reason=rejection_reason,
                manager_comments=approval_data.comments,
                ai_summary=ai_summary.strip() if ai_summary else None
            )
            logger.info(f"📧 Rejection email sent to {employee.email}")
    except Exception as e:
        logger.warning(f"Failed to send rejection email: {e}")
    
    # Create notification for employee
    try:
        notification = Notification(
            user_id=expense.employee_id,
            type=NotificationType.EXPENSE_REJECTED,
            title="Expense Claim Rejected",
            message=rejection_reason,
            expense_id=expense.id
        )
        db.add(notification)
        db.commit()
        logger.info(f"✅ Notification sent to employee")
    except Exception as e:
        logger.warning(f"Notification creation failed: {e}")
    
    # Log audit
    try:
        from src.models.audit_log import AuditLog
        audit_log = AuditLog(
            user_id=current_user.id,
            action="reject_expense",
            entity_type="expense",
            entity_id=expense.id,
            expense_id=expense.id,
            description=f"Rejected expense {expense.expense_number} at {approval_level} level",
            changes={
                "level": approval_level,
                "status": "rejected",
                "reason": rejection_reason
            }
        )
        db.add(audit_log)
        db.commit()
        logger.info(f"✅ Audit log created")
    except Exception as e:
        logger.warning(f"Audit log creation failed: {e}")
    
    logger.info(f"❌ Expense {expense.expense_number} rejected by {current_user.username} ({approval_level})")
    
    return {
        "success": True,
        "message": f"Expense rejected successfully at {approval_level} level",
        "expense_number": expense.expense_number,
        "rejection_reason": rejection_reason,
        "ai_analysis_summary": ai_summary.strip() if ai_summary else None
    }