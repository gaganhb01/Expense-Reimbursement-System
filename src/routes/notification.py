"""
Notification Routes
User notification management endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional

from src.config.database import get_db
from src.services.auth_service import auth_service
from src.models.user import User
from src.models.notification import Notification
from src.models.expense import Expense
from src.utils.logger import setup_logger

logger = setup_logger()
router = APIRouter()


@router.get("/my-notifications")
async def get_my_notifications(
    unread_only: bool = False,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_service.get_current_user)
):
    """
    Get current user's notifications
    
    **Parameters:**
    - unread_only: If True, only return unread notifications
    - skip: Number of records to skip (pagination)
    - limit: Maximum number of records to return
    
    **Returns:**
    - total: Total notification count
    - unread_count: Count of unread notifications
    - notifications: List of notification objects with expense details
    """
    # Build query
    query = db.query(Notification).filter(Notification.user_id == current_user.id)
    
    if unread_only:
        query = query.filter(Notification.is_read == False)
    
    # Get total count before pagination
    total_count = query.count()
    
    # Get notifications with pagination
    notifications = query.order_by(
        Notification.created_at.desc()
    ).offset(skip).limit(limit).all()
    
    # Get unread count
    unread_count = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False
    ).count()
    
    # Build response
    notifications_list = []
    
    for notif in notifications:
        notif_dict = {
            "id": notif.id,
            "user_id": notif.user_id,
            "type": notif.type.value if hasattr(notif.type, 'value') else str(notif.type),
            "title": notif.title,
            "message": notif.message,
            "expense_id": notif.expense_id,
            "is_read": notif.is_read,
            "read_at": notif.read_at.isoformat() if notif.read_at else None,
            "created_at": notif.created_at.isoformat(),
            "expense_number": None,
            "expense_amount": None,
            "expense_status": None
        }
        
        # Add expense details if available
        if notif.expense_id:
            expense = db.query(Expense).filter(Expense.id == notif.expense_id).first()
            if expense:
                notif_dict["expense_number"] = expense.expense_number
                notif_dict["expense_amount"] = float(expense.amount)
                notif_dict["expense_status"] = expense.status.value if hasattr(expense.status, 'value') else str(expense.status)
        
        notifications_list.append(notif_dict)
    
    logger.info(f"User {current_user.username} (ID: {current_user.id}) fetched {len(notifications_list)} notifications (unread: {unread_count})")
    
    return {
        "success": True,
        "total": total_count,
        "unread_count": unread_count,
        "notifications": notifications_list
    }


@router.get("/unread-count")
async def get_unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_service.get_current_user)
):
    """
    Get count of unread notifications (lightweight endpoint for polling)
    
    **Returns:**
    - unread_count: Number of unread notifications
    """
    unread_count = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False
    ).count()
    
    return {
        "success": True,
        "unread_count": unread_count
    }


@router.put("/{notification_id}/read")
async def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_service.get_current_user)
):
    """
    Mark a specific notification as read
    
    **Parameters:**
    - notification_id: ID of the notification to mark as read
    
    **Returns:**
    - success: Boolean indicating operation success
    - message: Success message
    """
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == current_user.id
    ).first()
    
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    
    if notification.is_read:
        return {
            "success": True,
            "message": "Notification was already marked as read"
        }
    
    notification.is_read = True
    notification.read_at = datetime.utcnow()
    db.commit()
    
    logger.info(f"User {current_user.username} marked notification {notification_id} as read")
    
    return {
        "success": True,
        "message": "Notification marked as read"
    }


@router.put("/mark-all-read")
async def mark_all_notifications_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_service.get_current_user)
):
    """
    Mark all notifications as read for current user
    
    **Returns:**
    - success: Boolean indicating operation success
    - message: Success message
    - count: Number of notifications marked as read
    """
    unread_count = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False
    ).count()
    
    if unread_count == 0:
        return {
            "success": True,
            "message": "No unread notifications to mark",
            "count": 0
        }
    
    db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False
    ).update({
        "is_read": True,
        "read_at": datetime.utcnow()
    }, synchronize_session=False)
    db.commit()
    
    logger.info(f"User {current_user.username} marked {unread_count} notifications as read")
    
    return {
        "success": True,
        "message": "All notifications marked as read",
        "count": unread_count
    }


@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_service.get_current_user)
):
    """
    Delete a specific notification
    
    **Parameters:**
    - notification_id: ID of the notification to delete
    
    **Returns:**
    - success: Boolean indicating operation success
    - message: Success message
    """
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == current_user.id
    ).first()
    
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    
    db.delete(notification)
    db.commit()
    
    logger.info(f"User {current_user.username} deleted notification {notification_id}")
    
    return {
        "success": True,
        "message": "Notification deleted successfully"
    }


@router.delete("/clear-all")
async def clear_all_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_service.get_current_user)
):
    """
    Delete all notifications for current user
    
    **Returns:**
    - success: Boolean indicating operation success
    - message: Success message
    - count: Number of notifications deleted
    """
    notification_count = db.query(Notification).filter(
        Notification.user_id == current_user.id
    ).count()
    
    if notification_count == 0:
        return {
            "success": True,
            "message": "No notifications to clear",
            "count": 0
        }
    
    db.query(Notification).filter(
        Notification.user_id == current_user.id
    ).delete(synchronize_session=False)
    db.commit()
    
    logger.info(f"User {current_user.username} cleared {notification_count} notifications")
    
    return {
        "success": True,
        "message": "All notifications cleared",
        "count": notification_count
    }


@router.get("/notification-stats")
async def get_notification_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_service.get_current_user)
):
    """
    Get notification statistics for current user
    
    **Returns:**
    - total: Total notifications
    - unread: Unread notifications
    - read: Read notifications
    - by_type: Count of notifications by type
    """
    from sqlalchemy import func
    from src.models.notification import NotificationType
    
    total = db.query(Notification).filter(
        Notification.user_id == current_user.id
    ).count()
    
    unread = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False
    ).count()
    
    # Get counts by type
    type_counts = db.query(
        Notification.type,
        func.count(Notification.id).label('count')
    ).filter(
        Notification.user_id == current_user.id
    ).group_by(Notification.type).all()
    
    by_type = {
        str(notif_type.value if hasattr(notif_type, 'value') else notif_type): count 
        for notif_type, count in type_counts
    }
    
    return {
        "success": True,
        "total": total,
        "unread": unread,
        "read": total - unread,
        "by_type": by_type
    }