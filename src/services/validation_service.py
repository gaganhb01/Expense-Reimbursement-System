"""
Validation Service
Validates expense claims against grade-based rules
"""

from typing import Optional, Dict, Any, Tuple

from src.config.settings import settings
from src.utils.logger import setup_logger

logger = setup_logger()


class ValidationService:
    """Service for validating expense claims"""
    
    def validate_expense_limits(
        self,
        category: str,
        amount: float,
        user_grade: str,
        travel_mode: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate expense against grade-based limits
        
        Args:
            category: Expense category (travel, food, medical, etc.)
            amount: Claimed amount
            user_grade: Employee grade (A, B, C, D)
            travel_mode: Travel mode if category is travel
            
        Returns:
            Tuple of (is_valid, error_message)
            - is_valid: True if expense is within limits
            - error_message: Description of violation if not valid
        """
        # Get rules for user's grade
        rules = settings.EXPENSE_RULES.get(user_grade, {})
        category_rules = rules.get(category, {})
        
        if not category_rules:
            logger.warning(f"No rules found for grade {user_grade}, category {category}")
            return True, None
        
        # Validate amount limit
        max_amount = category_rules.get("max_amount")
        if max_amount and amount > max_amount:
            error_msg = (
                f"Amount ₹{amount:,.2f} exceeds grade {user_grade} limit of "
                f"₹{max_amount:,.2f} for {category} expenses"
            )
            logger.info(f"Validation failed: {error_msg}")
            return False, error_msg
        
        # Validate travel mode (if applicable)
        if category == "travel" and travel_mode:
            allowed_modes = category_rules.get("allowed_modes", [])
            if allowed_modes and travel_mode not in allowed_modes:
                error_msg = (
                    f"Travel mode '{travel_mode}' is not allowed for grade {user_grade}. "
                    f"Allowed modes: {', '.join(allowed_modes)}"
                )
                logger.info(f"Validation failed: {error_msg}")
                return False, error_msg
        
        logger.info(f"Validation passed for grade {user_grade}, category {category}, amount ₹{amount}")
        return True, None
    
    def get_expense_rules(self, user_grade: str) -> Dict[str, Any]:
        """
        Get all expense rules for a specific grade
        
        Args:
            user_grade: Employee grade (A, B, C, D)
            
        Returns:
            Dictionary of rules for all categories
        """
        rules = settings.EXPENSE_RULES.get(user_grade, {})
        if not rules:
            logger.warning(f"No rules found for grade {user_grade}")
        return rules
    
    def get_category_limit(self, user_grade: str, category: str) -> Optional[float]:
        """
        Get maximum amount limit for a specific category and grade
        
        Args:
            user_grade: Employee grade
            category: Expense category
            
        Returns:
            Maximum allowed amount or None if no limit
        """
        rules = self.get_expense_rules(user_grade)
        category_rules = rules.get(category, {})
        return category_rules.get("max_amount")
    
    def get_allowed_travel_modes(self, user_grade: str) -> list:
        """
        Get allowed travel modes for a specific grade
        
        Args:
            user_grade: Employee grade
            
        Returns:
            List of allowed travel modes
        """
        rules = self.get_expense_rules(user_grade)
        travel_rules = rules.get("travel", {})
        return travel_rules.get("allowed_modes", [])
    
    def validate_multiple_expenses(
        self,
        expenses: list,
        user_grade: str
    ) -> Dict[str, Any]:
        """
        Validate multiple expenses at once
        
        Args:
            expenses: List of expense dictionaries with category, amount, travel_mode
            user_grade: Employee grade
            
        Returns:
            Dictionary with validation results for each expense
        """
        results = {
            "all_valid": True,
            "expenses": [],
            "total_violations": 0
        }
        
        for idx, expense in enumerate(expenses):
            is_valid, error = self.validate_expense_limits(
                category=expense.get("category"),
                amount=expense.get("amount"),
                user_grade=user_grade,
                travel_mode=expense.get("travel_mode")
            )
            
            results["expenses"].append({
                "index": idx,
                "valid": is_valid,
                "error": error
            })
            
            if not is_valid:
                results["all_valid"] = False
                results["total_violations"] += 1
        
        return results


# Create singleton instance
validation_service = ValidationService()