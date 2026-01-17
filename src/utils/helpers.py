"""
Helper Utilities
Common helper functions
"""

from typing import Dict, Any, Optional
from datetime import datetime
import json


def format_currency(amount: float, currency: str = "INR") -> str:
    """
    Format amount as currency
    
    Args:
        amount: Amount to format
        currency: Currency code
        
    Returns:
        str: Formatted currency string
    """
    if currency == "INR":
        return f"₹{amount:,.2f}"
    return f"{currency} {amount:,.2f}"


def format_date(date: datetime, format_str: str = "%Y-%m-%d") -> str:
    """
    Format datetime as string
    
    Args:
        date: Datetime object
        format_str: Format string
        
    Returns:
        str: Formatted date string
    """
    return date.strftime(format_str)


def format_datetime(dt: datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    Format datetime with time
    
    Args:
        dt: Datetime object
        format_str: Format string
        
    Returns:
        str: Formatted datetime string
    """
    return dt.strftime(format_str)


def safe_json_loads(json_str: str, default: Any = None) -> Any:
    """
    Safely load JSON string
    
    Args:
        json_str: JSON string
        default: Default value if parsing fails
        
    Returns:
        Parsed JSON or default value
    """
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return default


def generate_summary(data: Dict[str, Any]) -> str:
    """
    Generate a summary string from dict
    
    Args:
        data: Dictionary of data
        
    Returns:
        str: Summary string
    """
    items = [f"{k}: {v}" for k, v in data.items() if v is not None]
    return " | ".join(items)


def truncate_string(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate string to max length
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated
        
    Returns:
        str: Truncated string
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def get_client_ip(request) -> str:
    """
    Get client IP address from request
    
    Args:
        request: FastAPI request object
        
    Returns:
        str: Client IP address
    """
    if request.client:
        return request.client.host
    
    # Check for forwarded IP
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    
    return "unknown"