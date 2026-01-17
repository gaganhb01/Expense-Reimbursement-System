"""
Authentication Middleware
Validates JWT tokens and attaches user to request
"""

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Optional

from src.utils.security import decode_token
from src.utils.logger import setup_logger

logger = setup_logger()


class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware for JWT authentication"""
    
    async def dispatch(self, request: Request, call_next):
        """
        Process request and validate JWT token if present
        
        Args:
            request: FastAPI request
            call_next: Next middleware/route handler
            
        Returns:
            Response from next handler
        """
        # Skip authentication for public endpoints
        public_paths = [
            "/api/auth/login",
            "/api/auth/register",
            "/health",
            "/",
            "/api/docs",
            "/api/redoc",
            "/api/openapi.json"
        ]
        
        if request.url.path in public_paths:
            return await call_next(request)
        
        # Get token from Authorization header
        auth_header = request.headers.get("Authorization")
        
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            
            # Decode token
            payload = decode_token(token)
            
            if payload:
                # Attach user info to request state
                request.state.user_id = payload.get("sub")
                request.state.username = payload.get("username")
                request.state.role = payload.get("role")
            else:
                logger.warning(f"Invalid token for path: {request.url.path}")
        
        # Continue to next handler
        response = await call_next(request)
        return response