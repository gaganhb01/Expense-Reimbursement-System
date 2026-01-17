"""
Admin Routes
User management and system administration endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime, timedelta
import secrets
import string
import re

from src.config.database import get_db
from src.services.auth_service import auth_service
from src.models.user import User, UserRole, UserGrade
from src.models.expense import Expense
from src.schemas.user import UserResponse
from src.utils.logger import setup_logger
from src.utils.security import get_password_hash

logger = setup_logger()
router = APIRouter()


# ============================================
# NEW SCHEMAS FOR USER CREATION
# ============================================

class CreateUserRequest(BaseModel):
    """Request schema for creating new user with invitation"""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=100)
    # ✅ REMOVED: employee_id - now auto-generated
    role: str  # 'employee', 'manager', 'finance', 'admin'
    grade: str  # 'A', 'B', 'C', 'D'
    department: str
    phone: Optional[str] = None
    can_claim_expenses: bool = True
    send_invitation: bool = True


# ============================================
# HELPER FUNCTIONS
# ============================================

def generate_next_employee_id(db: Session) -> str:
    """
    Generate next employee ID in format: EMP001, EMP002, etc.
    
    Logic:
    1. Find all existing employee IDs that match pattern EMP###
    2. Extract the highest number
    3. Increment by 1
    4. Return new employee ID with leading zeros
    
    Examples:
    - No users yet → EMP001
    - Last user is EMP007 → EMP008
    - Last user is EMP099 → EMP100
    """
    try:
        # Get all employee IDs that match pattern "EMP" followed by digits
        all_users = db.query(User.employee_id).all()
        
        # Extract numbers from employee IDs like "EMP007"
        employee_numbers = []
        for (emp_id,) in all_users:
            if emp_id and emp_id.startswith("EMP"):
                # Extract numeric part (e.g., "007" from "EMP007")
                match = re.match(r'EMP(\d+)', emp_id)
                if match:
                    number = int(match.group(1))
                    employee_numbers.append(number)
        
        # Find highest number
        if employee_numbers:
            max_number = max(employee_numbers)
            next_number = max_number + 1
        else:
            # No existing employee IDs, start from 1
            next_number = 1
        
        # Format with leading zeros (e.g., 8 → "EMP008")
        new_employee_id = f"EMP{next_number:03d}"
        
        logger.info(f"✅ Generated employee ID: {new_employee_id}")
        return new_employee_id
        
    except Exception as e:
        logger.error(f"Error generating employee ID: {e}")
        # Fallback: use timestamp
        import time
        return f"EMP{int(time.time()) % 100000:05d}"


def generate_secure_token(length: int = 32) -> str:
    """Generate cryptographically secure random token"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def generate_temporary_password() -> str:
    """Generate temporary password (will be replaced when user sets password)"""
    return generate_secure_token(16)


