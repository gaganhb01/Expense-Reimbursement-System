"""
Authentication Service
Handles user authentication and authorization
"""

from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import JWTError

from src.config.database import get_db
from src.models.user import User
from src.utils.security import verify_password, create_access_token, create_refresh_token, decode_token
from src.utils.logger import setup_logger

logger = setup_logger()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


class AuthService:
    """Authentication service"""
    
    def authenticate_user(self, db: Session, username: str, password: str) -> Optional[User]:
        """
        Authenticate user with username and password
        
        Args:
            db: Database session
            username: Username or email
            password: Password
            
        Returns:
            User: Authenticated user or None
        """
        user = db.query(User).filter(
            (User.username == username) | (User.email == username)
        ).first()
        
        if not user:
            return None
        
        if not verify_password(password, user.hashed_password):
            return None
        
        if not user.is_active:
            return None
        
        # Update last login
        user.last_login = datetime.utcnow()
        db.commit()
        
        logger.info(f"User authenticated: {user.username}")
        return user
    
    def create_tokens(self, user: User) -> dict:
        """
        Create access and refresh tokens for user
        
        Args:
            user: User object
            
        Returns:
            dict: Access and refresh tokens
        """
        access_token = create_access_token(
            data={
                "sub": str(user.id),
                "username": user.username,
                "role": user.role.value,
                "grade": user.grade.value
            }
        )
        
        refresh_token = create_refresh_token(
            data={"sub": str(user.id)}
        )
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }
    
    async def get_current_user(
        self,
        token: str = Depends(oauth2_scheme),
        db: Session = Depends(get_db)
    ) -> User:
        """
        Get current authenticated user from token
        
        Args:
            token: JWT token
            db: Database session
            
        Returns:
            User: Current user
            
        Raises:
            HTTPException: If authentication fails
        """
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
        try:
            payload = decode_token(token)
            if payload is None:
                raise credentials_exception
            
            user_id: str = payload.get("sub")
            if user_id is None:
                raise credentials_exception
                
        except JWTError:
            raise credentials_exception
        
        user = db.query(User).filter(User.id == int(user_id)).first()
        if user is None:
            raise credentials_exception
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive"
            )
        
        return user
    
    def require_permission(self, permission: str):
        """
        Decorator to require specific permission
        
        Args:
            permission: Required permission
        """
        async def permission_checker(current_user: User = Depends(self.get_current_user)):
            if not current_user.has_permission(permission):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied: {permission} required"
                )
            return current_user
        
        return permission_checker
    
    def require_role(self, *roles: str):
        """
        Decorator to require specific role(s)
        
        Args:
            roles: Required roles
        """
        async def role_checker(current_user: User = Depends(self.get_current_user)):
            if current_user.role.value not in roles:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Access denied. Required role(s): {', '.join(roles)}"
                )
            return current_user
        
        return role_checker


# Create singleton instance
auth_service = AuthService()