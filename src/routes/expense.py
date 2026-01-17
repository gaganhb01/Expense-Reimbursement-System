"""
Expense Routes - COMPLETE VERSION WITH MULTI-BILL SUPPORT
Fully working with existing AI service
"""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, date, timedelta
import json

from src.config.database import get_db
from src.services.auth_service import auth_service
from src.services.ai_service import ai_service
from src.models.user import User
from src.models.expense import Expense, ExpenseCategory, ExpenseStatus, TravelMode
from src.schemas.expense import ExpenseCreate, ExpenseResponse, ExpenseListResponse
from src.utils.file_handler import save_upload_file, generate_expense_number
from src.utils.logger import setup_logger

logger = setup_logger()
router = APIRouter()

def filter_expense_for_employee(expense):
    """
    Filter sensitive AI analysis details from expense for employees
    Shows rejection reason and AI summary if rejected
    Managers/HR/Finance see full details
    """
    from src.models.user import UserRole
    
    # Create filtered expense dict
    filtered = {
        "id": expense.id,
        "expense_number": expense.expense_number,
        "employee_id": expense.employee_id,
        "category": expense.category,
        "amount": expense.amount,
        "currency": expense.currency,
        "expense_date": expense.expense_date,
        "description": expense.description,
        "travel_mode": expense.travel_mode,
        "travel_from": expense.travel_from,
        "travel_to": expense.travel_to,
        "bill_file_name": expense.bill_file_name,
        "bill_number": expense.bill_number,
        "vendor_name": expense.vendor_name,
        "status": expense.status,
        "current_approver_level": expense.current_approver_level,
        "created_at": expense.created_at,
        "submitted_at": expense.submitted_at,
        "approved_at": expense.approved_at,
        "rejected_at": expense.rejected_at,
    }
    
    # If rejected, include rejection reason and AI summary
    if expense.status == "rejected":
        filtered["rejection_reason"] = expense.rejection_reason
        filtered["ai_summary"] = expense.ai_summary
        
        # Build AI summary from stored ai_analysis JSON
        if expense.ai_analysis:
            ai_data = expense.ai_analysis
            ai_summary_text = ""
            
            ai_summary_text += f"📊 AI Analysis:\n"
            ai_summary_text += f"• Authenticity: {'✅ Authentic' if ai_data.get('is_authentic') else '❌ Not Authentic'}\n"
            ai_summary_text += f"• Confidence: {ai_data.get('confidence_score', 0)}%\n"
            ai_summary_text += f"• AI Recommendation: {ai_data.get('recommendation', 'N/A')}\n"
            
            # Add red flags (first 3)
            red_flags = ai_data.get('red_flags', [])
            if red_flags:
                ai_summary_text += f"• Issues Found: {len(red_flags)}\n"
                for i, flag in enumerate(red_flags[:3], 1):
                    ai_summary_text += f"  {i}. {flag}\n"
            
            # Add AI summary
            if ai_data.get('summary'):
                ai_summary_text += f"\n💡 Summary: {ai_data.get('summary')}\n"
            
            filtered["ai_analysis_summary"] = ai_summary_text.strip()
    else:
        # For non-rejected, don't include rejection details
        filtered["rejection_reason"] = None
    
    # Add limited AI analysis - only basic info for employees
    if expense.ai_analysis:
        filtered["ai_analysis"] = {
            "bill_number": expense.ai_analysis.get("bill_number"),
            "bill_date": expense.ai_analysis.get("bill_date"),
            "vendor_name": expense.ai_analysis.get("vendor_name"),
            "extracted_amount": expense.ai_analysis.get("extracted_amount"),
            "has_gst": expense.ai_analysis.get("has_gst"),
            "travel_mode": expense.ai_analysis.get("travel_mode"),
            "travel_route": expense.ai_analysis.get("travel_route"),
        }
    
    # Add basic summary fields (not full AI analysis)
    if expense.status != "rejected":
        filtered["ai_summary"] = expense.ai_summary
        filtered["ai_confidence_score"] = expense.ai_confidence_score
    
    return filtered

