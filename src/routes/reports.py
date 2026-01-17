"""
Reports Routes
Search, statistics, and reporting endpoints for managers
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from typing import Optional
from datetime import datetime
import os

from src.config.database import get_db
from src.services.auth_service import auth_service
from src.models.user import User
from src.models.expense import Expense, ExpenseStatus, ExpenseCategory
from src.models.audit_log import AuditLog
from src.utils.logger import setup_logger
from src.utils.file_handler import get_file_mime_type

logger = setup_logger()
router = APIRouter()


@router.get("/search")
async def search_expenses(
    q: Optional[str] = Query(None, description="Search query - search by description, employee name, vendor"),
    category: Optional[str] = Query(None, description="Filter by category: travel, food, medical, accommodation, communication, other"),
    status: Optional[str] = Query(None, description="Filter by status: submitted, manager_review, hr_review, finance_review, approved, rejected"),
    employee_id: Optional[int] = Query(None, description="Filter by employee ID"),
    employee_name: Optional[str] = Query(None, description="Search by employee name"),
    grade: Optional[str] = Query(None, description="Filter by employee grade: A, B, C, D"),
    department: Optional[str] = Query(None, description="Filter by department"),
    min_amount: Optional[float] = Query(None, description="Minimum amount"),
    max_amount: Optional[float] = Query(None, description="Maximum amount"),
    from_date: Optional[str] = Query(None, description="From date (YYYY-MM-DD)"),
    to_date: Optional[str] = Query(None, description="To date (YYYY-MM-DD)"),
    expense_number: Optional[str] = Query(None, description="Search by expense number"),
    bill_number: Optional[str] = Query(None, description="Search by bill number"),
    vendor_name: Optional[str] = Query(None, description="Search by vendor name"),
    ai_recommendation: Optional[str] = Query(None, description="Filter by AI recommendation: APPROVE, REJECT, REVIEW"),
    is_within_limits: Optional[bool] = Query(None, description="Filter by limit compliance: true/false"),
    skip: int = Query(0, description="Number of records to skip"),
    limit: int = Query(50, description="Maximum number of records to return"),
    sort_by: Optional[str] = Query("created_at", description="Sort by: created_at, amount, expense_date"),
    sort_order: Optional[str] = Query("desc", description="Sort order: asc, desc"),
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_service.require_permission("view_all_expenses"))
):
    """
    🔍 Advanced Expense Search with Multiple Filters
    
    For Managers, HR, Finance, and Admin to search and view expenses
    
    **Search Capabilities:**
    - Full-text search on description, employee name, vendor
    - Multiple filter options
    - Sorting options
    - Each result includes bill viewing URL and AI summary
    
    **Example Queries:**
    - Search all travel expenses: `?category=travel`
    - Find expenses by employee: `?employee_name=John`
    - Find pending approvals: `?status=manager_review`
    - Find high-value expenses: `?min_amount=5000`
    - Find out-of-limit claims: `?is_within_limits=false`
    - Combined filters: `?category=travel&grade=A&status=submitted`
    """
    # Start with base query joining employee data
    query = db.query(Expense).join(User, Expense.employee_id == User.id)
    
    # Apply text search (if provided)
    if q:
        search_term = f"%{q}%"
        query = query.filter(
            or_(
                Expense.description.ilike(search_term),
                Expense.vendor_name.ilike(search_term),
                User.full_name.ilike(search_term),
                User.employee_id.ilike(search_term)
            )
        )
    
    # Category filter
    if category:
        try:
            query = query.filter(Expense.category == ExpenseCategory(category.lower()))
        except ValueError:
            pass
    
    # Status filter
    if status:
        try:
            query = query.filter(Expense.status == ExpenseStatus(status.lower()))
        except ValueError:
            pass
    
    # Employee filters
    if employee_id:
        query = query.filter(Expense.employee_id == employee_id)
    
    if employee_name:
        query = query.filter(User.full_name.ilike(f"%{employee_name}%"))
    
    if grade:
        from src.models.user import UserGrade
        try:
            query = query.filter(User.grade == UserGrade(grade.upper()))
        except ValueError:
            pass
    
    if department:
        query = query.filter(User.department.ilike(f"%{department}%"))
    
    # Amount filters
    if min_amount:
        query = query.filter(Expense.amount >= min_amount)
    
    if max_amount:
        query = query.filter(Expense.amount <= max_amount)
    
    # Date filters
    if from_date:
        try:
            query = query.filter(Expense.expense_date >= datetime.strptime(from_date, "%Y-%m-%d"))
        except ValueError:
            pass
    
    if to_date:
        try:
            query = query.filter(Expense.expense_date <= datetime.strptime(to_date, "%Y-%m-%d"))
        except ValueError:
            pass
    
    # Expense number filter
    if expense_number:
        query = query.filter(Expense.expense_number.ilike(f"%{expense_number}%"))
    
    # Bill number filter
    if bill_number:
        query = query.filter(Expense.bill_number.ilike(f"%{bill_number}%"))
    
    # Vendor name filter
    if vendor_name:
        query = query.filter(Expense.vendor_name.ilike(f"%{vendor_name}%"))
    
    # AI recommendation filter
    if ai_recommendation:
        query = query.filter(Expense.ai_recommendation == ai_recommendation.upper())
    
    # Limit compliance filter
    if is_within_limits is not None:
        query = query.filter(Expense.is_within_limits == is_within_limits)
    
    # Get total count before pagination
    total = query.count()
    
    # Apply sorting
    if sort_by == "amount":
        order_column = Expense.amount
    elif sort_by == "expense_date":
        order_column = Expense.expense_date
    else:
        order_column = Expense.created_at
    
    if sort_order == "asc":
        query = query.order_by(order_column.asc())
    else:
        query = query.order_by(order_column.desc())
    
    # Apply pagination
    expenses = query.offset(skip).limit(limit).all()
    
    # Format response with bill viewing URLs
    results = []
    for expense in expenses:
        expense_data = {
            "id": expense.id,
            "expense_number": expense.expense_number,
            "employee": {
                "id": expense.employee_id,
                "name": expense.employee.full_name,
                "employee_id": expense.employee.employee_id,
                "grade": expense.employee.grade.value,
                "department": expense.employee.department
            },
            "category": expense.category.value,
            "amount": expense.amount,
            "expense_date": expense.expense_date.isoformat(),
            "description": expense.description,
            "status": expense.status.value,
            "vendor_name": expense.vendor_name,
            "bill_number": expense.bill_number,
            
            # AI Analysis Summary - This is what managers need!
            "ai_analysis": {
                "recommendation": expense.ai_recommendation,
                "confidence_score": expense.ai_confidence_score,
                "summary": expense.ai_summary,  # ← AI SUMMARY HERE
                "is_valid_bill": expense.is_valid_bill,
                "has_gst": expense.has_gst,
                "has_required_stamps": expense.has_required_stamps
            },
            
            # Validation
            "is_within_limits": expense.is_within_limits,
            "validation_errors": expense.validation_errors,
            
            # Travel details (if applicable)
            "travel_details": {
                "mode": expense.travel_mode.value if expense.travel_mode else None,
                "from": expense.travel_from,
                "to": expense.travel_to
            } if expense.category.value == "travel" else None,
            
            # Bill viewing URLs - Managers can click these
            "bill_urls": {
                "view": f"/api/reports/bills/{expense.id}/view",
                "download": f"/api/reports/bills/{expense.id}/download",
                "preview": f"/api/reports/bills/{expense.id}/preview"
            },
            
            # Timestamps
            "created_at": expense.created_at.isoformat(),
            "submitted_at": expense.submitted_at.isoformat() if expense.submitted_at else None,
            "approved_at": expense.approved_at.isoformat() if expense.approved_at else None,
            
            # Rejection info (if rejected)
            "rejection_info": {
                "reason": expense.rejection_reason,
                "rejected_at": expense.rejected_at.isoformat() if expense.rejected_at else None
            } if expense.status.value == "rejected" else None
        }
        results.append(expense_data)
    
    logger.info(f"Manager {current_user.username} searched expenses - {len(results)} results")
    
    return {
        "success": True,
        "total": total,
        "count": len(results),
        "page": skip // limit + 1 if limit > 0 else 1,
        "limit": limit,
        "filters_applied": {
            "search_query": q,
            "category": category,
            "status": status,
            "employee_name": employee_name,
            "grade": grade,
            "department": department,
            "amount_range": f"{min_amount or 0} - {max_amount or 'unlimited'}",
            "date_range": f"{from_date or 'start'} to {to_date or 'end'}"
        },
        "expenses": results
    }


@router.get("/bills/{expense_id}/view")
async def view_bill_file(
    expense_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_service.require_permission("view_all_expenses"))
):
    """
    📄 View Bill File (for managers in search results)
    
    Returns the actual bill file for viewing in browser
    Opens PDF/images directly in the browser
    """
    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    
    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Expense not found"
        )
    
    # Check if file exists
    if not os.path.exists(expense.bill_file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bill file not found on server"
        )
    
    # Determine media type
    media_type = get_file_mime_type(expense.bill_file_path)
    
    logger.info(f"Manager {current_user.username} viewing bill for expense {expense.expense_number}")
    
    # Return file for inline viewing in browser
    return FileResponse(
        path=expense.bill_file_path,
        filename=expense.bill_file_name,
        media_type=media_type,
        headers={"Content-Disposition": f'inline; filename="{expense.bill_file_name}"'}
    )


@router.get("/bills/{expense_id}/download")
async def download_bill_file(
    expense_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_service.require_permission("view_all_expenses"))
):
    """
    💾 Download Bill File
    
    Downloads the bill file to manager's computer
    """
    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    
    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Expense not found"
        )
    
    if not os.path.exists(expense.bill_file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bill file not found on server"
        )
    
    logger.info(f"Manager {current_user.username} downloading bill for expense {expense.expense_number}")
    
    # Return file for download
    return FileResponse(
        path=expense.bill_file_path,
        filename=expense.bill_file_name,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{expense.bill_file_name}"'}
    )


@router.get("/bills/{expense_id}/preview")
async def preview_bill_with_details(
    expense_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_service.require_permission("view_all_expenses"))
):
    """
    🔍 Preview Bill with Full Details
    
    Returns bill file URL along with complete expense details and AI analysis
    Perfect for manager's review dashboard
    
    **Includes:**
    - Complete employee details
    - Full expense information
    - Complete AI analysis and summary
    - Validation results
    - Bill viewing URLs
    - Quick action URLs for approve/reject
    """
    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    
    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Expense not found"
        )
    
    bill_exists = os.path.exists(expense.bill_file_path)
    
    return {
        "success": True,
        "expense": {
            "id": expense.id,
            "expense_number": expense.expense_number,
            "status": expense.status.value,
            
            # Employee details
            "employee": {
                "id": expense.employee_id,
                "name": expense.employee.full_name,
                "employee_id": expense.employee.employee_id,
                "email": expense.employee.email,
                "grade": expense.employee.grade.value,
                "department": expense.employee.department
            },
            
            # Expense details
            "details": {
                "category": expense.category.value,
                "amount": expense.amount,
                "currency": expense.currency,
                "expense_date": expense.expense_date.isoformat(),
                "description": expense.description,
                "vendor_name": expense.vendor_name,
                "bill_number": expense.bill_number
            },
            
            # Travel details (if travel expense)
            "travel_details": {
                "mode": expense.travel_mode.value if expense.travel_mode else None,
                "from": expense.travel_from,
                "to": expense.travel_to
            } if expense.category.value == "travel" else None,
            
            # AI Analysis - Complete summary for manager
            "ai_analysis": {
                "recommendation": expense.ai_recommendation,
                "confidence_score": expense.ai_confidence_score,
                "summary": expense.ai_summary,  # ← FULL AI SUMMARY
                "is_authentic": expense.is_valid_bill,
                "has_gst": expense.has_gst,
                "has_required_stamps": expense.has_required_stamps,
                "full_analysis": expense.ai_analysis  # ← Complete detailed analysis
            },
            
            # Validation results
            "validation": {
                "is_within_limits": expense.is_within_limits,
                "errors": expense.validation_errors,
                "grade_limits": expense.employee.get_expense_limits()
            },
            
            # Bill file info
            "bill_file": {
                "exists": bill_exists,
                "filename": expense.bill_file_name,
                "view_url": f"/api/reports/bills/{expense.id}/view",
                "download_url": f"/api/reports/bills/{expense.id}/download"
            },
            
            # Timestamps
            "timestamps": {
                "created_at": expense.created_at.isoformat(),
                "submitted_at": expense.submitted_at.isoformat() if expense.submitted_at else None,
                "approved_at": expense.approved_at.isoformat() if expense.approved_at else None,
                "rejected_at": expense.rejected_at.isoformat() if expense.rejected_at else None
            },
            
            # Approval info
            "approval_info": {
                "current_level": expense.current_approver_level,
                "can_approve": expense.can_be_approved_by(current_user.role.value)
            }
        },
        
        # Quick actions for manager
        "actions": {
            "approve_url": f"/api/approvals/{expense.id}/approve",
            "reject_url": f"/api/approvals/{expense.id}/reject"
        }
    }


@router.get("/statistics")
async def get_statistics(
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_service.require_permission("view_reports"))
):
    """
    Get expense statistics
    
    **Parameters:**
    - from_date: Start date filter (YYYY-MM-DD)
    - to_date: End date filter (YYYY-MM-DD)
    
    **Returns:**
    - Total expense count and amount
    - Breakdown by status
    - Breakdown by category
    """
    query = db.query(Expense)
    
    if from_date:
        try:
            query = query.filter(Expense.expense_date >= datetime.strptime(from_date, "%Y-%m-%d"))
        except ValueError:
            pass
    
    if to_date:
        try:
            query = query.filter(Expense.expense_date <= datetime.strptime(to_date, "%Y-%m-%d"))
        except ValueError:
            pass
    
    # Total statistics
    total_count = query.count()
    total_amount = query.with_entities(func.sum(Expense.amount)).scalar() or 0
    
    # By status
    by_status = db.query(
        Expense.status,
        func.count(Expense.id).label("count"),
        func.sum(Expense.amount).label("total")
    ).group_by(Expense.status).all()
    
    # By category
    by_category = db.query(
        Expense.category,
        func.count(Expense.id).label("count"),
        func.sum(Expense.amount).label("total")
    ).group_by(Expense.category).all()
    
    return {
        "success": True,
        "total_expenses": total_count,
        "total_amount": float(total_amount),
        "by_status": [
            {
                "status": item_status.value,
                "count": count,
                "total_amount": float(total or 0)
            }
            for item_status, count, total in by_status
        ],
        "by_category": [
            {
                "category": category.value,
                "count": count,
                "total_amount": float(total or 0)
            }
            for category, count, total in by_category
        ]
    }


@router.get("/audit-logs")
async def get_audit_logs(
    user_id: Optional[int] = None,
    action: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_service.require_role("admin"))
):
    """
    Get audit logs (Admin only)
    
    **Parameters:**
    - user_id: Filter by user ID
    - action: Filter by action type
    - skip: Pagination offset
    - limit: Maximum records to return
    
    **Returns:**
    - total: Total log count
    - logs: List of audit log entries
    """
    query = db.query(AuditLog)
    
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    
    if action:
        query = query.filter(AuditLog.action == action)
    
    logs = query.order_by(AuditLog.created_at.desc()).offset(skip).limit(limit).all()
    
    return {
        "success": True,
        "total": query.count(),
        "logs": logs
    }