def send_invitation_email(user: User, invitation_link: str):
    """Send cheerful invitation email to new user"""
    try:
        from src.services.email_service import email_service
        
        email_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 10px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">
                <!-- Header Section with UST Welcome -->
                <div style="text-align: center; padding: 30px 20px; background: white; border-radius: 10px; margin-bottom: 20px;">
                    <h1 style="color: #667eea; margin: 0 0 10px 0; font-size: 32px;">🎉 Welcome to UST! 🎉</h1>
                    <p style="color: #666; font-size: 18px; margin: 0;">We're thrilled to have you on board!</p>
                </div>
            </div>
            
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 10px; background: white; margin-top: -10px;">
                <div style="padding: 20px;">
                    <h2 style="color: #2563eb; margin-top: 0;">Welcome to the Expense Reimbursement System!</h2>
                    
                    <p style="font-size: 16px;">Hello <strong style="color: #667eea;">{user.full_name}</strong>,</p>
                    
                    <p style="font-size: 15px; line-height: 1.8;">
                        Great news! Your account has been created and you're just one step away from accessing our expense management platform. 
                        We're excited to help you manage your expenses seamlessly! 🚀
                    </p>
                    
                    <div style="background: linear-gradient(135deg, #667eea15 0%, #764ba215 100%); padding: 20px; border-radius: 10px; margin: 25px 0; border-left: 4px solid #667eea;">
                        <p style="margin: 0 0 15px 0; font-size: 15px; color: #555;">
                            <strong style="color: #667eea;">🔐 Let's get you started!</strong><br>
                            Click the button below to set your password and activate your account:
                        </p>
                    </div>
                    
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{invitation_link}" 
                           style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                                  color: white; 
                                  padding: 15px 40px; 
                                  text-decoration: none; 
                                  border-radius: 50px; 
                                  display: inline-block; 
                                  font-weight: bold; 
                                  font-size: 16px;
                                  box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
                                  transition: all 0.3s;">
                            ✨ Set Password & Activate Account ✨
                        </a>
                    </div>
                    
                    <div style="background-color: #f8f9ff; padding: 20px; border-radius: 10px; margin: 25px 0; border: 2px solid #e0e7ff;">
                        <h3 style="margin-top: 0; color: #1f2937; font-size: 18px;">📋 Your Account Details:</h3>
                        <table style="width: 100%; border-collapse: collapse;">
                            <tr>
                                <td style="padding: 8px 0; color: #666; font-weight: 500;">👤 Username:</td>
                                <td style="padding: 8px 0; color: #1f2937; font-weight: 600;">{user.username}</td>
                            </tr>
                            <tr>
                                <td style="padding: 8px 0; color: #666; font-weight: 500;">📧 Email:</td>
                                <td style="padding: 8px 0; color: #1f2937; font-weight: 600;">{user.email}</td>
                            </tr>
                            <tr>
                                <td style="padding: 8px 0; color: #666; font-weight: 500;">🆔 Employee ID:</td>
                                <td style="padding: 8px 0; color: #1f2937; font-weight: 600;">{user.employee_id}</td>
                            </tr>
                            <tr>
                                <td style="padding: 8px 0; color: #666; font-weight: 500;">💼 Role:</td>
                                <td style="padding: 8px 0; color: #1f2937; font-weight: 600;">{user.role.value if hasattr(user.role, 'value') else user.role}</td>
                            </tr>
                            <tr>
                                <td style="padding: 8px 0; color: #666; font-weight: 500;">⭐ Grade:</td>
                                <td style="padding: 8px 0; color: #1f2937; font-weight: 600;">{user.grade.value if hasattr(user.grade, 'value') else user.grade}</td>
                            </tr>
                            <tr>
                                <td style="padding: 8px 0; color: #666; font-weight: 500;">🏢 Department:</td>
                                <td style="padding: 8px 0; color: #1f2937; font-weight: 600;">{user.department or 'N/A'}</td>
                            </tr>
                        </table>
                    </div>
                    
                    <div style="background-color: #fef3c7; padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #f59e0b;">
                        <p style="margin: 0; color: #92400e; font-size: 14px;">
                            <strong>⏰ Important:</strong> This invitation link will expire in <strong>7 days</strong>. 
                            Don't wait too long! 😊
                        </p>
                    </div>
                    
                    <div style="background: linear-gradient(135deg, #10b98115 0%, #059b6915 100%); padding: 20px; border-radius: 10px; margin: 25px 0; text-align: center;">
                        <p style="margin: 0; font-size: 15px; color: #047857;">
                            <strong>🎯 What's Next?</strong><br>
                            After setting your password, you'll be able to:<br>
                            ✅ Submit expense claims<br>
                            ✅ Track reimbursement status<br>
                            ✅ View your expense history<br>
                            ✅ Access all UST expense management tools
                        </p>
                    </div>
                    
                    <p style="font-size: 14px; color: #666; margin-top: 25px;">
                        If you have any questions or need assistance, our support team is here to help! 
                        Feel free to reach out to your administrator. 💬
                    </p>
                    
                    <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 30px 0;">
                    
                    <p style="font-size: 13px; color: #9ca3af; margin-bottom: 10px;">
                        <strong>Didn't expect this email?</strong><br>
                        If you believe you received this email by mistake, please contact your administrator immediately.
                    </p>
                    
                    <p style="font-size: 12px; color: #9ca3af; margin: 15px 0;">
                        <em>This is an automated email. Please do not reply to this message.</em>
                    </p>
                    
                    <div style="background-color: #f9fafb; padding: 15px; border-radius: 8px; margin-top: 20px;">
                        <p style="font-size: 11px; color: #6b7280; margin: 0;">
                            <strong>💡 Tip:</strong> If you're having trouble clicking the button, copy and paste this link into your browser:<br>
                            <span style="color: #667eea; word-break: break-all;">{invitation_link}</span>
                        </p>
                    </div>
                    
                    <div style="text-align: center; margin-top: 30px; padding-top: 20px; border-top: 2px solid #e5e7eb;">
                        <p style="color: #667eea; font-weight: 600; font-size: 16px; margin: 0;">
                            Welcome aboard! Let's make expense management easy! 🚀
                        </p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        
        email_service.send_email(
            to_email=user.email,
            subject="🎉 Welcome to UST - Set Your Password & Get Started!",
            html_body=email_body
        )
        
        logger.info(f"📧 Invitation email sent to {user.email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send invitation email: {e}")
        return False


