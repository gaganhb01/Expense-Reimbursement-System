"""
Authentication Routes
Login, password management, token management
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime, timedelta
import random

from src.config.database import get_db
from src.services.auth_service import auth_service
from src.schemas.auth import Token, UserLogin
from src.schemas.user import UserResponse, UserCreate
from src.models.user import User, UserRole, UserGrade
from src.utils.security import get_password_hash, verify_password  # ✅ FIXED: Import from security
from src.utils.logger import setup_logger

logger = setup_logger()
router = APIRouter()


# ============================================
# NEW SCHEMAS FOR PASSWORD MANAGEMENT
# ============================================

class SetPasswordRequest(BaseModel):
    """Request to set password from invitation"""
    token: str = Field(..., min_length=32)
    password: str = Field(..., min_length=8, max_length=100)
    confirm_password: str = Field(..., min_length=8, max_length=100)


class ForgotPasswordRequest(BaseModel):
    """Request to send OTP for password reset"""
    email: EmailStr


class VerifyOTPRequest(BaseModel):
    """Request to verify OTP and reset password"""
    email: EmailStr
    otp: str = Field(..., min_length=6, max_length=6)
    new_password: str = Field(..., min_length=8, max_length=100)
    confirm_password: str = Field(..., min_length=8, max_length=100)


# ============================================
# HELPER FUNCTIONS
# ============================================

def generate_otp() -> str:
    """Generate 6-digit OTP"""
    return ''.join([str(random.randint(0, 9)) for _ in range(6)])


def send_password_set_confirmation_email(user: User):
    """Send confirmation email after password is set"""
    try:
        from src.services.email_service import email_service
        
        email_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 10px;">
                <h2 style="color: #10b981;">✅ Password Set Successfully!</h2>
                
                <p>Hello <strong>{user.full_name}</strong>,</p>
                
                <p>Your password has been set successfully and your account is now <strong>active</strong>!</p>
                
                <div style="background-color: #f3f4f6; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h3 style="margin-top: 0; color: #1f2937;">You can now login with:</h3>
                    <p style="margin: 5px 0;"><strong>Username:</strong> {user.username}</p>
                    <p style="margin: 5px 0;"><strong>Email:</strong> {user.email}</p>
                </div>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="http://localhost:3000/login" 
                       style="background-color: #2563eb; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block; font-weight: bold;">
                        Login to Your Account
                    </a>
                </div>
                
                <p>Welcome to the Expense Reimbursement System!</p>
                
                <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">
                
                <p style="font-size: 12px; color: #6b7280;">
                    If you did not set this password, please contact your administrator immediately.
                </p>
            </div>
        </body>
        </html>
        """
        
        email_service.send_email(
            to_email=user.email,
            subject="Password Set Successfully - Expense Reimbursement System",
            html_body=email_body
        )
        
        logger.info(f"📧 Password confirmation email sent to {user.email}")
        
    except Exception as e:
        logger.error(f"Failed to send password confirmation email: {e}")


