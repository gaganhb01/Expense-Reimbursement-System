# ============================================
# SELF-DECLARATION LIMITS CONFIGURATION
# ============================================

"""
File: Create new file: src/config/self_declaration_limits.py
"""

from typing import Dict

# Self-declaration limits by grade
SELF_DECLARATION_LIMITS = {
    "A": {
        "per_claim": 300,      # Max ₹300 per self-declared claim
        "monthly_total": 500,  # Max ₹500 total self-declared per month
        "max_count": 3         # Max 3 self-declarations per month
    },
    "B": {
        "per_claim": 250,
        "monthly_total": 400,
        "max_count": 3
    },
    "C": {
        "per_claim": 200,
        "monthly_total": 300,
        "max_count": 3
    },
    "D": {
        "per_claim": 150,
        "monthly_total": 200,
        "max_count": 3
    }
}

# Categories allowed for self-declaration
ALLOWED_SELF_DECLARATION_CATEGORIES = [
    "travel",      # Auto, taxi, rickshaw
    "food",        # Small food purchases
    "transport",   # Local transport, parking
    "miscellaneous"  # Tips, small purchases
]

# Categories NOT allowed without bill
FORBIDDEN_NO_BILL_CATEGORIES = [
    "accommodation",  # Hotel stays MUST have bills
]

# Reasons for no bill (for dropdown)
NO_BILL_REASONS = {
    "not_provided": "Vendor did not provide receipt",
    "lost": "Receipt was lost",
    "emergency": "Emergency expense, no time for bill",
    "auto_parking": "Auto/parking - receipt not issued",
    "small_vendor": "Small vendor/street purchase",
    "other": "Other (please specify in description)"
}


def get_self_declaration_limit(grade: str, limit_type: str = "per_claim") -> float:
    """
    Get self-declaration limit for a grade
    
    Args:
        grade: User grade (A, B, C, D)
        limit_type: "per_claim", "monthly_total", or "max_count"
    
    Returns:
        Limit value
    """
    grade_upper = grade.upper() if isinstance(grade, str) else str(grade).upper()
    
    if grade_upper not in SELF_DECLARATION_LIMITS:
        # Default to lowest grade if not found
        grade_upper = "D"
    
    return SELF_DECLARATION_LIMITS[grade_upper].get(limit_type, 0)


def is_category_allowed_for_self_declaration(category: str) -> bool:
    """Check if category allows self-declaration"""
    return category.lower() in ALLOWED_SELF_DECLARATION_CATEGORIES


def is_category_forbidden_for_self_declaration(category: str) -> bool:
    """Check if category is forbidden for self-declaration"""
    return category.lower() in FORBIDDEN_NO_BILL_CATEGORIES