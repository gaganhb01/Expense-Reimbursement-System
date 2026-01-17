"""
Duplicate Bill Detection Utility
Detects duplicate bill submissions to prevent fraud
"""

import hashlib
from typing import Optional, Dict, List, Tuple
from sqlalchemy.orm import Session
from datetime import datetime

from src.models.expense import Expense
from src.utils.logger import setup_logger

logger = setup_logger()


class DuplicateDetector:
    """Utility class for detecting duplicate bill submissions"""
    
    @staticmethod
    def calculate_file_hash(file_path: str) -> str:
        """
        Calculate SHA-256 hash of a file
        
        Args:
            file_path: Path to the file
            
        Returns:
            SHA-256 hash as hex string
        """
        sha256_hash = hashlib.sha256()
        
        try:
            with open(file_path, "rb") as f:
                # Read file in chunks to handle large files
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            
            file_hash = sha256_hash.hexdigest()
            logger.info(f"Calculated file hash: {file_hash[:16]}...")
            return file_hash
            
        except Exception as e:
            logger.error(f"Error calculating file hash: {e}")
            return None
    
    
    @staticmethod
    def check_duplicate_by_hash(
        db: Session,
        file_hash: str,
        employee_id: int,
        current_expense_id: Optional[int] = None
    ) -> Tuple[bool, Optional[Expense]]:
        """
        Check if file hash already exists in database
        
        Args:
            db: Database session
            file_hash: SHA-256 hash of the file
            employee_id: Current employee ID
            current_expense_id: ID of current expense (to exclude from check)
            
        Returns:
            Tuple of (is_duplicate, original_expense)
        """
        try:
            query = db.query(Expense).filter(
                Expense.file_hash == file_hash,
                Expense.employee_id == employee_id,
                Expense.status.in_(["submitted", "approved"])  # Only check submitted/approved
            )
            
            # Exclude current expense if updating
            if current_expense_id:
                query = query.filter(Expense.id != current_expense_id)
            
            original = query.first()
            
            if original:
                logger.warning(
                    f"⚠️ DUPLICATE FILE DETECTED: Hash matches expense {original.expense_number} "
                    f"(Status: {original.status})"
                )
                return True, original
            
            return False, None
            
        except Exception as e:
            logger.error(f"Error checking duplicate by hash: {e}")
            return False, None
    
    
    @staticmethod
    def check_duplicate_by_bill_details(
        db: Session,
        bill_number: Optional[str],
        vendor_name: Optional[str],
        bill_date: Optional[str],
        employee_id: int,
        current_expense_id: Optional[int] = None
    ) -> Tuple[bool, Optional[Expense]]:
        """
        Check if bill details (number + vendor + date) already exist
        
        Args:
            db: Database session
            bill_number: Bill/Invoice number from OCR
            vendor_name: Vendor name from OCR
            bill_date: Bill date from OCR
            employee_id: Current employee ID
            current_expense_id: ID of current expense (to exclude from check)
            
        Returns:
            Tuple of (is_duplicate, original_expense)
        """
        # Skip check if any required field is missing
        if not bill_number or not vendor_name:
            logger.info("Skipping bill details check - missing bill_number or vendor_name")
            return False, None
        
        try:
            from sqlalchemy import func  # ✅ FIX: Import func from sqlalchemy
            
            query = db.query(Expense).filter(
                Expense.bill_number == bill_number,
                Expense.vendor_name == vendor_name,
                Expense.employee_id == employee_id,
                Expense.status.in_(["submitted", "approved"])
            )
            
            # Add date filter if available
            if bill_date:
                query = query.filter(
                    func.date(Expense.expense_date) == func.date(bill_date)  # ✅ FIX: Use func instead of db.func
                )
            
            # Exclude current expense if updating
            if current_expense_id:
                query = query.filter(Expense.id != current_expense_id)
            
            original = query.first()
            
            if original:
                logger.warning(
                    f"⚠️ DUPLICATE BILL DETAILS DETECTED: "
                    f"Bill #{bill_number} from {vendor_name} matches expense {original.expense_number} "
                    f"(Status: {original.status})"
                )
                return True, original
            
            return False, None
            
        except Exception as e:
            logger.error(f"Error checking duplicate by bill details: {e}")
            return False, None
    
    
    @staticmethod
    def perform_full_check(
        db: Session,
        file_path: str,
        bill_number: Optional[str],
        vendor_name: Optional[str],
        bill_date: Optional[str],
        employee_id: int,
        current_expense_id: Optional[int] = None
    ) -> Dict:
        """
        Perform comprehensive duplicate check
        
        Args:
            db: Database session
            file_path: Path to uploaded file
            bill_number: Bill number from OCR
            vendor_name: Vendor name from OCR
            bill_date: Bill date from OCR
            employee_id: Current employee ID
            current_expense_id: ID of current expense (to exclude from check)
            
        Returns:
            Dict with check results:
            {
                "is_duplicate": bool,
                "duplicate_type": str,  # "file_hash" or "bill_details" or None
                "original_expense": Expense or None,
                "file_hash": str,
                "should_block": bool,  # True = block submission, False = flag for review
                "message": str
            }
        """
        result = {
            "is_duplicate": False,
            "duplicate_type": None,
            "original_expense": None,
            "file_hash": None,
            "should_block": False,
            "message": None
        }
        
        # Step 1: Calculate file hash
        file_hash = DuplicateDetector.calculate_file_hash(file_path)
        result["file_hash"] = file_hash
        
        if not file_hash:
            logger.error("Failed to calculate file hash")
            return result
        
        # Step 2: Check file hash (exact duplicate)
        is_hash_duplicate, hash_original = DuplicateDetector.check_duplicate_by_hash(
            db, file_hash, employee_id, current_expense_id
        )
        
        if is_hash_duplicate:
            result["is_duplicate"] = True
            result["duplicate_type"] = "file_hash"
            result["original_expense"] = hash_original
            result["should_block"] = True  # Block exact file duplicates
            result["message"] = (
                f"⚠️ DUPLICATE FILE DETECTED!\n\n"
                f"This exact file was already submitted as:\n"
                f"• Expense: {hash_original.expense_number}\n"
                f"• Amount: ₹{hash_original.amount:,.2f}\n"
                f"• Date: {hash_original.expense_date.strftime('%d %B %Y')}\n"
                f"• Status: {hash_original.status.upper()}\n\n"
                f"You cannot submit the same bill twice."
            )
            logger.error(f"🚫 BLOCKING SUBMISSION: Exact duplicate of {hash_original.expense_number}")
            return result
        
        # Step 3: Check bill details (bill number + vendor)
        is_details_duplicate, details_original = DuplicateDetector.check_duplicate_by_bill_details(
            db, bill_number, vendor_name, bill_date, employee_id, current_expense_id
        )
        
        if is_details_duplicate:
            result["is_duplicate"] = True
            result["duplicate_type"] = "bill_details"
            result["original_expense"] = details_original
            result["should_block"] = False  # Flag for review instead of blocking
            result["message"] = (
                f"⚠️ DUPLICATE BILL SUSPECTED!\n\n"
                f"A bill with the same details was already submitted:\n"
                f"• Expense: {details_original.expense_number}\n"
                f"• Bill #: {bill_number}\n"
                f"• Vendor: {vendor_name}\n"
                f"• Amount: ₹{details_original.amount:,.2f}\n"
                f"• Status: {details_original.status.upper()}\n\n"
                f"This claim will be flagged for manager review."
            )
            logger.warning(f"⚠️ FLAGGING FOR REVIEW: Bill details match {details_original.expense_number}")
            return result
        
        # Step 4: All checks passed
        logger.info("✅ No duplicates detected - claim is unique")
        return result