def send_otp_email(user: User, otp: str):
    """Send OTP email for password reset"""
    try:
        from src.services.email_service import email_service
        
        email_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 10px;">
                <h2 style="color: #ef4444;">🔐 Password Reset Request</h2>
                
                <p>Hello <strong>{user.full_name}</strong>,</p>
                
                <p>You requested to reset your password. Use the OTP below to reset your password:</p>
                
                <div style="text-align: center; margin: 30px 0; padding: 20px; background-color: #f3f4f6; border-radius: 10px;">
                    <h1 style="margin: 0; color: #2563eb; font-size: 48px; letter-spacing: 10px; font-family: 'Courier New', monospace;">
                        {otp}
                    </h1>
                    <p style="margin: 10px 0 0 0; color: #6b7280; font-size: 14px;">
                        This OTP is valid for <strong>15 minutes</strong>
                    </p>
                </div>
                
                <div style="background-color: #fef2f2; border-left: 4px solid #ef4444; padding: 15px; margin: 20px 0;">
                    <p style="margin: 0; color: #991b1b;">
                        <strong>⚠️ Security Alert:</strong><br>
                        If you did not request this password reset, please ignore this email and contact your administrator immediately.
                    </p>
                </div>
                
                <p>To reset your password, enter this OTP on the password reset page.</p>
                
                <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">
                
                <p style="font-size: 12px; color: #6b7280;">
                    This is an automated email. Please do not reply to this message.<br>
                    OTP expires in 15 minutes.
                </p>
            </div>
        </body>
        </html>
        """
        
        email_service.send_email(
            to_email=user.email,
            subject="Password Reset OTP - Expense Reimbursement System",
            html_body=email_body
        )
        
        logger.info(f"📧 OTP email sent to {user.email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send OTP email: {e}")
        return False


def send_password_reset_confirmation_email(user: User):
    """Send confirmation email after password is reset"""
    try:
        from src.services.email_service import email_service
        
        email_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 10px;">
                <h2 style="color: #10b981;">✅ Password Reset Successfully!</h2>
                
                <p>Hello <strong>{user.full_name}</strong>,</p>
                
                <p>Your password has been reset successfully.</p>
                
                <div style="background-color: #f3f4f6; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <p style="margin: 5px 0;"><strong>Time:</strong> {datetime.now().strftime('%d %B %Y at %I:%M %p')}</p>
                    <p style="margin: 5px 0;"><strong>Account:</strong> {user.email}</p>
                </div>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="http://localhost:3000/login" 
                       style="background-color: #2563eb; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block; font-weight: bold;">
                        Login with New Password
                    </a>
                </div>
                
                <div style="background-color: #fef2f2; border-left: 4px solid #ef4444; padding: 15px; margin: 20px 0;">
                    <p style="margin: 0; color: #991b1b;">
                        <strong>⚠️ Security Alert:</strong><br>
                        If you did not reset your password, contact your administrator immediately.
                    </p>
                </div>
                
                <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">
                
                <p style="font-size: 12px; color: #6b7280;">
                    This is an automated email. Please do not reply to this message.
                </p>
            </div>
        </body>
        </html>
        """
        
        email_service.send_email(
            to_email=user.email,
            subject="Password Reset Successful - Expense Reimbursement System",
            html_body=email_body
        )
        
        logger.info(f"📧 Password reset confirmation sent to {user.email}")
        
    except Exception as e:
        logger.error(f"Failed to send reset confirmation email: {e}")


# ============================================
# ENDPOINT - LOGIN
# ============================================

