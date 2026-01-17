"""
Expense Tests
Tests for expense creation, validation, and management
"""

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
        expense_data = response.json()
        assert expense_data["category"] == "travel"
        assert expense_data["amount"] == 1000.00
    
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
        
        assert response.status_code == 400


class TestExpenseRetrieval:
    """Test expense retrieval endpoints"""
    
    def test_get_my_expenses(self, test_user, auth_token):
        """Test getting user's own expenses"""
        response = client.get(
            "/api/expenses/my-expenses",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_get_expense_detail(self, test_user, auth_token):
        """Test getting specific expense detail"""
        # First create an expense
        db = TestingSessionLocal()
        expense = Expense(
            expense_number="EXP-TEST-001",
            employee_id=test_user.id,
            category="food",
            amount=500.00,
            expense_date=datetime.now(),
            description="Test expense for retrieval",
            bill_file_path="/tmp/test.pdf",
            bill_file_name="test.pdf",
            status="submitted"
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