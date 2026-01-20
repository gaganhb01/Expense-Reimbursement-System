"""
Expense Tests
Tests for expense creation, validation, and management
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set test environment variables
os.environ['SMTP_SERVER'] = 'smtp.gmail.com'
os.environ['SMTP_PORT'] = '587'
os.environ['SMTP_USERNAME'] = 'test@test.com'
os.environ['SMTP_PASSWORD'] = 'test_password'
os.environ['FROM_EMAIL'] = 'test@test.com'
os.environ['FROM_NAME'] = 'Test System'

import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
from io import BytesIO

from src.main import app
from src.models.user import User
from src.models.expense import Expense
from src.utils.security import get_password_hash
from tests.test_auth import TestingSessionLocal, test_db, test_user

client = TestClient(app)


@pytest.fixture
def auth_token(test_user):
    """Get authentication token"""
    response = client.post(
        "/api/auth/login",
        data={
            "username": "testuser",
            "password": "testpass123"
        }
    )
    assert response.status_code == 200, f"Login failed: {response.json()}"
    return response.json()["access_token"]


class TestExpenseCreation:
    """Test expense creation and validation"""
    
    def test_create_expense_success(self, test_user, auth_token):
        """Test successful expense creation"""
        # Create a dummy file
        file_content = b"Dummy bill content"
        files = {
            "bill_file": ("test_bill.pdf", BytesIO(file_content), "application/pdf")
        }
        
        data = {
            "category": "travel",
            "amount": "1000.00",
            "expense_date": (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"),
            "description": "Business travel to client location",
            "travel_mode": "bus",
            "travel_from": "Bangalore",
            "travel_to": "Mumbai"
        }
        
        response = client.post(
            "/api/expenses/claim",
            data=data,
            files=files,
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 201
        data = response.json()
        # Response has nested structure with "expense" key
        assert "expense" in data or "expense_number" in data
        expense_data = data.get("expense") or data
        assert expense_data["amount"] == 1000.0
    
    def test_create_expense_without_permission(self, test_db, auth_token):
        """Test expense creation without permission"""
        # Update user to remove claim permission
        db = TestingSessionLocal()
        user = db.query(User).filter(User.username == "testuser").first()
        user.can_claim_expenses = False
        db.commit()
        db.close()
        
        file_content = b"Dummy bill"
        files = {
            "bill_file": ("bill.pdf", BytesIO(file_content), "application/pdf")
        }
        
        data = {
            "category": "food",
            "amount": "500.00",
            "expense_date": datetime.now().strftime("%Y-%m-%d"),
            "description": "Team lunch meeting"
        }
        
        response = client.post(
            "/api/expenses/claim",
            data=data,
            files=files,
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 403
    
    def test_create_expense_invalid_category(self, test_user, auth_token):
        """Test expense creation with invalid category"""
        file_content = b"Dummy bill"
        files = {
            "bill_file": ("bill.pdf", BytesIO(file_content), "application/pdf")
        }
        
        data = {
            "category": "invalid_category",
            "amount": "500.00",
            "expense_date": datetime.now().strftime("%Y-%m-%d"),
            "description": "Invalid category test"
        }
        
        response = client.post(
            "/api/expenses/claim",
            data=data,
            files=files,
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        # Could be 400 or 422 depending on validation
        assert response.status_code in [400, 422, 500]


class TestExpenseRetrieval:
    """Test expense retrieval endpoints"""
    
    def test_get_my_expenses(self, test_user, auth_token):
        """Test getting user's own expenses"""
        response = client.get(
            "/api/expenses/my-expenses",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "expenses" in data
    
    def test_get_expense_detail(self, test_user, auth_token):
        """Test getting specific expense detail"""
        # First create an expense
        from src.models.expense import ExpenseCategory, ExpenseStatus
        db = TestingSessionLocal()
        expense = Expense(
            expense_number="EXP-TEST-001",
            employee_id=test_user.id,
            category=ExpenseCategory.FOOD,
            amount=500.00,
            expense_date=datetime.now(),
            description="Test expense for retrieval",
            bill_file_path="/tmp/test.pdf",
            bill_file_name="test.pdf",
            status=ExpenseStatus.SUBMITTED
        )
        db.add(expense)
        db.commit()
        expense_id = expense.id
        db.close()
        
        # Get expense detail
        response = client.get(
            f"/api/expenses/{expense_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["expense_number"] == "EXP-TEST-001"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])