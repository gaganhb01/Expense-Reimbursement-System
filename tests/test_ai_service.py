"""
AI Service Tests
Tests for AI bill analysis functionality
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set test environment variables BEFORE importing anything else
os.environ['SMTP_SERVER'] = 'smtp.gmail.com'
os.environ['SMTP_PORT'] = '587'
os.environ['SMTP_USERNAME'] = 'test@test.com'
os.environ['SMTP_PASSWORD'] = 'test_password'
os.environ['FROM_EMAIL'] = 'test@test.com'
os.environ['FROM_NAME'] = 'Test System'

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from src.services.ai_service import AIService


class TestAIService:
    """Test AI service functionality"""
    
    @pytest.fixture
    def ai_service(self):
        """Create AI service instance"""
        return AIService()
    
    @pytest.mark.asyncio
    async def test_analyze_bill_structure(self, ai_service):
        """Test that analyze_bill returns expected structure"""
        # Mock the Gemini API response
        with patch.object(ai_service.model, 'generate_content') as mock_generate:
            mock_response = Mock()
            mock_response.text = '''
            {
                "is_authentic": true,
                "confidence_score": 92,
                "bill_number": "INV123456",
                "bill_date": "2026-01-05",
                "vendor_name": "Test Vendor",
                "extracted_amount": 1200.0,
                "has_gst": true,
                "gst_number": "29ABCDE1234F1Z5",
                "has_required_stamps": null,
                "travel_mode": "bus",
                "travel_class": null,
                "travel_route": "Bangalore - Mumbai",
                "payment_method": "card",
                "red_flags": [],
                "missing_elements": [],
                "recommendation": "APPROVE",
                "recommendation_reason": "Valid bill with all required details",
                "summary": "Valid bus ticket for business travel",
                "detailed_analysis": "Complete bill with GST and proper documentation"
            }
            '''
            mock_generate.return_value = mock_response
            
            result = await ai_service.analyze_bill(
                file_path="/tmp/test.pdf",
                category="travel",
                amount=1200.0,
                user_grade="A",
                description="Business travel"
            )
            
            # Verify structure
            assert "is_authentic" in result
            assert "confidence_score" in result
            assert "recommendation" in result
            assert "summary" in result
            assert result["recommendation"] in ["APPROVE", "REJECT", "REVIEW"]
    
    @pytest.mark.asyncio
    async def test_check_limits_within_limits(self, ai_service):
        """Test limit checking when within limits"""
        is_valid, error = ai_service._check_limits(
            category="travel",
            amount=1000.0,
            user_grade="A",
            travel_mode="bus"
        )
        
        assert is_valid is True
        assert error is None
    
    @pytest.mark.asyncio
    async def test_check_limits_exceeds_amount(self, ai_service):
        """Test limit checking when amount exceeds"""
        is_valid, error = ai_service._check_limits(
            category="travel",
            amount=2000.0,
            user_grade="A",
            travel_mode="bus"
        )
        
        assert is_valid is False
        assert "exceeds" in error.lower()
    
    @pytest.mark.asyncio
    async def test_check_limits_invalid_travel_mode(self, ai_service):
        """Test limit checking with invalid travel mode"""
        is_valid, error = ai_service._check_limits(
            category="travel",
            amount=1000.0,
            user_grade="A",
            travel_mode="flight_business"
        )
        
        assert is_valid is False
        assert "not allowed" in error.lower()
    
    @pytest.mark.asyncio
    async def test_generate_rejection_reason(self, ai_service):
        """Test AI rejection reason generation via fallback"""
        # Test that rejection reason is generated properly in fallback
        result = ai_service._get_fallback_analysis("Missing GST details")
        
        assert result["recommendation"] == "REVIEW"
        assert "manual review required" in result["recommendation_reason"].lower()
        assert "ai_error" in result
        assert result["ai_error"] == "Missing GST details"
    
    def test_fallback_analysis(self, ai_service):
        """Test fallback analysis when AI fails"""
        result = ai_service._get_fallback_analysis("Connection error")
        
        assert result["recommendation"] == "REVIEW"
        assert "manual review required" in result["summary"].lower()
        assert "ai_error" in result


class TestAIValidation:
    """Test AI validation helpers"""
    
    def test_parse_valid_json(self):
        """Test parsing valid JSON response"""
        ai_service = AIService()
        json_text = '''
        {
            "recommendation": "APPROVE",
            "confidence_score": 95
        }
        '''
        
        result = ai_service._parse_ai_response(json_text)
        assert result["recommendation"] == "APPROVE"
        assert result["confidence_score"] == 95
    
    def test_parse_json_with_markdown(self):
        """Test parsing JSON wrapped in markdown code blocks"""
        ai_service = AIService()
        json_text = '''
```json
        {
            "recommendation": "REJECT",
            "confidence_score": 85
        }
```
        '''
        
        result = ai_service._parse_ai_response(json_text)
        assert result["recommendation"] == "REJECT"
    
    def test_parse_invalid_json(self):
        """Test handling of invalid JSON"""
        ai_service = AIService()
        invalid_text = "This is not JSON at all"
        
        result = ai_service._parse_ai_response(invalid_text)
        assert result["recommendation"] == "REVIEW"
        assert "ai_error" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])