"""
Logging Middleware
Logs all HTTP requests and responses
"""

import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from src.utils.logger import setup_logger

logger = setup_logger()


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all requests and responses"""
    
    async def dispatch(self, request: Request, call_next):
        """Process request and log details"""
        start_time = time.time()
        
        # Log request
        logger.info(
            f"Request: {request.method} {request.url.path} | "
            f"Client: {request.client.host if request.client else 'unknown'}"
        )
        
        # Process request
        try:
            response = await call_next(request)
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Log response
            logger.info(
                f"Response: {request.method} {request.url.path} | "
                f"Status: {response.status_code} | "
                f"Duration: {duration:.3f}s"
            )
            
            return response
            
        except Exception:
            # ✅ FIXED: Use logger.exception() instead of manually formatting error
            # This automatically handles exceptions with curly braces in the message
            duration = time.time() - start_time
            logger.exception(
                f"Error: {request.method} {request.url.path} | "
                f"Duration: {duration:.3f}s"
            )
            raise