# ============================================
# NEW ENDPOINT - CREATE USER WITH AUTO-INCREMENT EMPLOYEE ID
# ============================================

@router.post("/users/create", status_code=status.HTTP_201_CREATED)
async def create_new_user(
    user_data: CreateUserRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_service.get_current_user)
):
    """
    Create new user and send invitation email (ADMIN ONLY)
    
    ✅ NEW: Employee ID is auto-generated (EMP001, EMP002, etc.)
    
    Flow:
    1. Admin creates user with all details (NO employee_id needed)
    2. System auto-generates employee_id (e.g., EMP008)
    3. System generates invitation token
    4. Invitation email sent to user
    5. User clicks link to set password
    6. Account activated
    """
    try:
        # Step 1: Check if current user is admin
        if current_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators can create new users"
            )
        
        logger.info(f"Admin {current_user.username} creating new user: {user_data.username}")
        
        # ✅ Step 1.5: Generate employee ID automatically
        employee_id = generate_next_employee_id(db)
        logger.info(f"🆔 Auto-generated employee ID: {employee_id}")
        
        # Step 2: Check if username already exists
        existing_user = db.query(User).filter(User.username == user_data.username).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Username '{user_data.username}' already exists"
            )
        
        # Step 3: Check if email already exists
        existing_email = db.query(User).filter(User.email == user_data.email).first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Email '{user_data.email}' already exists"
            )
        
        # Step 4: Validate role
        try:
            role_enum = UserRole(user_data.role.lower())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role '{user_data.role}'. Must be: employee, manager, finance, or admin"
            )
        
        # Step 5: Validate grade
        try:
            grade_enum = UserGrade(user_data.grade.upper())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid grade '{user_data.grade}'. Must be: A, B, C, or D"
            )
        
        # Step 6: Generate invitation token
        invitation_token = generate_secure_token(32)
        invitation_expires_at = datetime.now() + timedelta(days=7)  # Expires in 7 days
        
        # Step 7: Create temporary password (will be replaced when user sets password)
        temp_password = generate_temporary_password()
        hashed_temp_password = get_password_hash(temp_password)
        
        # Step 8: Create new user with auto-generated employee_id
        new_user = User(
            username=user_data.username,
            email=user_data.email,
            full_name=user_data.full_name,
            employee_id=employee_id,  # ✅ AUTO-GENERATED
            role=role_enum,
            grade=grade_enum,
            department=user_data.department,
            phone=user_data.phone,
            can_claim_expenses=user_data.can_claim_expenses,
            
            # Temporary password (user will set real password via invitation link)
            hashed_password=hashed_temp_password,
            
            # Invitation fields
            invitation_token=invitation_token,
            invitation_sent_at=datetime.now() if user_data.send_invitation else None,
            invitation_expires_at=invitation_expires_at,
            is_password_set=False,
            account_status='pending_setup',
            
            # User is not active until they set password
            is_active=False,
            
            created_at=datetime.now()
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        logger.info(f"✅ User {new_user.username} created successfully with employee ID {employee_id}")
        
        # Step 9: Send invitation email
        invitation_sent = False
        invitation_link = None
        
        if user_data.send_invitation:
            # Generate invitation link
            invitation_link = f"http://localhost:3000/set-password?token={invitation_token}"
            
            invitation_sent = send_invitation_email(new_user, invitation_link)
        
        # Step 10: Create audit log
        from src.models.audit_log import AuditLog
        audit_log = AuditLog(
            user_id=current_user.id,
            action="create_user",
            entity_type="user",
            entity_id=new_user.id,
            description=f"Created new user {new_user.username} ({employee_id})",
            changes={
                "username": new_user.username,
                "email": new_user.email,
                "employee_id": employee_id,
                "role": new_user.role.value,
                "grade": new_user.grade.value
            }
        )
        db.add(audit_log)
        db.commit()
        
        # Step 11: Return response
        return {
            "success": True,
            "message": f"User '{new_user.username}' created successfully with Employee ID: {employee_id}",
            "user": {
                "id": new_user.id,
                "username": new_user.username,
                "email": new_user.email,
                "full_name": new_user.full_name,
                "employee_id": employee_id,  # ✅ AUTO-GENERATED
                "role": new_user.role.value if hasattr(new_user.role, 'value') else str(new_user.role),
                "grade": new_user.grade.value if hasattr(new_user.grade, 'value') else str(new_user.grade),
                "department": new_user.department,
                "can_claim_expenses": new_user.can_claim_expenses,
                "account_status": new_user.account_status,
                "is_active": new_user.is_active,
                "created_at": new_user.created_at.isoformat()
            },
            "invitation": {
                "sent": invitation_sent,
                "expires_at": invitation_expires_at.isoformat(),
                "link": invitation_link if invitation_link else None,
                "note": "User must set password within 7 days to activate account"
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating user: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create user: {str(e)}"
        )


# ============================================
# NEW ENDPOINT - GET NEXT EMPLOYEE ID (PREVIEW)
# ============================================

@router.get("/users/next-employee-id")
async def get_next_employee_id(
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_service.get_current_user)
):
    """
    Get the next employee ID that will be assigned (ADMIN ONLY)
    
    Useful for preview/confirmation before creating user
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    next_id = generate_next_employee_id(db)
    
    return {
        "next_employee_id": next_id,
        "format": "EMP###",
        "note": "This ID will be automatically assigned to the next user created"
    }


# ============================================
# NEW ENDPOINT - RESEND INVITATION
# ============================================

@router.post("/users/{user_id}/resend-invitation")
async def resend_invitation(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_service.get_current_user)
):
    """
    Resend invitation email to user (ADMIN ONLY)
    """
    try:
        # Check admin permission
        if current_user.role != UserRole.ADMIN:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        # Get user
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Check if already activated
        if user.is_password_set and user.is_active:
            raise HTTPException(
                status_code=400,
                detail="User has already set password and is active"
            )
        
        # Generate new invitation token
        invitation_token = generate_secure_token(32)
        invitation_expires_at = datetime.now() + timedelta(days=7)
        
        # Update user
        user.invitation_token = invitation_token
        user.invitation_sent_at = datetime.now()
        user.invitation_expires_at = invitation_expires_at
        
        db.commit()
        
        # Send email
        invitation_link = f"http://localhost:3000/set-password?token={invitation_token}"
        invitation_sent = send_invitation_email(user, invitation_link)
        
        return {
            "success": True,
            "message": f"Invitation resent to {user.email}",
            "invitation_sent": invitation_sent,
            "expires_at": invitation_expires_at.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resending invitation: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# EXISTING ENDPOINTS (NO CHANGES)
# ============================================

@router.get("/users", response_model=List[UserResponse])
async def get_all_users(
    is_active: Optional[bool] = None,
    role: Optional[str] = None,
    grade: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_service.require_role("admin"))
):
    """
    Get all users (Admin only)
    
    **Filters:**
    - is_active: Filter by active status
    - role: Filter by role (employee, manager, hr, finance, admin)
    - grade: Filter by grade (A, B, C, D)
    
    **Returns:**
    - List of all users matching filters
    """
    query = db.query(User)
    
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    
    if role:
        try:
            query = query.filter(User.role == UserRole(role.lower()))
        except ValueError:
            pass
    
    if grade:
        try:
            query = query.filter(User.grade == UserGrade(grade.upper()))
        except ValueError:
            pass
    
    users = query.offset(skip).limit(limit).all()
    
    logger.info(f"Admin {current_user.username} retrieved {len(users)} users")
    
    return users


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user_details(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_service.require_role("admin"))
):
    """
    Get specific user details (Admin only)
    
    **Parameters:**
    - user_id: ID of the user to retrieve
    
    **Returns:**
    - Complete user information
    """
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user


@router.put("/users/{user_id}/toggle-active")
async def toggle_user_active(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_service.require_role("admin"))
):
    """
    Activate/Deactivate user (Admin only)
    
    Toggles the is_active status of a user.
    Inactive users cannot login or perform any actions.
    
    **Parameters:**
    - user_id: ID of the user to toggle
    
    **Returns:**
    - success: Boolean
    - message: Status message
    - is_active: New active status
    """
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Prevent admin from deactivating themselves
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own account"
        )
    
    user.is_active = not user.is_active
    db.commit()
    
    action = "activated" if user.is_active else "deactivated"
    logger.info(f"Admin {current_user.username} {action} user {user.username}")
    
    # Create audit log
    from src.models.audit_log import AuditLog
    audit_log = AuditLog(
        user_id=current_user.id,
        action=f"toggle_user_active",
        entity_type="user",
        entity_id=user.id,
        description=f"{action.capitalize()} user {user.username} ({user.employee_id})",
        changes={"is_active": user.is_active}
    )
    db.add(audit_log)
    db.commit()
    
    return {
        "success": True,
        "message": f"User {action} successfully",
        "is_active": user.is_active
    }


@router.put("/users/{user_id}/toggle-claim-permission")
async def toggle_claim_permission(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_service.require_role("admin"))
):
    """
    Toggle expense claim permission (Admin only)
    
    Controls whether a user can submit expense claims.
    Useful for temporary restrictions or probation periods.
    
    **Parameters:**
    - user_id: ID of the user to toggle
    
    **Returns:**
    - success: Boolean
    - message: Status message
    - can_claim_expenses: New permission status
    """
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user.can_claim_expenses = not user.can_claim_expenses
    db.commit()
    
    action = "enabled" if user.can_claim_expenses else "disabled"
    logger.info(f"Admin {current_user.username} {action} claim permission for user {user.username}")
    
    # Create audit log
    from src.models.audit_log import AuditLog
    audit_log = AuditLog(
        user_id=current_user.id,
        action="toggle_claim_permission",
        entity_type="user",
        entity_id=user.id,
        description=f"{action.capitalize()} claim permission for user {user.username} ({user.employee_id})",
        changes={"can_claim_expenses": user.can_claim_expenses}
    )
    db.add(audit_log)
    db.commit()
    
    return {
        "success": True,
        "message": f"Claim permission {action} successfully",
        "can_claim_expenses": user.can_claim_expenses
    }


@router.put("/users/{user_id}/update-role")
async def update_user_role(
    user_id: int,
    new_role: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_service.require_role("admin"))
):
    """
    Update user role (Admin only)
    
    **Parameters:**
    - user_id: ID of the user
    - new_role: New role (employee, manager, hr, finance, admin)
    
    **Returns:**
    - success: Boolean
    - message: Status message
    - role: New role
    """
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Prevent admin from changing their own role
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change your own role"
        )
    
    try:
        old_role = user.role.value
        user.role = UserRole(new_role.lower())
        db.commit()
        
        logger.info(f"Admin {current_user.username} changed user {user.username} role from {old_role} to {new_role}")
        
        # Create audit log
        from src.models.audit_log import AuditLog
        audit_log = AuditLog(
            user_id=current_user.id,
            action="update_user_role",
            entity_type="user",
            entity_id=user.id,
            description=f"Changed role for user {user.username} from {old_role} to {new_role}",
            changes={"old_role": old_role, "new_role": new_role}
        )
        db.add(audit_log)
        db.commit()
        
        return {
            "success": True,
            "message": f"User role updated to {new_role}",
            "role": user.role.value
        }
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Must be one of: employee, manager, hr, finance, admin"
        )


@router.put("/users/{user_id}/update-grade")
async def update_user_grade(
    user_id: int,
    new_grade: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_service.require_role("admin"))
):
    """
    Update user grade (Admin only)
    
    Changes affect expense limits and permissions
    
    **Parameters:**
    - user_id: ID of the user
    - new_grade: New grade (A, B, C, D)
    
    **Returns:**
    - success: Boolean
    - message: Status message
    - grade: New grade
    - new_limits: Updated expense limits
    """
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    try:
        old_grade = user.grade.value
        user.grade = UserGrade(new_grade.upper())
        db.commit()
        
        logger.info(f"Admin {current_user.username} changed user {user.username} grade from {old_grade} to {new_grade}")
        
        # Create audit log
        from src.models.audit_log import AuditLog
        audit_log = AuditLog(
            user_id=current_user.id,
            action="update_user_grade",
            entity_type="user",
            entity_id=user.id,
            description=f"Changed grade for user {user.username} from {old_grade} to {new_grade}",
            changes={"old_grade": old_grade, "new_grade": new_grade}
        )
        db.add(audit_log)
        db.commit()
        
        return {
            "success": True,
            "message": f"User grade updated to {new_grade}",
            "grade": user.grade.value,
            "new_limits": user.get_expense_limits()
        }
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid grade. Must be one of: A, B, C, D"
        )


@router.get("/system-stats")
async def get_system_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_service.require_role("admin"))
):
    """
    Get system statistics (Admin only)
    
    **Returns:**
    - User statistics
    - Expense statistics
    - System health
    """
    # User statistics
    total_users = db.query(func.count(User.id)).scalar()
    active_users = db.query(func.count(User.id)).filter(User.is_active == True).scalar()
    users_by_role = db.query(
        User.role,
        func.count(User.id).label("count")
    ).group_by(User.role).all()
    
    users_by_grade = db.query(
        User.grade,
        func.count(User.id).label("count")
    ).group_by(User.grade).all()
    
    # Expense statistics
    total_expenses = db.query(func.count(Expense.id)).scalar()
    pending_approvals = db.query(func.count(Expense.id)).filter(
        Expense.status.in_(['manager_review', 'hr_review', 'finance_review'])
    ).scalar()
    
    approved_expenses = db.query(func.count(Expense.id)).filter(
        Expense.status == 'approved'
    ).scalar()
    
    rejected_expenses = db.query(func.count(Expense.id)).filter(
        Expense.status == 'rejected'
    ).scalar()
    
    # Total amounts
    total_claimed = db.query(func.sum(Expense.amount)).scalar() or 0
    total_approved_amount = db.query(func.sum(Expense.amount)).filter(
        Expense.status == 'approved'
    ).scalar() or 0
    
    return {
        "success": True,
        "users": {
            "total": total_users,
            "active": active_users,
            "inactive": total_users - active_users,
            "by_role": [
                {"role": role.value, "count": count}
                for role, count in users_by_role
            ],
            "by_grade": [
                {"grade": grade.value, "count": count}
                for grade, count in users_by_grade
            ]
        },
        "expenses": {
            "total": total_expenses,
            "pending": pending_approvals,
            "approved": approved_expenses,
            "rejected": rejected_expenses,
            "total_claimed_amount": float(total_claimed),
            "total_approved_amount": float(total_approved_amount)
        },
        "system_health": "healthy"
    }


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_service.require_role("admin"))
):
    """
    Delete user (Admin only)
    
    **Warning:** This permanently deletes the user and all associated data.
    Consider deactivating instead.
    
    **Parameters:**
    - user_id: ID of the user to delete
    
    **Returns:**
    - success: Boolean
    - message: Confirmation message
    """
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Prevent admin from deleting themselves
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )
    
    username = user.username
    employee_id = user.employee_id
    
    # Create audit log before deletion
    from src.models.audit_log import AuditLog
    audit_log = AuditLog(
        user_id=current_user.id,
        action="delete_user",
        entity_type="user",
        entity_id=user.id,
        description=f"Deleted user {username} ({employee_id})",
        changes={"deleted_user": username}
    )
    db.add(audit_log)
    
    # Delete user
    db.delete(user)
    db.commit()
    
    logger.warning(f"Admin {current_user.username} deleted user {username}")
    
    return {
        "success": True,
        "message": f"User {username} deleted successfully"
    }