@router.post("/claim", status_code=status.HTTP_201_CREATED)
async def create_expense_claim(
    category: str = Form(...),
    amount: float = Form(...),
    expense_date: str = Form(...),
    description: str = Form(...),
    travel_mode: Optional[str] = Form(None),
    travel_from: Optional[str] = Form(None),
    travel_to: Optional[str] = Form(None),
    
    # ✅ NEW: Self-declaration support
    is_self_declaration: bool = Form(False),
    no_bill_reason: Optional[str] = Form(None),
    no_bill_category: Optional[str] = Form(None),
    
    # ✅ UPDATED: Bill file now optional
    bill_file: UploadFile = File(default=None),
    
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_service.get_current_user)
):
    """
    Create new expense claim with AI-powered validation and duplicate detection (SINGLE BILL)
    ✅ NEW: Supports self-declaration (no bill) with stricter limits
    """
    # Step 1: Check permission
    if not current_user.can_claim_expenses:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to claim expenses"
        )
    
    logger.info(f"User {current_user.username} (Grade {current_user.grade}) creating expense claim (Self-decl: {is_self_declaration})")
    
    try:
        # ✅ NEW Step 1.5: Validate self-declaration
        if is_self_declaration:
            from src.config.self_declaration_limits import (
                get_self_declaration_limit,
                is_category_forbidden_for_self_declaration
            )
            
            # Check category
            if is_category_forbidden_for_self_declaration(category):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Category '{category}' requires a bill."
                )
            
            # Check amount limit
            max_self_decl = get_self_declaration_limit(current_user.grade, "per_claim")
            if amount > max_self_decl:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Self-declared expenses limited to ₹{max_self_decl} for Grade {current_user.grade}."
                )
            
            # Check monthly count
            from sqlalchemy import func, extract
            current_month = datetime.now().month
            current_year = datetime.now().year
            
            self_decl_count = db.query(func.count(Expense.id)).filter(
                Expense.employee_id == current_user.id,
                Expense.is_self_declaration == True,
                extract('month', Expense.created_at) == current_month,
                extract('year', Expense.created_at) == current_year
            ).scalar()
            
            max_count = get_self_declaration_limit(current_user.grade, "max_count")
            if self_decl_count >= max_count:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Monthly limit of {max_count} self-declared expenses reached."
                )
            
            # Check monthly total
            self_decl_total = db.query(func.sum(Expense.amount)).filter(
                Expense.employee_id == current_user.id,
                Expense.is_self_declaration == True,
                extract('month', Expense.created_at) == current_month,
                extract('year', Expense.created_at) == current_year
            ).scalar() or 0
            
            monthly_limit = get_self_declaration_limit(current_user.grade, "monthly_total")
            if (self_decl_total + amount) > monthly_limit:
                remaining = monthly_limit - self_decl_total
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Monthly limit of ₹{monthly_limit} would be exceeded. Remaining: ₹{remaining:.2f}"
                )
            
            # Require detailed description
            if len(description) < 50:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Self-declared expenses require detailed description (minimum 50 characters)"
                )
            
            # Require reason
            if not no_bill_reason:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Please provide reason why bill is not available"
                )
        
        # ✅ Validate bill file (required if NOT self-declaration)
        if not is_self_declaration and not bill_file:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bill file is required. If you don't have a bill, check 'Self-Declaration' option."
            )
        
        # Step 2: Validate and parse date
        try:
            expense_date_parsed = datetime.strptime(expense_date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date format. Use YYYY-MM-DD"
            )
        
        # ✅ Step 3: Handle file (bill OR self-declaration)
        file_path = None
        saved_filename = None
        ai_analysis = {}
        duplicate_check = {
            "is_duplicate": False,
            "should_block": False,
            "file_hash": None,
            "original_expense": None
        }
        
        if is_self_declaration:
            # Create self-declaration file
            logger.info(f"Creating self-declaration expense (no bill)")
            
            import os
            declaration_dir = f"uploads/{current_user.id}/self_declarations"
            os.makedirs(declaration_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            declaration_filename = f"self_decl_{timestamp}.txt"
            file_path = os.path.join(declaration_dir, declaration_filename)
            
            with open(file_path, 'w') as f:
                f.write(f"SELF-DECLARATION - NO BILL AVAILABLE\n{'=' * 50}\n\n")
                f.write(f"Employee: {current_user.full_name} ({current_user.username})\n")
                f.write(f"Grade: {current_user.grade}\n")
                f.write(f"Date: {expense_date}\n")
                f.write(f"Category: {category}\n")
                f.write(f"Amount: ₹{amount}\n\n")
                f.write(f"Reason for No Bill:\n{no_bill_reason}\n\n")
                f.write(f"Description:\n{description}\n\n")
                f.write(f"Declaration Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            
            saved_filename = "Self Declaration"
            
            ai_analysis = {
                "is_authentic": None,
                "confidence_score": 0,
                "bill_number": "SELF-DECL",
                "bill_date": expense_date,
                "vendor_name": "Not Provided",
                "extracted_amount": amount,
                "has_gst": False,
                "travel_mode": travel_mode,
                "recommendation": "REVIEW",
                "summary": f"Self-declared expense - ₹{amount} - {category}",
                "red_flags": [f"No bill provided - {no_bill_reason}"]
            }
            
            duplicate_check["file_hash"] = f"SELF-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
        else:
            # Regular bill handling
            logger.info(f"Saving bill file: {bill_file.filename}")
            file_path, saved_filename = await save_upload_file(bill_file, current_user.id)
            logger.info(f"File saved: {file_path}")
            
            # Step 4: AI Analysis
            logger.info("Starting AI analysis...")
            ai_analysis = await ai_service.analyze_bill(
                file_path=file_path,
                category=category,
                amount=amount,
                user_grade=current_user.grade.value if hasattr(current_user.grade, 'value') else str(current_user.grade),
                description=description
            )
            
            logger.info(f"AI recommendation: {ai_analysis.get('recommendation', 'REVIEW')}")
            
            # ✅✅✅ Step 4.5: DUPLICATE DETECTION (NEW!) ✅✅✅
            logger.info("🔍 Starting duplicate detection...")
            from src.utils.duplicate_detector import DuplicateDetector
            
            duplicate_check = DuplicateDetector.perform_full_check(
                db=db,
                file_path=file_path,
                bill_number=ai_analysis.get("bill_number"),
                vendor_name=ai_analysis.get("vendor_name"),
                bill_date=ai_analysis.get("bill_date"),
                employee_id=current_user.id
            )
            
            # If exact duplicate (file hash match) - BLOCK submission
            if duplicate_check["should_block"]:
                logger.error(f"🚫 BLOCKING: Duplicate detected - {duplicate_check['duplicate_type']}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=duplicate_check["message"]
                )
        
        # Step 5: Generate expense number
        expense_number = generate_expense_number()
        
        # Step 6: Extract travel info from AI if not provided
        final_travel_mode = travel_mode or ai_analysis.get("travel_mode")
        
        travel_route = ai_analysis.get("travel_route", "")
        if travel_route and not (travel_from and travel_to):
            if " - " in travel_route:
                parts = travel_route.split(" - ")
                final_travel_from = travel_from or parts[0].strip()
                final_travel_to = travel_to or parts[1].strip() if len(parts) > 1 else None
            elif " to " in travel_route.lower():
                parts = travel_route.lower().split(" to ")
                final_travel_from = travel_from or parts[0].strip()
                final_travel_to = travel_to or parts[1].strip() if len(parts) > 1 else None
            else:
                final_travel_from = travel_from
                final_travel_to = travel_to
        else:
            final_travel_from = travel_from
            final_travel_to = travel_to
        
        # Step 7: Create expense with duplicate detection fields
        expense = Expense(
            expense_number=expense_number,
            employee_id=current_user.id,
            category=category.strip().lower(),
            amount=amount,
            currency="INR",
            expense_date=expense_date_parsed,
            description=description,
            travel_mode=final_travel_mode,
            travel_from=final_travel_from,
            travel_to=final_travel_to,
            bill_file_path=file_path,
            bill_file_name=saved_filename,
            bill_number=ai_analysis.get("bill_number"),
            vendor_name=ai_analysis.get("vendor_name"),
            ai_analysis=ai_analysis,
            ai_summary=ai_analysis.get("summary", ""),
            ai_recommendation=ai_analysis.get("recommendation", "REVIEW"),
            ai_confidence_score=ai_analysis.get("confidence_score", 0),
            is_valid_bill=ai_analysis.get("is_authentic"),
            has_gst=ai_analysis.get("has_gst"),
            has_required_stamps=ai_analysis.get("has_required_stamps"),
            is_within_limits=ai_analysis.get("is_within_limits", [True])[0] if isinstance(ai_analysis.get("is_within_limits"), tuple) else True,
            validation_errors=ai_analysis.get("red_flags", []),
            status="submitted",
            current_approver_level="MANAGER",
            submitted_at=datetime.now(),
            
            # ✅ NEW: Self-declaration fields
            is_self_declaration=is_self_declaration,
            declaration_reason=no_bill_reason if is_self_declaration else None,
            no_bill_category=no_bill_category if is_self_declaration else None,
            
            # ✅ NEW: Duplicate detection fields
            file_hash=duplicate_check.get("file_hash"),
            duplicate_check_status="suspected" if duplicate_check.get("is_duplicate") else "clean",
            duplicate_of_expense_id=duplicate_check["original_expense"].id if duplicate_check.get("original_expense") else None,
            duplicate_detected_at=datetime.now() if duplicate_check.get("is_duplicate") else None
        )
        
        db.add(expense)
        db.commit()
        db.refresh(expense)
        
        logger.info(f"✅ Expense {expense_number} created successfully (Self-decl: {is_self_declaration})")
        
        # If suspected duplicate - Log warning
        if duplicate_check.get("is_duplicate"):
            logger.warning(f"⚠️ Expense {expense_number} flagged as suspected duplicate")
        
        # ✅ NEW: Send confirmation email to employee
        try:
            from src.services.email_service import email_service
            
            email_service.send_submission_confirmation(
                to_email=current_user.email,
                employee_name=current_user.full_name,
                expense_data={
                    "id": expense.id,
                    "expense_number": expense.expense_number,
                    "bill_number": expense.bill_number or ("Self Declaration" if is_self_declaration else "N/A"),
                    "vendor_name": expense.vendor_name or ("Not Provided" if is_self_declaration else "N/A"),
                    "amount": expense.amount,
                    "category": expense.category,
                    "expense_date": expense.expense_date.strftime('%d %B %Y'),
                    "description": expense.description,
                    "submitted_at": expense.submitted_at.strftime('%d %B %Y at %I:%M %p')
                }
            )
            logger.info(f"📧 Confirmation email sent to {current_user.email}")
        except Exception as e:
            logger.warning(f"Failed to send confirmation email: {e}")
        
        # Step 8: Create approvals
        manager = None
        try:
            from src.models.approval import Approval
            from src.models.user import UserRole
            
            manager = db.query(User).filter(
                User.role == UserRole.MANAGER,
                User.is_active == True
            ).first()
            
            if manager:
                approval = Approval(
                    expense_id=expense.id,
                    approver_id=manager.id,
                    level="MANAGER",
                    status="PENDING"
                )
                db.add(approval)
                db.commit()
                logger.info(f"✅ Approval created for manager: {manager.username}")
            else:
                logger.warning("⚠️ No active manager found to create approval")
        except Exception as e:
            logger.warning(f"Approval creation failed: {e}")
        
        # Step 9: Send notification (special alert if self-declaration OR duplicate suspected)
        try:
            if manager:
                from src.models.notification import Notification, NotificationType
                
                if is_self_declaration:
                    # ✅ Self-declaration alert
                    from src.config.self_declaration_limits import get_self_declaration_limit
                    max_limit = get_self_declaration_limit(current_user.grade, "per_claim")

                    grade_str = current_user.grade.value if hasattr(current_user.grade, 'value') else str(current_user.grade)
                    category_str = expense.category.value if hasattr(expense.category, 'value') else str(expense.category)
                    
                    alert_message = (
                        f"⚠️ SELF-DECLARED EXPENSE (NO BILL)\n\n"
                        f"Employee: {current_user.full_name} ({current_user.username})\n"
                        f"Grade: {grade_str}\n"  # ✅ FIXED
                        f"Expense: {expense.expense_number}\n"
                        f"Amount: ₹{expense.amount:,.2f} (Limit: ₹{max_limit})\n"
                        f"Category: {category_str.upper()}\n\n"  # ✅ FIXED
                        f"🚫 Reason: {no_bill_reason}\n\n"
                        f"📝 Description: {description}\n\n"
                        f"⚠️ Verify carefully - no physical bill provided."
                    )
                    
                    notification = Notification(
                        user_id=manager.id,
                        type=NotificationType.EXPENSE_SUBMITTED,
                        title=f"⚠️ Self-Declaration (No Bill) - {expense.expense_number}",
                        message=alert_message,
                        expense_id=expense.id
                    )
                    db.add(notification)
                    db.commit()
                    logger.info(f"⚠️ Self-declaration alert sent to manager")
                    
                elif duplicate_check.get("is_duplicate"):

                    category_str = expense.category.value if hasattr(expense.category, 'value') else str(expense.category)
                    orig_status_str = duplicate_check['original_expense'].status.value if hasattr(duplicate_check['original_expense'].status, 'value') else str(duplicate_check['original_expense'].status)
                    # ✅ Send duplicate alert to manager
                    alert_message = (
                        f"⚠️ DUPLICATE SUSPECTED\n\n"
                        f"Employee: {current_user.full_name} ({current_user.username})\n"
                        f"New Expense: {expense.expense_number}\n"
                        f"Amount: ₹{expense.amount:,.2f}\n"
                        f"Category: {category_str}\n\n"  # ✅ FIXED
                        f"Similar to:\n"
                        f"• Original: {duplicate_check['original_expense'].expense_number}\n"
                        f"• Amount: ₹{duplicate_check['original_expense'].amount:,.2f}\n"
                        f"• Status: {orig_status_str.upper()}\n" 
                        f"• Bill #: {duplicate_check['original_expense'].bill_number}\n"
                        f"• Vendor: {duplicate_check['original_expense'].vendor_name}\n\n"
                        f"⚠️ Please review carefully before approval."
                    )
                    
                    duplicate_alert = Notification(
                        user_id=manager.id,
                        type=NotificationType.EXPENSE_SUBMITTED,
                        title=f"⚠️ Suspected Duplicate - {expense.expense_number}",
                        message=alert_message,
                        expense_id=expense.id
                    )
                    db.add(duplicate_alert)
                    db.commit()
                    logger.info(f"⚠️ Duplicate alert sent to manager")
                else:
                    # ✅ FIXED: Normal notification - CREATE MANUALLY
                    notification = Notification(
                        user_id=manager.id,
                        type=NotificationType.EXPENSE_SUBMITTED,
                        title=f"New Expense Claim - {expense.expense_number}",
                        message=(
                            f"📋 New Expense Claim Submitted\n\n"
                            f"Employee: {current_user.full_name}\n"
                            f"Expense Number: {expense.expense_number}\n"
                            f"Amount: ₹{expense.amount:,.2f}\n"
                            f"Category: {expense.category.upper()}\n"
                            f"Description: {expense.description}\n\n"
                            f"Please review and approve."
                        ),
                        expense_id=expense.id
                    )
                    db.add(notification)
                    db.commit()
                    logger.info(f"✅ Notification sent to manager: {manager.username}")
            else:
                logger.warning("⚠️ No manager to notify")
        except Exception as e:
            logger.warning(f"Notification failed: {e}")
        
        # Step 10: Index in Elasticsearch
        try:
            from src.services.elasticsearch_service import elasticsearch_service
            await elasticsearch_service.index_expense(expense)
        except Exception as e:
            logger.warning(f"Elasticsearch indexing failed: {e}")
        
        # Step 11: Create user-friendly response
        user_message = (
            f"✅ Expense claim submitted successfully!\n\n"
            f"📋 Claim Details:\n"
            f"• Expense Number: {expense.expense_number}\n"
            f"• Amount Claimed: ₹{expense.amount:,.2f}\n"
            f"• Category: {expense.category.capitalize()}\n"
            f"• Expense Date: {expense.expense_date.strftime('%d %B %Y')}\n"
            f"• Description: {expense.description}\n"
        )
        
        if is_self_declaration:
            user_message += f"\n⚠️ SELF-DECLARATION:\n• Reason: {no_bill_reason}\n• Requires manager verification\n"
        
        user_message += f"\n🕐 Submission Time:\n• {expense.submitted_at.strftime('%d %B %Y at %I:%M %p')}\n\n"
        
        if not is_self_declaration:
            user_message += (
                f"📊 AI Analysis Result:\n"
                f"• Recommendation: {expense.ai_recommendation}\n"
                f"• Confidence Score: {expense.ai_confidence_score}%\n"
                f"• Bill Authentic: {'Yes' if expense.is_valid_bill else 'No' if expense.is_valid_bill is not None else 'Under Review'}\n\n"
            )
        
        # ✅ Add duplicate warning if suspected
        if duplicate_check.get("is_duplicate"):
            user_message += (
                f"⚠️ IMPORTANT NOTICE:\n"
                f"This bill appears similar to expense {duplicate_check['original_expense'].expense_number}.\n"
                f"Your manager will review this carefully.\n\n"
            )
        
        user_message += f"📤 Status: Your claim has been sent to the approval team for review."
        
        # Step 12: Create filtered response
        filtered_expense = {
            "id": expense.id,
            "expense_number": expense.expense_number,
            "amount": expense.amount,
            "currency": expense.currency,
            "category": expense.category,
            "expense_date": expense.expense_date,
            "description": expense.description,
            "travel_mode": expense.travel_mode,
            "travel_from": expense.travel_from,
            "travel_to": expense.travel_to,
            "bill_file_name": expense.bill_file_name,
            "bill_number": expense.bill_number,
            "vendor_name": expense.vendor_name,
            "status": expense.status,
            "submitted_at": expense.submitted_at,
            "created_at": expense.created_at,
            
            # ✅ Add self-declaration status
            "is_self_declaration": expense.is_self_declaration,
            "declaration_reason": expense.declaration_reason,
            
            # ✅ Add duplicate status
            "duplicate_check_status": expense.duplicate_check_status,
            "is_suspected_duplicate": duplicate_check.get("is_duplicate"),
            
            # Limited AI analysis
            "ai_analysis": {
                "bill_number": ai_analysis.get("bill_number"),
                "bill_date": ai_analysis.get("bill_date"),
                "vendor_name": ai_analysis.get("vendor_name"),
                "extracted_amount": ai_analysis.get("extracted_amount"),
                "has_gst": ai_analysis.get("has_gst"),
                "travel_mode": ai_analysis.get("travel_mode"),
                "travel_route": ai_analysis.get("travel_route"),
            }
        }
        
        return {
            "success": True,
            "message": user_message,
            "expense": filtered_expense,
            # ✅ Include duplicate warning if detected
            "duplicate_warning": duplicate_check.get("message") if duplicate_check.get("is_duplicate") else None,
            # ✅ Include self-declaration notice
            "self_declaration_notice": "No bill provided - requires manager verification" if is_self_declaration else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error creating expense: %s", str(e), exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create expense claim: {str(e)}"
        )

@router.post("/claim-multi", status_code=status.HTTP_201_CREATED)
async def create_multi_bill_claim(
    # Trip Information (Optional - for multi-day trips)
    trip_start_date: Optional[str] = Form(None),
    trip_end_date: Optional[str] = Form(None),
    trip_purpose: Optional[str] = Form(None),
    
    # Bill Information (Arrays - one value per bill)
    categories: List[str] = Form(...),
    amounts: str = Form(...),  # ✅ CHANGED: Accept as string to handle comma-separated format
    expense_dates: List[str] = Form(...),
    descriptions: List[str] = Form(...),
    
    # Travel specific (optional, parallel arrays)
    travel_modes: Optional[List[str]] = Form(None),
    travel_from_list: Optional[List[str]] = Form(None),
    travel_to_list: Optional[List[str]] = Form(None),
    
    # Bill Files (PDFs or Images)
    bill_files: List[UploadFile] = File(...),
    
    # Dependencies
    current_user: User = Depends(auth_service.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create expense claim with MULTIPLE bills with duplicate detection
    ✅ FIXED: Handles both "130,510" and proper array formats
    """
    
    try:
        logger.info(f"User {current_user.username} creating multi-bill expense with {len(bill_files)} bills")
        
        # 1. Validate user permissions
        if not current_user.can_claim_expenses:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to claim expenses"
            )
        
        # ✅ NEW: Parse amounts - handle both comma-separated string and array
        logger.info(f"Raw amounts received: {amounts} (type: {type(amounts)})")
        
        parsed_amounts = []
        
        if isinstance(amounts, str):
            # Check if it's comma-separated (e.g., "130,510,200")
            if ',' in amounts:
                logger.info(f"Detected comma-separated amounts string")
                amount_strings = amounts.split(',')
            else:
                # Single amount as string
                amount_strings = [amounts]
            
            # Parse each amount
            for i, amount_str in enumerate(amount_strings):
                try:
                    cleaned = float(amount_str.strip())
                    if cleaned <= 0:
                        raise ValueError("Amount must be positive")
                    parsed_amounts.append(cleaned)
                except (ValueError, AttributeError) as e:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid amount for bill #{i+1}: '{amount_str}'. Please enter a valid number."
                    )
        elif isinstance(amounts, list):
            # Already a list - parse each item
            for i, amount_item in enumerate(amounts):
                try:
                    cleaned = float(str(amount_item).strip())
                    if cleaned <= 0:
                        raise ValueError("Amount must be positive")
                    parsed_amounts.append(cleaned)
                except (ValueError, AttributeError) as e:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid amount for bill #{i+1}: '{amount_item}'. Please enter a valid number."
                    )
        else:
            # Try to parse as single float
            try:
                cleaned = float(amounts)
                if cleaned <= 0:
                    raise ValueError("Amount must be positive")
                parsed_amounts.append(cleaned)
            except (ValueError, AttributeError) as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid amounts format: {amounts}"
                )
        
        logger.info(f"✅ Successfully parsed {len(parsed_amounts)} amounts: {parsed_amounts}")
        
        # Use parsed amounts from now on
        amounts = parsed_amounts
        
        # 2. Validate input lengths match
        if not (len(categories) == len(amounts) == len(expense_dates) == len(descriptions) == len(bill_files)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Mismatch: {len(categories)} categories, {len(amounts)} amounts, {len(expense_dates)} dates, {len(descriptions)} descriptions, {len(bill_files)} files. All must match!"
            )
        
        # 3. Parse trip dates
        trip_start = None
        trip_end = None
        trip_duration_days = None
        
        if trip_start_date and trip_end_date:
            try:
                trip_start = datetime.strptime(trip_start_date, "%Y-%m-%d").date()
                trip_end = datetime.strptime(trip_end_date, "%Y-%m-%d").date()
                
                if trip_end < trip_start:
                    raise ValueError("End date must be after start date")
                
                trip_duration_days = (trip_end - trip_start).days + 1
                
            except ValueError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid trip dates: {str(e)}"
                )
        
        # 4. Parse and validate expense dates
        parsed_expense_dates = []
        for i, date_str in enumerate(expense_dates):
            try:
                exp_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                parsed_expense_dates.append(exp_date)
                
                # Validate against trip dates
                if trip_start and trip_end:
                    if not (trip_start <= exp_date <= trip_end):
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Bill #{i+1} dated {exp_date} falls outside trip dates ({trip_start} to {trip_end})"
                        )
                        
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid date format for bill #{i+1}: {date_str}. Use YYYY-MM-DD"
                )
        
        # 5. Save all bill files
        logger.info(f"Saving {len(bill_files)} bill files...")
        saved_files = []
        
        for idx, file in enumerate(bill_files):
            file_path, filename = await save_upload_file(file, current_user.id)
            
            saved_files.append({
                "file_path": file_path,
                "filename": filename,
                "category": categories[idx],
                "amount": amounts[idx],
                "expense_date": parsed_expense_dates[idx],
                "description": descriptions[idx],
                "travel_mode": travel_modes[idx] if travel_modes and idx < len(travel_modes) else None,
                "travel_from": travel_from_list[idx] if travel_from_list and idx < len(travel_from_list) else None,
                "travel_to": travel_to_list[idx] if travel_to_list and idx < len(travel_to_list) else None
            })
        
        # ✅✅✅ 5.5: DUPLICATE DETECTION FOR EACH BILL (NEW!) ✅✅✅
        logger.info("🔍 Starting duplicate detection for multi-bill claim...")
        from src.utils.duplicate_detector import DuplicateDetector
        
        duplicate_detected = False
        duplicate_details = []
        blocked_bills = []
        
        # 6. Analyze each bill with AI AND check for duplicates
        logger.info(f"Analyzing {len(saved_files)} bills with AI...")
        bill_analyses = []
        
        for idx, bill_data in enumerate(saved_files):
            logger.info(f"Analyzing bill {idx+1}/{len(saved_files)}: {bill_data['filename']}")
            
            ai_analysis = await ai_service.analyze_bill(
                file_path=bill_data["file_path"],
                category=bill_data["category"],
                amount=bill_data["amount"],
                user_grade=current_user.grade.value if hasattr(current_user.grade, 'value') else str(current_user.grade),
                description=bill_data["description"]
            )
            
            bill_data["ai_analysis"] = ai_analysis
            
            # ✅ Check for duplicates for this bill
            duplicate_check = DuplicateDetector.perform_full_check(
                db=db,
                file_path=bill_data["file_path"],
                bill_number=ai_analysis.get("bill_number"),
                vendor_name=ai_analysis.get("vendor_name"),
                bill_date=ai_analysis.get("bill_date"),
                employee_id=current_user.id
            )
            
            bill_data["duplicate_check"] = duplicate_check
            bill_data["file_hash"] = duplicate_check["file_hash"]
            
            # If any bill is exact duplicate - BLOCK entire submission
            if duplicate_check["should_block"]:
                blocked_bills.append({
                    "bill_number": idx + 1,
                    "filename": bill_data["filename"],
                    "message": duplicate_check["message"]
                })
            
            # If suspected duplicate - Flag for review
            if duplicate_check["is_duplicate"]:
                duplicate_detected = True
                duplicate_details.append({
                    "bill_number": idx + 1,
                    "filename": bill_data["filename"],
                    "duplicate_type": duplicate_check["duplicate_type"],
                    "original_expense": duplicate_check["original_expense"].expense_number
                })
            
            bill_analyses.append(bill_data)
        
        # ✅ If any bill is blocked - REJECT entire submission
        if blocked_bills:
            error_message = "⚠️ DUPLICATE FILES DETECTED - Submission blocked!\n\n"
            for blocked in blocked_bills:
                error_message += f"Bill #{blocked['bill_number']} ({blocked['filename']}):\n{blocked['message']}\n\n"
            error_message += "Please remove duplicate bills and resubmit."
            
            logger.error(f"🚫 BLOCKING multi-bill submission: {len(blocked_bills)} duplicates found")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_message
            )
        
        # 7. Combine AI recommendations
        combined_recommendation = "APPROVE"
        has_rejections = False
        has_reviews = False
        
        for bill_data in bill_analyses:
            rec = bill_data["ai_analysis"].get("recommendation", "REVIEW")
            if rec == "REJECT":
                has_rejections = True
                combined_recommendation = "REJECT"
                break
            elif rec == "REVIEW":
                has_reviews = True
                combined_recommendation = "REVIEW"
        
        # 8. Calculate totals
        total_amount = sum(amounts)
        bill_count = len(bill_files)
        average_per_day = 0.0
        
        if trip_duration_days and trip_duration_days > 0:
            average_per_day = round(total_amount / trip_duration_days, 2)
        
        # 9. Calculate per-day breakdown
        per_day_breakdown = []
        if trip_start and trip_end:
            current_date = trip_start
            while current_date <= trip_end:
                day_bills = [b for b in bill_analyses if b["expense_date"] == current_date]
                
                day_total = sum(b["amount"] for b in day_bills)
                day_food = sum(b["amount"] for b in day_bills if b["category"] == "food")
                day_travel = sum(b["amount"] for b in day_bills if b["category"] == "travel")
                
                per_day_breakdown.append({
                    "date": current_date.isoformat(),
                    "total_amount": day_total,
                    "food_amount": day_food,
                    "travel_amount": day_travel,
                    "bill_count": len(day_bills)
                })
                
                current_date += timedelta(days=1)
        
        # 10. Generate expense number
        expense_number = generate_expense_number()
        
        # ✅ Determine duplicate status for entire claim
        overall_duplicate_status = "suspected" if duplicate_detected else "clean"
        first_duplicate_ref = duplicate_details[0]["original_expense"] if duplicate_details else None
        
        # 11. Create expense record with duplicate detection
        expense = Expense(
            expense_number=expense_number,
            employee_id=current_user.id,
            
            # Trip information
            trip_start_date=trip_start,
            trip_end_date=trip_end,
            trip_purpose=trip_purpose,
            trip_duration_days=trip_duration_days,
            
            # Multi-bill information
            is_multi_bill=True,
            bill_count=bill_count,
            bill_files=json.dumps(saved_files, default=str),
            
            # Amounts
            category=categories[0].strip().lower(),
            amount=total_amount,
            currency="INR",
            
            # Dates
            expense_date=parsed_expense_dates[0],
            
            # Description
            description=f"{bill_count} bills: " + ", ".join(descriptions[:3]) + ("..." if len(descriptions) > 3 else ""),
            
            # Travel info
            travel_mode=saved_files[0].get("travel_mode") if categories[0] == "travel" else None,
            travel_from=saved_files[0].get("travel_from"),
            travel_to=saved_files[0].get("travel_to"),
            
            # File paths
            bill_file_path=saved_files[0]["file_path"],
            bill_file_name=saved_files[0]["filename"],
            
            # AI Analysis
            ai_analysis={"bill_analyses": bill_analyses, "combined_recommendation": combined_recommendation},
            ai_summary=f"Analyzed {bill_count} bills. {combined_recommendation}. Avg: ₹{average_per_day}/day",
            ai_recommendation=combined_recommendation,
            ai_confidence_score=85.0,
            
            # Per-day breakdown
            per_day_breakdown=json.dumps(per_day_breakdown, default=str),
            average_per_day=average_per_day,
            
            # Validation
            is_within_limits=not has_rejections,
            is_within_daily_limits=True,
            validation_errors=["Multiple bills - requires review"] if bill_count > 1 else [],
            
            # Status
            status="submitted",
            current_approver_level="MANAGER",
            submitted_at=datetime.now(),
            
            # ✅ Duplicate detection (use first bill's hash)
            file_hash=saved_files[0]["file_hash"],
            duplicate_check_status=overall_duplicate_status,
            duplicate_of_expense_id=None,  # Multi-bill claims don't link to single original
            duplicate_detected_at=datetime.now() if duplicate_detected else None
        )
        
        db.add(expense)
        db.commit()
        db.refresh(expense)
        
        logger.info(f"✅ Multi-bill expense {expense_number} created with {bill_count} bills")
        
        if duplicate_detected:
            logger.warning(f"⚠️ {len(duplicate_details)} bills flagged as suspected duplicates")
        
        # ✅ NEW: Send confirmation email for multi-bill claim
        try:
            from src.services.email_service import email_service
            
            email_service.send_submission_confirmation(
                to_email=current_user.email,
                employee_name=current_user.full_name,
                expense_data={
                    "id": expense.id,
                    "expense_number": expense.expense_number,
                    "bill_number": f"{bill_count} bills",
                    "vendor_name": "Multiple vendors",
                    "amount": total_amount,
                    "category": "Multiple categories",
                    "expense_date": f"{trip_start.strftime('%d %b') if trip_start else 'N/A'} to {trip_end.strftime('%d %b') if trip_end else 'N/A'}",
                    "description": expense.description,
                    "submitted_at": expense.submitted_at.strftime('%d %B %Y at %I:%M %p')
                }
            )
            logger.info(f"📧 Multi-bill confirmation email sent to {current_user.email}")
        except Exception as e:
            logger.warning(f"Failed to send confirmation email: {e}")
        
        # 12. Create approvals
        manager = None
        try:
            from src.models.approval import Approval
            from src.models.user import UserRole
            
            manager = db.query(User).filter(
                User.role == UserRole.MANAGER,
                User.is_active == True
            ).first()
            
            if manager:
                approval = Approval(
                    expense_id=expense.id,
                    approver_id=manager.id,
                    level="MANAGER",
                    status="PENDING"
                )
                db.add(approval)
                db.commit()
                logger.info(f"✅ Approval created for manager: {manager.username}")
            else:
                logger.warning("⚠️ No active manager found to create approval")
        except Exception as e:
            logger.warning(f"Approval creation failed: {e}")
        
        # 13. Send notification (with duplicate alert if needed)
        try:
            if manager:
                if duplicate_detected:
                    # ✅ Send duplicate alert
                    from src.models.notification import Notification, NotificationType
                    
                    alert_message = (
                        f"⚠️ MULTI-BILL CLAIM WITH SUSPECTED DUPLICATES\n\n"
                        f"Employee: {current_user.full_name} ({current_user.username})\n"
                        f"Expense: {expense.expense_number}\n"
                        f"Total Amount: ₹{total_amount:,.2f}\n"
                        f"Bill Count: {bill_count}\n\n"
                        f"Suspected Duplicate Bills:\n"
                    )
                    
                    for detail in duplicate_details:
                        alert_message += f"• Bill #{detail['bill_number']} ({detail['filename']}) - similar to {detail['original_expense']}\n"
                    
                    alert_message += "\n⚠️ Please review all bills carefully before approval."
                    
                    duplicate_alert = Notification(
                        user_id=manager.id,
                        type=NotificationType.EXPENSE_SUBMITTED,
                        title=f"⚠️ Multi-Bill with Duplicates - {expense.expense_number}",
                        message=alert_message,
                        expense_id=expense.id
                    )
                    db.add(duplicate_alert)
                    db.commit()
                    logger.info(f"⚠️ Duplicate alert sent to manager")
                else:
                    # ✅ FIXED: Normal notification - CREATE MANUALLY
                    from src.models.notification import Notification, NotificationType
                    
                    notification = Notification(
                        user_id=manager.id,
                        type=NotificationType.EXPENSE_SUBMITTED,
                        title=f"New Multi-Bill Expense - {expense.expense_number}",
                        message=(
                            f"📋 New Multi-Bill Expense Submitted\n\n"
                            f"Employee: {current_user.full_name}\n"
                            f"Total Amount: ₹{total_amount:,.2f}\n"
                            f"Bill Count: {bill_count}\n\n"
                            f"Please review and approve."
                        ),
                        expense_id=expense.id
                    )
                    db.add(notification)
                    db.commit()
                    logger.info(f"✅ Notification sent to manager: {manager.username}")
            else:
                logger.warning("⚠️ No manager to notify")
        except Exception as e:
            logger.warning(f"Notification failed: {e}")
        
        # 14. Index in Elasticsearch
        try:
            from src.services.elasticsearch_service import elasticsearch_service
            await elasticsearch_service.index_expense(expense)
        except Exception as e:
            logger.warning(f"Elasticsearch indexing failed: {e}")
        
        # 15. Return response
        response_message = f"Expense claim created with {bill_count} bills"
        if duplicate_detected:
            response_message += f"\n\n⚠️ WARNING: {len(duplicate_details)} bill(s) appear similar to previously submitted expenses. Your manager will review carefully."
        
        return {
            "success": True,
            "message": response_message,
            "duplicate_warning": duplicate_details if duplicate_detected else None,
            "expense": {
                "id": expense.id,
                "expense_number": expense.expense_number,
                "total_amount": total_amount,
                "bill_count": bill_count,
                "is_multi_bill": True,
                "duplicate_check_status": overall_duplicate_status,
                "is_suspected_duplicate": duplicate_detected,
                
                # Trip info
                "trip_start_date": trip_start.isoformat() if trip_start else None,
                "trip_end_date": trip_end.isoformat() if trip_end else None,
                "trip_duration_days": trip_duration_days,
                "trip_purpose": trip_purpose,
                
                # Analysis
                "ai_recommendation": combined_recommendation,
                "ai_summary": expense.ai_summary,
                "average_per_day": average_per_day,
                
                # Per-day breakdown
                "per_day_breakdown": per_day_breakdown,
                
                # Bills info
                "bills": [
                    {
                        "filename": f["filename"],
                        "category": f["category"],
                        "amount": f["amount"],
                        "date": f["expense_date"].isoformat(),
                        "ai_recommendation": f["ai_analysis"].get("recommendation", "REVIEW"),
                        "is_suspected_duplicate": f["duplicate_check"]["is_duplicate"]
                    }
                    for f in saved_files
                ],
                
                # Status
                "status": expense.status,
                "created_at": expense.created_at.isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error creating multi-bill expense: %s", str(e), exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create expense claim: {str(e)}"
        )


@router.get("/my-expenses")
async def get_my_expenses(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_service.get_current_user)
):
    """Get current user's expenses (filtered for security)"""
    
   
    db.expire_all()  # Force fresh data from database
    
    expenses = db.query(Expense).filter(
        Expense.employee_id == current_user.id
    ).order_by(Expense.created_at.desc()).offset(skip).limit(limit).all()
    
    
    for expense in expenses:
        db.refresh(expense)
    
    total = db.query(Expense).filter(Expense.employee_id == current_user.id).count()
    
    # Filter expenses to hide sensitive AI details
    filtered_expenses = [filter_expense_for_employee(exp) for exp in expenses]
    
    return {
        "expenses": filtered_expenses,
        "total": total,
        "skip": skip,
        "limit": limit
    }



# ============================================
# ADD THIS SINGLE ENDPOINT TO YOUR expense.py
# Replace the get_pending_approvals endpoint with this
# ============================================

@router.get("/bill-status/{expense_number}")
async def get_bill_status(
    expense_number: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_service.get_current_user)
):
    """
    Get status of an expense bill by expense number
    
    Employees can check:
    - Current status (submitted/approved/rejected)
    - Manager comments (if rejected)
    - AI analysis summary (if rejected)
    - Approval timeline
    """
    try:
        # Step 1: Find expense by expense_number
        expense = db.query(Expense).filter(
            Expense.expense_number == expense_number
        ).first()
        
        if not expense:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Expense with number '{expense_number}' not found"
            )
        
        # Step 2: Check if this expense belongs to the current user
        if expense.employee_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only check status of your own expenses"
            )
        
        logger.info(f"Employee {current_user.username} checking status of {expense_number}")
        
        # Step 3: Get approval history
        from src.models.approval import Approval
        approvals = db.query(Approval).filter(
            Approval.expense_id == expense.id
        ).order_by(Approval.created_at.desc()).all()
        
        approval_history = []
        manager_comments = None
        rejection_details = None
        
        for approval in approvals:
            approver = db.query(User).filter(User.id == approval.approver_id).first()
            
            # Build approval record with appropriate labels
            approval_record = {
                "level": approval.level,
                "status": approval.status,
                "reviewed_at": approval.reviewed_at.isoformat() if approval.reviewed_at else None,
                "created_at": approval.created_at.isoformat()
            }
            
            # Get status as string (handle both enum and string types)
            if hasattr(approval.status, 'value'):
                # It's an enum
                approval_status_str = str(approval.status.value).upper()
            else:
                # It's already a string
                approval_status_str = str(approval.status).upper()
            
            logger.info(f"Processing approval: status={approval.status}, status_str={approval_status_str}, type={type(approval.status)}")
            
            # Add appropriate name/role based on status
            if approval_status_str == "APPROVED":
                approval_record["approver_name"] = approver.full_name if approver else "Unknown"
                approval_record["approver_role"] = approval.level
                approval_record["comments"] = approval.comments
            elif approval_status_str == "REJECTED":
                approval_record["rejector_name"] = approver.full_name if approver else "Unknown"
                approval_record["rejector_role"] = approval.level
                approval_record["rejection_reason"] = approval.comments
            else:  # PENDING
                approval_record["pending_with_name"] = approver.full_name if approver else "Unknown"
                approval_record["pending_with_role"] = approval.level
            
            approval_history.append(approval_record)
            
            # If rejected, capture the details
            if approval_status_str == "REJECTED":
                manager_comments = approval.comments
                rejection_details = {
                    "rejected_by_name": approver.full_name if approver else "Unknown",
                    "rejected_by_role": approval.level,
                    "rejected_at": approval.reviewed_at.isoformat() if approval.reviewed_at else None,
                    "rejection_reason": approval.comments
                }
        
        # Step 4: Build response based on status
        response = {
            "success": True,
            "expense_number": expense.expense_number,
            "status": expense.status,
            "amount": expense.amount,
            "category": expense.category,
            "description": expense.description,
            "submitted_at": expense.submitted_at.isoformat(),
            "bill_file_name": expense.bill_file_name
        }
        
        # Step 5: Add status-specific information
        if expense.status == "submitted":
            # Still pending review
            response["message"] = "📋 Your expense claim is under review"
            response["current_stage"] = expense.current_approver_level
            response["pending_with"] = f"{expense.current_approver_level} department"
            
        elif expense.status == "rejected":
            # REJECTED - Show full details
            response["message"] = "❌ Your expense claim has been rejected"
            response["rejection_details"] = rejection_details
            response["manager_comments"] = manager_comments or expense.rejection_reason
            
            # Add AI analysis summary for rejected bills
            if expense.ai_analysis:
                ai_data = expense.ai_analysis
                ai_summary_text = ""
                
                ai_summary_text += f"📊 AI Analysis:\n"
                ai_summary_text += f"• Authenticity: {'✅ Authentic' if ai_data.get('is_authentic') else '❌ Not Authentic'}\n"
                ai_summary_text += f"• Confidence: {ai_data.get('confidence_score', 0)}%\n"
                ai_summary_text += f"• AI Recommendation: {ai_data.get('recommendation', 'N/A')}\n"
                
                # Add red flags if present
                red_flags = ai_data.get('red_flags', [])
                if red_flags:
                    ai_summary_text += f"• Issues Found: {len(red_flags)}\n"
                    for i, flag in enumerate(red_flags[:3], 1):
                        ai_summary_text += f"  {i}. {flag}\n"
                
                # Add AI summary
                if ai_data.get('summary'):
                    ai_summary_text += f"\n💡 Summary: {ai_data.get('summary')}\n"
                
                response["ai_analysis_summary"] = ai_summary_text.strip()
            
            # Add what employee should do next
            response["next_steps"] = (
                "You can:\n"
                "1. Review the rejection reason and AI analysis\n"
                "2. Upload a new claim with the correct bill/invoice\n"
                "3. Contact your manager if you have questions"
            )
            
        elif expense.status == "approved":
            # APPROVED
            response["message"] = "✅ Your expense claim has been approved!"
            response["approved_at"] = expense.approved_at.isoformat() if expense.approved_at else None
            response["next_steps"] = "Your reimbursement will be processed in the next payment cycle"
        
        # Step 6: Add approval timeline
        response["approval_history"] = approval_history
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting bill status: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get bill status: {str(e)}"
        )