@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Login endpoint
    
    OAuth2 compatible token login
    """
    user = auth_service.authenticate_user(db, form_data.username, form_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # ✅ NEW: Check if user can login (account activated)
    if not user.can_login():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account not activated. Please set your password using the invitation link sent to your email."
        )
    
    tokens = auth_service.create_tokens(user)
    
    # Update last login
    user.last_login = datetime.now()
    db.commit()
    
    logger.info(f"User logged in: {user.username}")
    
    return tokens


# ============================================
# NEW ENDPOINT - SET PASSWORD FROM INVITATION
# ============================================

@router.post("/set-password")
async def set_password_from_invitation(
    request: SetPasswordRequest,
    db: Session = Depends(get_db)
):
    """
    Set password from invitation link (NEW USER)
    
    Flow:
    1. User receives invitation email
    2. Clicks link with token
    3. Sets new password
    4. Account activated
    """
    try:
        # Step 1: Validate passwords match
        if request.password != request.confirm_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Passwords do not match"
            )
        
        # Step 2: Find user by invitation token
        user = db.query(User).filter(User.invitation_token == request.token).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invalid invitation token"
            )
        
        # Step 3: Check if token has expired
        if not user.is_invitation_valid():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invitation link has expired. Please contact your administrator to resend."
            )
        
        # Step 4: Check if password already set
        if user.is_password_set:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password has already been set for this account. Use 'Forgot Password' to reset."
            )
        
        logger.info(f"User {user.username} setting password from invitation")
        
        # Step 5: Hash new password
        hashed_password = get_password_hash(request.password)  # ✅ FIXED
        
        # Step 6: Update user
        user.hashed_password = hashed_password
        user.is_password_set = True
        user.password_set_at = datetime.now()
        user.account_status = 'active'
        user.is_active = True
        user.invitation_token = None  # Clear token (one-time use)
        
        db.commit()
        db.refresh(user)
        
        logger.info(f"✅ Password set successfully for user {user.username}")
        
        # Step 7: Send confirmation email
        send_password_set_confirmation_email(user)
        
        # Step 8: Return success
        return {
            "success": True,
            "message": "Password set successfully! Your account is now active.",
            "user": {
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name,
                "account_status": user.account_status
            },
            "next_step": "You can now login with your username and password"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting password: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to set password: {str(e)}"
        )


# ============================================
# NEW ENDPOINT - FORGOT PASSWORD (SEND OTP)
# ============================================

@router.post("/forgot-password")
async def forgot_password(
    request: ForgotPasswordRequest,
    db: Session = Depends(get_db)
):
    """
    Send OTP for password reset (EXISTING USER)
    
    Flow:
    1. User enters email
    2. System sends 6-digit OTP to email
    3. OTP valid for 15 minutes
    """
    try:
        # Step 1: Find user by email
        user = db.query(User).filter(User.email == request.email).first()
        
        if not user:
            # Security: Don't reveal if email exists
            # Return success even if user not found
            return {
                "success": True,
                "message": "If this email is registered, you will receive an OTP shortly.",
                "note": "Please check your email for the OTP. It will be valid for 15 minutes."
            }
        
        # Step 2: Check if account is active
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Account is not active. Please contact administrator."
            )
        
        logger.info(f"Password reset requested for user {user.username}")
        
        # Step 3: Generate OTP
        otp = generate_otp()
        otp_expires_at = datetime.now() + timedelta(minutes=15)
        
        # Step 4: Store OTP (hashed for security)
        user.reset_token = get_password_hash(otp)  # ✅ FIXED
        user.reset_token_expires_at = otp_expires_at
        
        db.commit()
        
        # Step 5: Send OTP email
        email_sent = send_otp_email(user, otp)
        
        if not email_sent:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send OTP email. Please try again."
            )
        
        logger.info(f"✅ OTP sent to {user.email}")
        
        # Step 6: Return success
        return {
            "success": True,
            "message": "OTP sent to your email successfully",
            "email": user.email,
            "expires_in": "15 minutes",
            "note": "Please check your email for the 6-digit OTP"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in forgot password: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process password reset request"
        )


# ============================================
# NEW ENDPOINT - VERIFY OTP & RESET PASSWORD
# ============================================

@router.post("/reset-password")
async def reset_password_with_otp(
    request: VerifyOTPRequest,
    db: Session = Depends(get_db)
):
    """
    Verify OTP and reset password
    
    Flow:
    1. User enters email, OTP, and new password
    2. System verifies OTP
    3. Password updated
    """
    try:
        # Step 1: Validate passwords match
        if request.new_password != request.confirm_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Passwords do not match"
            )
        
        # Step 2: Find user by email
        user = db.query(User).filter(User.email == request.email).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Step 3: Check if reset token exists
        if not user.reset_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No password reset request found. Please request OTP first."
            )
        
        # Step 4: Check if OTP has expired
        if not user.is_reset_token_valid():
            user.reset_token = None
            user.reset_token_expires_at = None
            db.commit()
            
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OTP has expired. Please request a new OTP."
            )
        
        # Step 5: Verify OTP
        if not verify_password(request.otp, user.reset_token):  # ✅ FIXED
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid OTP. Please try again."
            )
        
        logger.info(f"User {user.username} resetting password with OTP")
        
        # Step 6: Hash new password
        hashed_password = get_password_hash(request.new_password)  # ✅ FIXED
        
        # Step 7: Update user
        user.hashed_password = hashed_password
        user.last_password_reset = datetime.now()
        user.reset_token = None  # Clear OTP (one-time use)
        user.reset_token_expires_at = None
        
        db.commit()
        db.refresh(user)
        
        logger.info(f"✅ Password reset successfully for user {user.username}")
        
        # Step 8: Send confirmation email
        send_password_reset_confirmation_email(user)
        
        # Step 9: Return success
        return {
            "success": True,
            "message": "Password reset successfully!",
            "user": {
                "username": user.username,
                "email": user.email
            },
            "next_step": "You can now login with your new password"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resetting password: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset password: {str(e)}"
        )



@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(auth_service.get_current_user)
):
    """Get current user information"""
    return current_user


@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_token: str,
    db: Session = Depends(get_db)
):
    """
    Refresh access token using refresh token
    """
    from src.utils.security import decode_token
    
    payload = decode_token(refresh_token)
    
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == int(user_id)).first()
    
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    tokens = auth_service.create_tokens(user)
    return tokens