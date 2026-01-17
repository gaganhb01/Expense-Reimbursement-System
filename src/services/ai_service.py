"""
Enhanced AI Service with OCR and PDF Support - UPDATED WITH DATE FORMAT FIX
Analyzes bills using Gemini AI + OCR for text extraction
"""

import google.generativeai as genai
from typing import Dict, Any, Optional, Tuple, List
from pathlib import Path
import json
from PIL import Image
import PyPDF2
from pdf2image import convert_from_path
import pytesseract
import cv2
import numpy as np
from io import BytesIO
from datetime import date, datetime, timedelta

from src.config.settings import settings
from src.utils.logger import setup_logger

logger = setup_logger()

# Configure Gemini AI
genai.configure(api_key=settings.GEMINI_API_KEY)


class AIService:
    """Enhanced AI Service with OCR and multi-bill support"""
    
    def __init__(self):
        self.model = genai.GenerativeModel(settings.GEMINI_MODEL)
    
    async def analyze_bill(
        self,
        file_path: str,
        category: str,
        amount: float,
        user_grade: str,
        description: str
    ) -> Dict[str, Any]:
        """
        Simple bill analysis (for backward compatibility with existing routes)
        
        Args:
            file_path: Path to bill file
            category: Expense category
            amount: Claimed amount
            user_grade: Employee grade
            description: Expense description
            
        Returns:
            dict: Analysis results
        """
        try:
            logger.info(f"Starting AI analysis for bill: {file_path}")
            
            # Get expense rules for grade
            expense_rules = settings.EXPENSE_RULES.get(user_grade, {})
            category_rules = expense_rules.get(category, {})
            
            # Load bill image
            bill_image = await self._load_bill_as_image(file_path)
            
            # Try OCR extraction
            try:
                ocr_text = await self._extract_text_ocr(file_path)
            except Exception as e:
                logger.warning(f"OCR failed, continuing without it: {e}")
                ocr_text = ""
            
            # Create analysis prompt
            prompt = self._create_simple_analysis_prompt(
                category, amount, user_grade, description, category_rules, ocr_text
            )
            
            # Generate AI analysis
            response = self.model.generate_content([prompt, bill_image])
            
            # Parse AI response
            analysis = self._parse_ai_response(response.text)
            
            # Add validation results
            analysis["is_within_limits"] = self._check_limits(
                category, amount, user_grade, analysis.get("travel_mode")
            )
            
            # Add OCR text if available
            if ocr_text:
                analysis["ocr_text"] = ocr_text[:500]  # First 500 chars
            
            logger.info(f"✅ AI analysis completed successfully")
            return analysis
            
        except Exception as e:
            logger.error(f"Error in AI analysis: {str(e)}", exc_info=True)
            return self._get_fallback_analysis(str(e))
    
    async def analyze_bill_with_ocr(
        self,
        file_path: str,
        category: str,
        amount: float,
        user_grade: str,
        description: str,
        expense_date: date,
        trip_start_date: Optional[date] = None,
        trip_end_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        Analyze bill using OCR + Gemini AI
        
        Args:
            file_path: Path to bill file
            category: Expense category
            amount: Claimed amount
            user_grade: Employee grade
            description: Expense description
            expense_date: Date of expense
            trip_start_date: Trip start date (optional)
            trip_end_date: Trip end date (optional)
            
        Returns:
            dict: Analysis results with OCR text
        """
        try:
            logger.info(f"Starting enhanced AI analysis for bill: {file_path}")
            
            # Step 1: Extract text using OCR
            ocr_text = await self._extract_text_ocr(file_path)
            logger.info(f"OCR extracted {len(ocr_text)} characters from bill")
            
            # Step 2: Load bill image/PDF
            bill_image = await self._load_bill_as_image(file_path)
            
            # Step 3: Validate date against trip dates
            date_validation = self._validate_bill_date(
                expense_date, trip_start_date, trip_end_date
            )
            
            # Step 4: Get expense rules for grade
            expense_rules = settings.EXPENSE_RULES.get(user_grade, {})
            category_rules = expense_rules.get(category, {})
            
            # Step 5: Create enhanced analysis prompt with OCR text
            prompt = self._create_enhanced_analysis_prompt(
                category, amount, user_grade, description,
                expense_date, ocr_text, date_validation, category_rules
            )
            
            # Step 6: Generate AI analysis
            response = self.model.generate_content([prompt, bill_image])
            
            # Step 7: Parse AI response
            analysis = self._parse_ai_response(response.text)
            
            # Step 8: Add OCR text and validations
            analysis["ocr_text"] = ocr_text
            analysis["date_validation"] = date_validation
            analysis["is_within_limits"] = self._check_limits(
                category, amount, user_grade, analysis.get("travel_mode")
            )
            
            logger.info(f"Enhanced AI analysis completed for bill: {file_path}")
            return analysis
            
        except Exception as e:
            logger.error(f"Error in enhanced AI analysis: {str(e)}", exc_info=True)
            return self._get_fallback_analysis(str(e))
    
    async def analyze_multiple_bills(
        self,
        bills_data: List[Dict[str, Any]],
        user_grade: str,
        trip_start_date: Optional[date] = None,
        trip_end_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        Analyze multiple bills and calculate per-day breakdown
        
        Args:
            bills_data: List of bill information
            user_grade: Employee grade
            trip_start_date: Trip start date
            trip_end_date: Trip end date
            
        Returns:
            dict: Combined analysis with per-day breakdown
        """
        try:
            logger.info(f"Analyzing {len(bills_data)} bills for multi-expense claim")
            
            # Analyze each bill individually
            bill_analyses = []
            for bill_data in bills_data:
                analysis = await self.analyze_bill_with_ocr(
                    file_path=bill_data['file_path'],
                    category=bill_data['category'],
                    amount=bill_data['amount'],
                    user_grade=user_grade,
                    description=bill_data['description'],
                    expense_date=bill_data['expense_date'],
                    trip_start_date=trip_start_date,
                    trip_end_date=trip_end_date
                )
                bill_analyses.append({
                    **bill_data,
                    'ai_analysis': analysis
                })
            
            # Calculate per-day breakdown
            per_day_breakdown = self._calculate_per_day_breakdown(
                bill_analyses, trip_start_date, trip_end_date
            )
            
            # Check daily limits
            daily_limit_violations = self._check_daily_limits(
                per_day_breakdown, user_grade
            )
            
            # Generate combined recommendation
            combined_recommendation = self._generate_combined_recommendation(
                bill_analyses, daily_limit_violations
            )
            
            return {
                "bills_analyzed": len(bills_data),
                "bill_analyses": bill_analyses,
                "per_day_breakdown": per_day_breakdown,
                "daily_limit_violations": daily_limit_violations,
                "has_daily_violations": len(daily_limit_violations) > 0,
                "combined_recommendation": combined_recommendation,
                "total_amount": sum(b['amount'] for b in bills_data),
                "average_per_day": self._calculate_average_per_day(
                    per_day_breakdown
                )
            }
            
        except Exception as e:
            logger.error(f"Error analyzing multiple bills: {str(e)}", exc_info=True)
            return {"error": str(e), "bills_analyzed": 0}
    
    def _create_simple_analysis_prompt(
        self,
        category: str,
        amount: float,
        user_grade: str,
        description: str,
        category_rules: dict,
        ocr_text: str
    ) -> str:
        """Create simple analysis prompt for basic bill analysis"""
        
        ocr_section = f"\n**OCR Extracted Text:**\n{ocr_text[:500]}\n" if ocr_text else ""
        
        prompt = f"""
You are an expert expense auditor analyzing a bill for an expense reimbursement claim.

**CRITICAL DATE FORMAT INSTRUCTION:**
- Indian bills use DD/MM/YY or DD/MM/YYYY format (DAY first, then MONTH)
- Example: 11/01/26 means 11th January 2026 (NOT January 11, 2026)
- Example: 25/12/25 means 25th December 2025 (NOT December 25, 2025)
- Today's date is: {datetime.now().strftime('%d/%m/%Y')} ({datetime.now().strftime('%Y-%m-%d')})
- When extracting bill_date, convert to YYYY-MM-DD format (e.g., 11/01/26 → 2026-01-11)
- Only flag as "future date" if the date is ACTUALLY in the future after correct DD/MM/YY parsing

**Expense Details:**
- Category: {category}
- Claimed Amount: ₹{amount}
- Description: {description}
- Employee Grade: {user_grade}

{ocr_section}

**Expense Rules for Grade {user_grade}:**
{json.dumps(category_rules, indent=2)}

**Your Task:**
Analyze the bill image and provide your assessment in JSON format.

Return ONLY valid JSON with this structure:
{{
  "is_authentic": true/false,
  "confidence_score": 0-100,
  "bill_number": "extracted bill number or null",
  "bill_date": "YYYY-MM-DD or null",
  "vendor_name": "vendor name or null",
  "extracted_amount": amount from bill or null,
  "has_gst": true/false/null,
  "gst_number": "GST number if visible",
  "has_required_stamps": true/false/null,
  "travel_mode": "bus/train/cab/etc or null",
  "travel_route": "from-to or null",
  "payment_method": "cash/card/upi or null",
  "red_flags": ["list any suspicious elements"],
  "missing_elements": ["list missing required elements"],
  "recommendation": "APPROVE/REJECT/REVIEW",
  "recommendation_reason": "detailed reason",
  "summary": "brief 1-2 line summary",
  "detailed_analysis": "comprehensive analysis"
}}

**Key Checks:**
1. Does amount on bill match claimed amount?
2. Is bill authentic (not tampered)?
3. Are all required details visible?
4. Is it within grade limits?

Return ONLY the JSON, no other text.
"""
        return prompt
    
    async def _extract_text_ocr(self, file_path: str) -> str:
        """Extract text from bill using OCR"""
        try:
            file_ext = Path(file_path).suffix.lower()
            
            if file_ext == '.pdf':
                # Convert PDF to images
                images = convert_from_path(file_path, dpi=300)
                text_parts = []
                for img in images:
                    # Preprocess image for better OCR
                    img_array = np.array(img)
                    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
                    # Apply thresholding for better text recognition
                    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                    # Extract text
                    text = pytesseract.image_to_string(thresh)
                    text_parts.append(text)
                return "\n".join(text_parts)
            else:
                # For images
                img = Image.open(file_path)
                img_array = np.array(img)
                # Convert to grayscale
                if len(img_array.shape) == 3:
                    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
                else:
                    gray = img_array
                # Apply preprocessing
                _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                # Extract text
                text = pytesseract.image_to_string(thresh)
                return text
        except Exception as e:
            logger.warning(f"OCR extraction failed: {str(e)}")
            return ""
    
    async def _load_bill_as_image(self, file_path: str) -> Image.Image:
        """Load bill file as image for Gemini AI"""
        file_ext = Path(file_path).suffix.lower()
        
        if file_ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
            return Image.open(file_path)
        elif file_ext == '.pdf':
            # Convert first page of PDF to image
            images = convert_from_path(file_path, first_page=1, last_page=1, dpi=200)
            return images[0] if images else None
        else:
            raise ValueError(f"Unsupported file type: {file_ext}")
    
    def _validate_bill_date(
        self,
        expense_date: date,
        trip_start_date: Optional[date],
        trip_end_date: Optional[date]
    ) -> Dict[str, Any]:
        """Validate bill date against trip dates"""
        if not trip_start_date or not trip_end_date:
            return {
                "is_valid": True,
                "message": "No trip dates to validate against"
            }
        
        if trip_start_date <= expense_date <= trip_end_date:
            return {
                "is_valid": True,
                "message": "Bill date falls within trip dates"
            }
        else:
            return {
                "is_valid": False,
                "message": f"Bill dated {expense_date} falls outside trip dates ({trip_start_date} to {trip_end_date})",
                "violation_type": "date_mismatch"
            }
    
    def _calculate_per_day_breakdown(
        self,
        bill_analyses: List[Dict],
        trip_start_date: Optional[date],
        trip_end_date: Optional[date]
    ) -> List[Dict[str, Any]]:
        """Calculate per-day expense breakdown"""
        if not trip_start_date or not trip_end_date:
            # No trip dates, group by expense date
            date_groups = {}
            for bill in bill_analyses:
                bill_date = bill['expense_date']
                if bill_date not in date_groups:
                    date_groups[bill_date] = []
                date_groups[bill_date].append(bill)
            
            breakdown = []
            for date_key, bills in date_groups.items():
                breakdown.append(self._calculate_day_summary(date_key, bills))
            return breakdown
        
        # Calculate for each day in trip
        breakdown = []
        current_date = trip_start_date
        while current_date <= trip_end_date:
            day_bills = [
                b for b in bill_analyses
                if b['expense_date'] == current_date
            ]
            breakdown.append(self._calculate_day_summary(current_date, day_bills))
            current_date += timedelta(days=1)
        
        return breakdown
    
    def _calculate_day_summary(self, date: date, bills: List[Dict]) -> Dict[str, Any]:
        """Calculate summary for a single day"""
        food_amount = sum(b['amount'] for b in bills if b['category'] == 'food')
        travel_amount = sum(b['amount'] for b in bills if b['category'] == 'travel')
        accommodation_amount = sum(b['amount'] for b in bills if b['category'] == 'accommodation')
        other_amount = sum(b['amount'] for b in bills if b['category'] not in ['food', 'travel', 'accommodation'])
        
        return {
            "date": date.isoformat(),
            "total_amount": sum(b['amount'] for b in bills),
            "food_amount": food_amount,
            "travel_amount": travel_amount,
            "accommodation_amount": accommodation_amount,
            "other_amount": other_amount,
            "bill_count": len(bills),
            "bills": bills
        }
    
    def _check_daily_limits(
        self,
        per_day_breakdown: List[Dict],
        user_grade: str
    ) -> List[Dict[str, Any]]:
        """Check if any day exceeds daily limits"""
        violations = []
        expense_rules = settings.EXPENSE_RULES.get(user_grade, {})
        
        # Get daily limits
        daily_food_limit = expense_rules.get('food', {}).get('max_per_day', 500)
        daily_travel_limit = expense_rules.get('travel', {}).get('max_per_day', 2000)
        
        for day in per_day_breakdown:
            day_violations = []
            
            if day['food_amount'] > daily_food_limit:
                day_violations.append({
                    "category": "food",
                    "amount": day['food_amount'],
                    "limit": daily_food_limit,
                    "excess": day['food_amount'] - daily_food_limit
                })
            
            if day['travel_amount'] > daily_travel_limit:
                day_violations.append({
                    "category": "travel",
                    "amount": day['travel_amount'],
                    "limit": daily_travel_limit,
                    "excess": day['travel_amount'] - daily_travel_limit
                })
            
            if day_violations:
                violations.append({
                    "date": day['date'],
                    "violations": day_violations,
                    "total_excess": sum(v['excess'] for v in day_violations)
                })
        
        return violations
    
    def _generate_combined_recommendation(
        self,
        bill_analyses: List[Dict],
        daily_violations: List[Dict]
    ) -> str:
        """Generate combined recommendation for all bills"""
        # Check individual bill recommendations
        reject_count = sum(
            1 for b in bill_analyses
            if b['ai_analysis'].get('recommendation') == 'REJECT'
        )
        review_count = sum(
            1 for b in bill_analyses
            if b['ai_analysis'].get('recommendation') == 'REVIEW'
        )
        
        # Check daily violations
        has_violations = len(daily_violations) > 0
        
        if reject_count > 0 or has_violations:
            return "REJECT"
        elif review_count > 0:
            return "REVIEW"
        else:
            return "APPROVE"
    
    def _calculate_average_per_day(self, per_day_breakdown: List[Dict]) -> float:
        """Calculate average spending per day"""
        if not per_day_breakdown:
            return 0.0
        total = sum(day['total_amount'] for day in per_day_breakdown)
        return round(total / len(per_day_breakdown), 2)
    
    def _create_enhanced_analysis_prompt(
        self,
        category: str,
        amount: float,
        user_grade: str,
        description: str,
        expense_date: date,
        ocr_text: str,
        date_validation: Dict,
        category_rules: dict
    ) -> str:
        """Create enhanced prompt with OCR text"""
        
        prompt = f"""
You are an expert expense auditor analyzing a bill with OCR-extracted text.

**CRITICAL DATE FORMAT INSTRUCTION:**
- Indian bills use DD/MM/YY or DD/MM/YYYY format (DAY first, then MONTH)
- Example: 11/01/26 means 11th January 2026 (NOT January 11, 2026)
- Example: 25/12/25 means 25th December 2025 (NOT December 25, 2025)
- Today's date is: {datetime.now().strftime('%d/%m/%Y')} ({datetime.now().strftime('%Y-%m-%d')})
- When extracting bill_date, convert to YYYY-MM-DD format (e.g., 11/01/26 → 2026-01-11)
- Only flag as "future date" if the date is ACTUALLY in the future after correct DD/MM/YY parsing

**Expense Details:**
- Category: {category}
- Claimed Amount: ₹{amount}
- Expense Date: {expense_date}
- Description: {description}
- Employee Grade: {user_grade}

**OCR Extracted Text from Bill:**
{ocr_text[:1000] if ocr_text else "No text extracted"}

**Date Validation:**
{json.dumps(date_validation, indent=2)}

**Expense Rules for Grade {user_grade}:**
{json.dumps(category_rules, indent=2)}

**Your Task:**
Analyze the bill thoroughly and provide your assessment in JSON format.

Return ONLY valid JSON with this structure:
{{
  "is_authentic": true/false,
  "confidence_score": 0-100,
  "bill_number": "extracted from OCR or image",
  "bill_date": "YYYY-MM-DD or null",
  "vendor_name": "extracted vendor name",
  "extracted_amount": amount from bill,
  "has_gst": true/false/null,
  "gst_number": "GST number if found",
  "has_required_stamps": true/false/null,
  "travel_mode": "bus/train/cab/etc or null",
  "travel_route": "from-to or null",
  "payment_method": "cash/card/upi or null",
  "red_flags": ["list any suspicious elements"],
  "missing_elements": ["list missing required elements"],
  "recommendation": "APPROVE/REJECT/REVIEW",
  "recommendation_reason": "detailed reason",
  "summary": "brief 1-2 line summary",
  "detailed_analysis": "comprehensive analysis including OCR findings"
}}

**Key Checks:**
1. Does extracted amount match claimed amount?
2. Is bill date valid and within trip dates?
3. Are all required details present?
4. Any signs of tampering or fraud?
5. Is it within grade limits?

Return ONLY the JSON, no other text.
"""
        return prompt
    
    def _check_limits(
        self,
        category: str,
        amount: float,
        user_grade: str,
        travel_mode: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """Check if expense is within grade limits"""
        expense_rules = settings.EXPENSE_RULES.get(user_grade, {})
        category_rules = expense_rules.get(category, {})
        
        if not category_rules:
            return True, None
        
        # Check amount limit
        max_amount = category_rules.get("max_amount")
        if max_amount and amount > max_amount:
            return False, f"Amount ₹{amount} exceeds grade {user_grade} limit of ₹{max_amount} for {category}"
        
        # Check travel mode
        if category == "travel" and travel_mode:
            allowed_modes = category_rules.get("allowed_modes", [])
            if allowed_modes and travel_mode not in allowed_modes:
                return False, f"Travel mode '{travel_mode}' not allowed for grade {user_grade}"
        
        return True, None
    
    def _parse_ai_response(self, response_text: str) -> Dict[str, Any]:
        """Parse AI response with improved error handling"""
        try:
            logger.info(f"Parsing AI response (length: {len(response_text)} chars)")
            logger.info(f"Raw response preview: {response_text[:200]}")
            
            # Clean up response
            cleaned = response_text.strip()
            
            # Remove markdown code blocks
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            elif cleaned.startswith("```"):
                cleaned = cleaned[3:]
            
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            
            cleaned = cleaned.strip()
            
            # Find JSON boundaries
            start_idx = cleaned.find('{')
            end_idx = cleaned.rfind('}') + 1
            
            if start_idx == -1 or end_idx <= start_idx:
                logger.error("No JSON found in response")
                logger.error(f"Response preview: {cleaned[:200]}")
                return self._get_fallback_analysis("No JSON in AI response")
            
            # Extract JSON
            json_str = cleaned[start_idx:end_idx]
            
            logger.info(f"Extracted JSON (first 200 chars): {json_str[:200]}")
            
            # Try to parse JSON
            try:
                parsed = json.loads(json_str)
                logger.info(f"✅ Successfully parsed JSON with keys: {list(parsed.keys())}")
                return parsed
            except json.JSONDecodeError as e:
                # Log the exact problem
                logger.error(f"❌ JSON decode error at position {e.pos}: {e.msg}")
                logger.error(f"JSON string causing error: {json_str}")
                logger.error(f"Problematic section: ...{json_str[max(0,e.pos-50):e.pos+50]}...")
                
                # Return fallback
                return self._get_fallback_analysis(f"Invalid JSON at position {e.pos}: {e.msg}")
                
        except Exception as e:
            logger.error(f"❌ Unexpected parse error: {str(e)}", exc_info=True)
            logger.error(f"Full response text: {response_text}")
            return self._get_fallback_analysis(str(e))
    
    def _get_fallback_analysis(self, error_message: str) -> Dict[str, Any]:
        """Fallback analysis when AI fails"""
        return {
            "is_authentic": None,
            "confidence_score": 0,
            "recommendation": "REVIEW",
            "recommendation_reason": f"Manual review required: {error_message}",
            "summary": "AI analysis could not be completed. Manual review required.",
            "red_flags": ["AI analysis failed"],
            "ai_error": error_message
        }


# Singleton instance
ai_service = AIService()