@router.get("/{expense_id}")
async def get_expense(
    expense_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_service.get_current_user)
):
    """Get specific expense details (filtered based on role)"""
    
    # ✅ ADD THESE TWO LINES AT THE START
    db.expire_all()  # Force fresh data
    
    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    # ✅ ADD THIS LINE AFTER THE QUERY
    db.refresh(expense)
    
    # Check permission
    from src.models.user import UserRole
    
    # Check if user is the owner
    is_owner = expense.employee_id == current_user.id
    
    # Check if user is manager/HR/finance/admin
    is_approver = current_user.role in [
        UserRole.MANAGER, UserRole.HR, UserRole.FINANCE, UserRole.ADMIN
    ]
    
    if not is_owner and not is_approver:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # If employee viewing their own expense, filter sensitive data
    if is_owner and not is_approver:
        return filter_expense_for_employee(expense)
    
    # If manager/HR/finance viewing, return full details
    return expense


@router.put("/{expense_id}")
async def update_expense(
    expense_id: int,
    category: Optional[str] = Form(None),
    amount: Optional[float] = Form(None),
    expense_date: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    travel_mode: Optional[str] = Form(None),
    travel_from: Optional[str] = Form(None),
    travel_to: Optional[str] = Form(None),
    bill_file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_service.get_current_user)
):
    """
    Update an existing expense claim
    
    Rules:
    - Only the owner can update
    - Can ONLY update if status is 'submitted' (pending)
    - CANNOT update if 'approved' or 'rejected'
    - If employee tries to update approved/rejected, notify manager
    """
    try:
        # Step 1: Get existing expense
        expense = db.query(Expense).filter(Expense.id == expense_id).first()
        
        if not expense:
            raise HTTPException(status_code=404, detail="Expense not found")
        
        # Step 2: Check ownership
        if expense.employee_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only update your own expenses"
            )
        
        # Step 3: Check if expense can be edited
        # ✅ NEW LOGIC: Only allow editing if 'submitted' (pending review)
        if expense.status != "submitted":
            # Employee trying to update approved/rejected expense - ALERT MANAGER!
            logger.warning(f"⚠️ Employee {current_user.username} attempted to update expense {expense.expense_number} with status '{expense.status}'")
            
            # Send notification to manager
            try:
                from src.models.notification import Notification, NotificationType
                from src.models.user import UserRole
                
                # Find manager
                manager = db.query(User).filter(
                    User.role == UserRole.MANAGER,
                    User.is_active == True
                ).first()
                
                if manager:

                    # Create alert notification
                    category_str = expense.category.value if hasattr(expense.category, 'value') else str(expense.category)
                    status_str = expense.status.value if hasattr(expense.status, 'value') else str(expense.status)
                    
                    # Create alert notification
                    alert_message = (
                        f"🚨 UPDATE ATTEMPT ALERT\n\n"
                        f"Employee: {current_user.full_name} ({current_user.username})\n"
                        f"Employee ID: {current_user.employee_id}\n"
                        f"Department: {current_user.department}\n\n"
                        f"Attempted to update:\n"
                        f"• Expense Number: {expense.expense_number}\n"
                        f"• Amount: ₹{expense.amount:,.2f}\n"
                        f"• Category: {category_str.upper()}\n"
                        f"• Description: {expense.description}\n"
                        f"• Current Status: {status_str.upper()}\n"
                        f"• Submitted Date: {expense.submitted_at.strftime('%d %B %Y')}\n"
                        f"• Bill: {expense.bill_file_name}\n\n"
                        f"⚠️ Update blocked - expense is {status_str}!"
                    )
                    
                    notification = Notification(
                        user_id=manager.id,
                        type=NotificationType.EXPENSE_REJECTED,
                        title=f"⚠️ Unauthorized Update Attempt by {current_user.full_name}",
                        message=alert_message,
                        expense_id=expense.id
                    )
                    db.add(notification)
                    db.commit()
                    
                    logger.info(f"📧 Alert sent to manager {manager.username} about update attempt")
                    
            except Exception as e:
                logger.error(f"Failed to send manager alert: {e}")
            
            # Return error to employee
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Cannot update expense with status '{expense.status}'. Only expenses with status 'submitted' (pending review) can be updated. The expense has already been {expense.status}. Please contact your manager for assistance. Your manager has been notified of this attempt."
            )
        
        logger.info(f"User {current_user.username} updating expense {expense.expense_number}")
        
        # Step 4: Update fields if provided
        if category:
            expense.category = category.strip().lower()
        
        if amount is not None:
            expense.amount = amount
        
        if expense_date:
            try:
                expense.expense_date = datetime.strptime(expense_date, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid date format. Use YYYY-MM-DD"
                )
        
        if description:
            expense.description = description
        
        if travel_mode:
            expense.travel_mode = travel_mode
        
        if travel_from:
            expense.travel_from = travel_from
        
        if travel_to:
            expense.travel_to = travel_to
        
        # Step 5: Handle new bill file if provided
        if bill_file:
            logger.info(f"Updating bill file: {bill_file.filename}")
            file_path, saved_filename = await save_upload_file(bill_file, current_user.id)
            
            # Re-analyze with AI
            logger.info("Re-analyzing bill with AI...")
            ai_analysis = await ai_service.analyze_bill(
                file_path=file_path,
                category=expense.category,
                amount=expense.amount,
                user_grade=current_user.grade.value if hasattr(current_user.grade, 'value') else str(current_user.grade),
                description=expense.description
            )
            
            # Update file and AI fields
            expense.bill_file_path = file_path
            expense.bill_file_name = saved_filename
            expense.bill_number = ai_analysis.get("bill_number")
            expense.vendor_name = ai_analysis.get("vendor_name")
            expense.ai_analysis = ai_analysis
            expense.ai_summary = ai_analysis.get("summary", "")
            expense.ai_recommendation = ai_analysis.get("recommendation", "REVIEW")
            expense.ai_confidence_score = ai_analysis.get("confidence_score", 0)
            expense.is_valid_bill = ai_analysis.get("is_authentic")
            expense.has_gst = ai_analysis.get("has_gst")
            expense.has_required_stamps = ai_analysis.get("has_required_stamps")
            expense.is_within_limits = ai_analysis.get("is_within_limits", (True, None))[0] if isinstance(ai_analysis.get("is_within_limits"), tuple) else True
            expense.validation_errors = ai_analysis.get("red_flags", [])
        
        # Step 6: Update timestamp
        expense.updated_at = datetime.now()
        
        # Step 7: Save changes
        db.commit()
        db.refresh(expense)
        
        logger.info(f"✅ Expense {expense.expense_number} updated successfully")
        
        # Step 8: Re-index in Elasticsearch
        try:
            from src.services.elasticsearch_service import elasticsearch_service
            await elasticsearch_service.index_expense(expense)
        except Exception as e:
            logger.warning(f"Elasticsearch indexing failed: {e}")
        
        # ✅ RETURN FILTERED RESPONSE FOR EMPLOYEE
        return filter_expense_for_employee(expense)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error updating expense: %s", str(e), exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update expense: {str(e)}"
        )


