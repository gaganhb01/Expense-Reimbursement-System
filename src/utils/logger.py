"""
Logging Configuration
"""

from loguru import logger
import sys
from pathlib import Path

from src.config.settings import settings


def setup_logger():
    """
    Setup application logger with file and console output
    
    Returns:
        logger: Configured logger instance
    """
    # Remove default logger
    logger.remove()
    
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Console logging
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=settings.LOG_LEVEL,
        colorize=True
    )
    
    # File logging - all logs
    logger.add(
        settings.LOG_FILE,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level=settings.LOG_LEVEL,
        rotation="10 MB",
        retention="30 days",
        compression="zip"
    )
    
    # File logging - errors only
    logger.add(
        "logs/error.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="ERROR",
        rotation="10 MB",
        retention="90 days",
        compression="zip"
    )
    
    # File logging - audit trail
    logger.add(
        "logs/audit.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {message}",
        filter=lambda record: "AUDIT" in record["extra"],
        rotation="10 MB",
        retention="365 days",
        compression="zip"
    )
    
    return logger


def log_audit(user_id: int, action: str, details: str):
    """
    Log audit trail entry
    
    Args:
        user_id: User ID who performed the action
        action: Action performed
        details: Action details
    """
    logger.bind(AUDIT=True).info(f"USER_ID={user_id} | ACTION={action} | DETAILS={details}")