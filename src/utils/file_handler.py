"""
File Handler Utilities
File upload, validation, and processing
"""

import os
import shutil
from pathlib import Path
from typing import Optional, Tuple
from fastapi import UploadFile, HTTPException, status
import mimetypes
from datetime import datetime
import uuid

from src.config.settings import settings
from src.utils.logger import setup_logger

logger = setup_logger()


def validate_file(file: UploadFile) -> Tuple[bool, Optional[str]]:
    """
    Validate uploaded file
    
    Args:
        file: Uploaded file
        
    Returns:
        Tuple[bool, Optional[str]]: (is_valid, error_message)
    """
    # Check file extension
    file_ext = file.filename.split(".")[-1].lower()
    if file_ext not in settings.allowed_extensions_list:
        return False, f"File type '{file_ext}' not allowed. Allowed types: {', '.join(settings.allowed_extensions_list)}"
    
    # Check file size (read first chunk to get size)
    file.file.seek(0, 2)  # Seek to end
    file_size = file.file.tell()
    file.file.seek(0)  # Seek back to start
    
    if file_size > settings.MAX_FILE_SIZE:
        max_size_mb = settings.MAX_FILE_SIZE / (1024 * 1024)
        return False, f"File size exceeds maximum allowed size of {max_size_mb}MB"
    
    if file_size == 0:
        return False, "File is empty"
    
    return True, None


async def save_upload_file(file: UploadFile, user_id: int) -> Tuple[str, str]:
    """
    Save uploaded file to disk
    
    Args:
        file: Uploaded file
        user_id: User ID who uploaded the file
        
    Returns:
        Tuple[str, str]: (file_path, file_name)
        
    Raises:
        HTTPException: If file validation or save fails
    """
    # Validate file
    is_valid, error_message = validate_file(file)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_message
        )
    
    # Create user directory
    user_dir = Path(settings.UPLOAD_DIRECTORY) / str(user_id)
    user_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate unique filename
    file_ext = file.filename.split(".")[-1].lower()
    unique_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.{file_ext}"
    file_path = user_dir / unique_filename
    
    try:
        # Save file
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        logger.info(f"File saved: {file_path} by user {user_id}")
        return str(file_path), file.filename
        
    except Exception as e:
        logger.error(f"Error saving file: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save file"
        )
    finally:
        file.file.close()


def delete_file(file_path: str) -> bool:
    """
    Delete a file from disk
    
    Args:
        file_path: Path to file
        
    Returns:
        bool: True if deleted successfully
    """
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"File deleted: {file_path}")
            return True
        return False
    except Exception as e:
        logger.error(f"Error deleting file {file_path}: {str(e)}")
        return False


def get_file_mime_type(file_path: str) -> str:
    """
    Get MIME type of a file
    
    Args:
        file_path: Path to file
        
    Returns:
        str: MIME type
    """
    try:
        # Try to guess MIME type from file extension
        mime_type, _ = mimetypes.guess_type(file_path)
        if mime_type:
            return mime_type
        
        # Fallback based on extension
        ext = Path(file_path).suffix.lower()
        mime_types = {
            '.pdf': 'application/pdf',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif'
        }
        return mime_types.get(ext, 'application/octet-stream')
    except Exception as e:
        logger.error(f"Error getting MIME type for {file_path}: {str(e)}")
        return "application/octet-stream"


def generate_expense_number() -> str:
    """
    Generate unique expense number
    
    Returns:
        str: Expense number in format EXP-YYYYMMDD-XXXXXX
    """
    timestamp = datetime.now().strftime("%Y%m%d")
    unique_id = uuid.uuid4().hex[:6].upper()
    return f"EXP-{timestamp}-{unique_id}"