@router.delete("/{expense_id}", status_code=status.HTTP_200_OK)
async def delete_expense(
    expense_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_service.get_current_user)
):
    """
    Delete an expense claim
    
    Rules:
    - Employees can ONLY delete if status is 'submitted' (pending review)
    - Employees CANNOT delete if status is 'approved' or 'rejected'
    - If employee tries to delete approved/rejected, notify manager
    """
    try:
        # Step 1: Get existing expense
        expense = db.query(Expense).filter(Expense.id == expense_id).first()
        
        if not expense:
            raise HTTPException(status_code=404, detail="Expense not found")
        
        # Step 2: Check ownership
        if expense.employee_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only delete your own expenses"
            )
        
        # Step 3: Check if expense can be deleted
        # ✅ NEW LOGIC: Only allow deletion if 'submitted' (pending review)
        if expense.status != "submitted":
            # Employee trying to delete approved/rejected expense - ALERT MANAGER!
            logger.warning(f"⚠️ Employee {current_user.username} attempted to delete expense {expense.expense_number} with status '{expense.status}'")
            
            # Send notification to manager
            try:
                from src.models.notification import Notification, NotificationType
                from src.models.user import UserRole
                
                # Find manager
                manager = db.query(User).filter(
                    User.role == UserRole.MANAGER,
                    User.is_active == True
                ).first()
                
                if manager:
                    # ✅ FIXED: Get proper string values (handle both enum and string)
                    category_str = expense.category.value if hasattr(expense.category, 'value') else str(expense.category)
                    status_str = expense.status.value if hasattr(expense.status, 'value') else str(expense.status)
                    
                    # ✅ FIXED: Proper deletion alert message
                    alert_message = (
                        f"🚨 DELETION ATTEMPT ALERT\n\n"
                        f"Employee: {current_user.full_name} ({current_user.username})\n"
                        f"Employee ID: {current_user.employee_id}\n"
                        f"Department: {current_user.department}\n\n"
                        f"Attempted to delete:\n"
                        f"• Expense Number: {expense.expense_number}\n"
                        f"• Amount: ₹{expense.amount:,.2f}\n"
                        f"• Category: {category_str.upper()}\n"
                        f"• Description: {expense.description}\n"
                        f"• Current Status: {status_str.upper()}\n"
                        f"• Submitted Date: {expense.submitted_at.strftime('%d %B %Y')}\n"
                        f"• Bill: {expense.bill_file_name}\n\n"
                        f"⚠️ Deletion blocked - expense is {status_str}!"
                    )
                    
                    notification = Notification(
                        user_id=manager.id,
                        type=NotificationType.EXPENSE_REJECTED,  # Using existing type
                        title=f"⚠️ Unauthorized Deletion Attempt by {current_user.full_name}",
                        message=alert_message,
                        expense_id=expense.id
                    )
                    db.add(notification)
                    db.commit()
                    
                    logger.info(f"📧 Alert sent to manager {manager.username} about deletion attempt")
                    
            except Exception as e:
                logger.error(f"Failed to send manager alert: {e}")
            
            # Return error to employee
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Cannot delete expense with status '{expense.status}'. Only expenses with status 'submitted' (pending review) can be deleted. Your manager has been notified of this attempt."
            )
        
        logger.info(f"User {current_user.username} deleting expense {expense.expense_number}")
        
        # Step 4: Delete related notifications first (foreign key constraint)
        try:
            from src.models.notification import Notification
            deleted_notifications = db.query(Notification).filter(Notification.expense_id == expense_id).delete()
            logger.info(f"✅ Deleted {deleted_notifications} notifications for expense {expense_id}")
        except Exception as e:
            logger.warning(f"Error deleting notifications: {e}")
        
        # Step 5: Delete related approvals (foreign key constraint)
        try:
            from src.models.approval import Approval
            deleted_approvals = db.query(Approval).filter(Approval.expense_id == expense_id).delete()
            logger.info(f"✅ Deleted {deleted_approvals} approvals for expense {expense_id}")
        except Exception as e:
            logger.warning(f"Error deleting approvals: {e}")
        
        # Step 6: Delete from Elasticsearch
        try:
            from src.services.elasticsearch_service import elasticsearch_service
            await elasticsearch_service.delete_expense(expense_id)
        except Exception as e:
            logger.warning(f"Elasticsearch deletion failed: {e}")
        
        # Step 7: Delete expense
        expense_number = expense.expense_number
        db.delete(expense)
        db.commit()
        
        logger.info(f"✅ Expense {expense_number} deleted successfully")
        
        return {
            "success": True,
            "message": f"Expense {expense_number} deleted successfully",
            "expense_id": expense_id,
            "expense_number": expense_number
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error deleting expense: %s", str(e), exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete expense: {str(e)}"
        )