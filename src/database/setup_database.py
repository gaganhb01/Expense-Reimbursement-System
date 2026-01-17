"""
Database Setup Script
Creates all tables and initial data with comprehensive examples
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
import hashlib
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import create_engine
from src.config.settings import settings
from src.config.database import Base
from src.models.user import User
from src.models.expense import Expense, ExpenseStatus, ExpenseCategory, TravelMode
from src.models.approval import Approval, ApprovalLevel, ApprovalStatus
from src.models.notification import Notification
from src.models.audit_log import AuditLog
from src.utils.security import get_password_hash
from src.config.database import SessionLocal


def create_tables():
    """Create all database tables"""
    print("Creating database tables...")
    engine = create_engine(settings.DATABASE_URL)
    Base.metadata.create_all(bind=engine)
    print("✓ Database tables created successfully")


def create_initial_users():
    """Create initial users with complete profile data"""
    print("\nCreating initial users...")
    db = SessionLocal()
    
    try:
        # Check if users already exist
        if db.query(User).first():
            print("✓ Users already exist, skipping...")
            return
        
        now = datetime.utcnow()
        
        # Create Admin user
        admin = User(
            email="admin@expensesystem.com",
            username="admin",
            full_name="System Administrator",
            employee_id="EMP001",
            hashed_password=get_password_hash("admin123"),
            role="admin",
            grade="D",
            department="IT",
            phone="+91-9876543210",
            is_active=True,
            can_claim_expenses=True,
            invitation_token=None,
            password_set_at=now,
            is_password_set=True,
            account_status="active",
            created_at=now,
            last_login=now
        )
        db.add(admin)
        
        # Create Manager user
        manager = User(
            email="manager@expensesystem.com",
            username="manager",
            full_name="Department Manager",
            employee_id="EMP002",
            hashed_password=get_password_hash("manager123"),
            role="manager",
            grade="C",
            department="Operations",
            phone="+91-9876543211",
            is_active=True,
            can_claim_expenses=True,
            password_set_at=now,
            is_password_set=True,
            account_status="active",
            created_at=now,
            last_login=now - timedelta(days=1)
        )
        db.add(manager)
        
        # Create HR user
        hr = User(
            email="hr@expensesystem.com",
            username="hr",
            full_name="HR Manager",
            employee_id="EMP003",
            hashed_password=get_password_hash("hr123"),
            role="hr",
            grade="C",
            department="Human Resources",
            phone="+91-9876543212",
            is_active=True,
            can_claim_expenses=True,
            password_set_at=now,
            is_password_set=True,
            account_status="active",
            created_at=now,
            last_login=now - timedelta(days=2)
        )
        db.add(hr)
        
        # Create Finance user
        finance = User(
            email="finance@expensesystem.com",
            username="finance",
            full_name="Finance Manager",
            employee_id="EMP004",
            hashed_password=get_password_hash("finance123"),
            role="finance",
            grade="C",
            department="Finance",
            phone="+91-9876543213",
            is_active=True,
            can_claim_expenses=True,
            password_set_at=now,
            is_password_set=True,
            account_status="active",
            created_at=now,
            last_login=now - timedelta(days=3)
        )
        db.add(finance)
        
        # Create Employee Grade A
        employee_a = User(
            email="employeea@expensesystem.com",
            username="employee_a",
            full_name="Rajesh Sharma",
            employee_id="EMP005",
            hashed_password=get_password_hash("employee123"),
            role="employee",
            grade="A",
            department="Operations",
            phone="+91-9876543214",
            is_active=True,
            can_claim_expenses=True,
            password_set_at=now,
            is_password_set=True,
            account_status="active",
            created_at=now,
            last_login=now - timedelta(hours=5)
        )
        db.add(employee_a)
        
        # Create Employee Grade B
        employee_b = User(
            email="employeeb@expensesystem.com",
            username="employee_b",
            full_name="Priya Gupta",
            employee_id="EMP006",
            hashed_password=get_password_hash("employee123"),
            role="employee",
            grade="B",
            department="Sales",
            phone="+91-9876543215",
            is_active=True,
            can_claim_expenses=True,
            password_set_at=now,
            is_password_set=True,
            account_status="active",
            created_at=now,
            last_login=now - timedelta(hours=12)
        )
        db.add(employee_b)
        
        # Create Employee without claim permission
        employee_no_perm = User(
            email="employeenoperm@expensesystem.com",
            username="employee_no_perm",
            full_name="Rahul Mehta",
            employee_id="EMP007",
            hashed_password=get_password_hash("employee123"),
            role="employee",
            grade="A",
            department="Operations",
            phone="+91-9876543216",
            is_active=True,
            can_claim_expenses=False,
            password_set_at=now,
            is_password_set=True,
            account_status="active",
            created_at=now
        )
        db.add(employee_no_perm)
        
        db.commit()
        print("✓ Initial users created successfully (7 users)")
        
    except Exception as e:
        db.rollback()
        print(f"✗ Error creating initial users: {str(e)}")
        raise
    finally:
        db.close()


def create_sample_expenses():
    """Create sample expenses with comprehensive data"""
    print("\nCreating sample expenses...")
    db = SessionLocal()
    
    try:
        # Check if expenses already exist
        if db.query(Expense).first():
            print("✓ Expenses already exist, skipping...")
            return
        
        now = datetime.utcnow()
        employee_a = db.query(User).filter(User.employee_id == "EMP005").first()
        employee_b = db.query(User).filter(User.employee_id == "EMP006").first()
        
        if not employee_a or not employee_b:
            print("✗ Employees not found, skipping expense creation")
            return
        
        # Sample expenses
        expenses_data = [
            {
                "employee_id": employee_a.id,
                "expense_number": "EXP-20260115-001",
                "category": ExpenseCategory.FOOD,
                "amount": 750.0,
                "expense_date": now - timedelta(days=5),
                "description": "Client lunch meeting",
                "bill_file_path": "uploads/5/bills/bill_001.jpg",
                "bill_file_name": "restaurant_bill.jpg",
                "bill_number": "INV001",
                "vendor_name": "The Restaurant",
                "is_self_declaration": False,
                "status": ExpenseStatus.APPROVED,
                "ai_confidence_score": 95.0,
                "is_valid_bill": True,
                "has_gst": True,
                "is_within_limits": True,
                "approved_at": now - timedelta(days=2),
                "submitted_at": now - timedelta(days=5),
                "ai_summary": "Legitimate restaurant bill with GST. Amount matches submitted claim.",
                "ai_recommendation": "approve",
                "file_hash": hashlib.sha256(b"bill_001_content").hexdigest(),
                "duplicate_check_status": "clean"
            },
            {
                "employee_id": employee_a.id,
                "expense_number": "EXP-20260114-002",
                "category": ExpenseCategory.TRAVEL,
                "amount": 2000.0,
                "expense_date": now - timedelta(days=10),
                "description": "Flight to Mumbai for client presentation",
                "bill_file_path": "uploads/5/bills/flight_ticket.pdf",
                "bill_file_name": "flight_booking.pdf",
                "bill_number": "BK123456",
                "vendor_name": "AIRLINES",
                "travel_mode": TravelMode.FLIGHT_ECONOMY,
                "travel_from": "Delhi",
                "travel_to": "Mumbai",
                "is_self_declaration": False,
                "status": ExpenseStatus.APPROVED,
                "ai_confidence_score": 98.0,
                "is_valid_bill": True,
                "has_gst": True,
                "is_within_limits": True,
                "approved_at": now - timedelta(days=1),
                "submitted_at": now - timedelta(days=7),
                "ai_summary": "Flight ticket with valid airline details and GST invoice.",
                "ai_recommendation": "approve",
                "file_hash": hashlib.sha256(b"flight_booking_content").hexdigest(),
                "duplicate_check_status": "clean"
            },
            {
                "employee_id": employee_b.id,
                "expense_number": "EXP-20260113-003",
                "category": ExpenseCategory.ACCOMMODATION,
                "amount": 3500.0,
                "expense_date": now - timedelta(days=8),
                "description": "Hotel stay in Bangalore for conference",
                "bill_file_path": "uploads/6/bills/hotel_receipt.pdf",
                "bill_file_name": "hotel_bill.pdf",
                "bill_number": "HO789",
                "vendor_name": "GRAND HOTEL",
                "is_self_declaration": False,
                "status": ExpenseStatus.APPROVED,
                "ai_confidence_score": 92.0,
                "is_valid_bill": True,
                "has_gst": True,
                "is_within_limits": True,
                "approved_at": now - timedelta(days=1),
                "submitted_at": now - timedelta(days=6),
                "ai_summary": "Hotel bill with proper GST details and valid dates.",
                "ai_recommendation": "approve",
                "file_hash": hashlib.sha256(b"hotel_bill_content").hexdigest(),
                "duplicate_check_status": "clean"
            },
            {
                "employee_id": employee_a.id,
                "expense_number": "EXP-20260112-004",
                "category": ExpenseCategory.MEDICAL,
                "amount": 150.0,
                "expense_date": now - timedelta(days=3),
                "description": "Medical consultation and prescription",
                "bill_file_path": "uploads/5/bills/medical_bill.jpg",
                "bill_file_name": "medical_receipt.jpg",
                "bill_number": "MED456",
                "vendor_name": "City Clinic",
                "is_self_declaration": False,
                "status": ExpenseStatus.SUBMITTED,
                "ai_confidence_score": 85.0,
                "is_valid_bill": True,
                "has_gst": False,
                "is_within_limits": True,
                "submitted_at": now - timedelta(days=3),
                "ai_summary": "Medical bill. No GST as per medical exemption.",
                "ai_recommendation": "approve",
                "file_hash": hashlib.sha256(b"medical_bill_content").hexdigest(),
                "duplicate_check_status": "clean",
                "current_approver_level": "manager"
            },
            {
                "employee_id": employee_b.id,
                "expense_number": "EXP-20260111-005",
                "category": ExpenseCategory.COMMUNICATION,
                "amount": 500.0,
                "expense_date": now - timedelta(days=2),
                "description": "Internet and mobile bill reimbursement",
                "bill_file_path": "uploads/6/bills/comm_bill.pdf",
                "bill_file_name": "telecom_invoice.pdf",
                "bill_number": "COM123",
                "vendor_name": "TELECOM PROVIDER",
                "is_self_declaration": False,
                "status": ExpenseStatus.SUBMITTED,
                "ai_confidence_score": 88.0,
                "is_valid_bill": True,
                "has_gst": True,
                "is_within_limits": True,
                "submitted_at": now - timedelta(days=2),
                "ai_summary": "Telecom bill with GST. Valid for business communication.",
                "ai_recommendation": "approve",
                "file_hash": hashlib.sha256(b"telecom_bill_content").hexdigest(),
                "duplicate_check_status": "clean",
                "current_approver_level": "manager"
            },
            {
                "employee_id": employee_a.id,
                "expense_number": "EXP-20260110-006",
                "category": ExpenseCategory.OTHER,
                "amount": 400.0,
                "expense_date": now - timedelta(days=15),
                "description": "No bill provided - local shop purchase",
                "bill_file_path": "uploads/5/bills/no_bill.txt",
                "bill_file_name": "no_bill_declaration.txt",
                "is_self_declaration": True,
                "declaration_reason": "Small purchase from local vendor, no receipt issued",
                "no_bill_category": "local_shop",
                "status": ExpenseStatus.REJECTED,
                "ai_confidence_score": 30.0,
                "is_valid_bill": False,
                "is_within_limits": True,
                "submitted_at": now - timedelta(days=12),
                "rejected_at": now - timedelta(days=8),
                "rejection_reason": "No proper bill documentation provided",
                "ai_summary": "Self-declaration without valid bill. Local shop - authenticity cannot be verified.",
                "ai_recommendation": "reject",
                "validation_errors": {"no_bill": "Missing bill document", "authenticity": "Cannot verify"},
                "file_hash": hashlib.sha256(b"no_bill_content").hexdigest(),
                "duplicate_check_status": "clean"
            },
            {
                "employee_id": employee_b.id,
                "expense_number": "EXP-20260109-007",
                "category": ExpenseCategory.FOOD,
                "amount": 1500.0,
                "expense_date": now - timedelta(days=20),
                "description": "Dummy bill - suspicious vendor",
                "bill_file_path": "uploads/6/bills/dummy_bill.jpg",
                "bill_file_name": "suspicious_vendor.jpg",
                "bill_number": "[FAKE]",
                "vendor_name": "Unknown Vendor",
                "is_self_declaration": False,
                "status": ExpenseStatus.REJECTED,
                "ai_confidence_score": 15.0,
                "is_valid_bill": False,
                "has_gst": False,
                "is_within_limits": False,
                "submitted_at": now - timedelta(days=18),
                "rejected_at": now - timedelta(days=15),
                "rejection_reason": "Bill explicitly flagged as fake and dummy by AI analysis. Confidence score too low.",
                "ai_summary": "⚠️ FAKE BILL: Explicitly states 'FAKE EXPENSE BILL'. Dummy bill generated for application testing.",
                "ai_recommendation": "reject",
                "validation_errors": {"authenticity": "Fake and dummy bill", "confidence_score": "Critically low (15%)", "bill_number": "Invalid format"},
                "file_hash": hashlib.sha256(b"dummy_bill_content").hexdigest(),
                "duplicate_check_status": "clean"
            }
        ]
        
        for exp_data in expenses_data:
            expense = Expense(**exp_data)
            db.add(expense)
        
        db.commit()
        print(f"✓ Sample expenses created successfully ({len(expenses_data)} expenses)")
        
    except Exception as e:
        db.rollback()
        print(f"✗ Error creating sample expenses: {str(e)}")
        raise
    finally:
        db.close()


def create_sample_approvals():
    """Create sample approvals for workflow demonstration"""
    print("\nCreating sample approvals...")
    db = SessionLocal()
    
    try:
        # Check if approvals already exist
        if db.query(Approval).first():
            print("✓ Approvals already exist, skipping...")
            return
        
        now = datetime.utcnow()
        manager = db.query(User).filter(User.role == "manager").first()
        finance = db.query(User).filter(User.role == "finance").first()
        
        if not manager or not finance:
            print("✗ Manager or Finance user not found")
            return
        
        # Get approved expenses
        approved_expenses = db.query(Expense).filter(
            Expense.status == ExpenseStatus.APPROVED
        ).all()
        
        for expense in approved_expenses:
            # Manager approval
            manager_approval = Approval(
                expense_id=expense.id,
                approver_id=manager.id,
                level=ApprovalLevel.MANAGER,
                status=ApprovalStatus.APPROVED,
                comments="Looks good, forwarding to finance",
                ai_summary="Manager: Expense within limits, moving to finance",
                created_at=expense.submitted_at,
                reviewed_at=expense.submitted_at + timedelta(days=1)
            )
            db.add(manager_approval)
            
            # Finance approval
            finance_approval = Approval(
                expense_id=expense.id,
                approver_id=finance.id,
                level=ApprovalLevel.FINANCE,
                status=ApprovalStatus.APPROVED,
                comments="Approved for payment processing",
                ai_summary="Finance: All validations passed, ready for payment",
                created_at=expense.submitted_at + timedelta(days=1),
                reviewed_at=expense.approved_at
            )
            db.add(finance_approval)
        
        # Get submitted expenses and create pending approvals
        submitted_expenses = db.query(Expense).filter(
            Expense.status == ExpenseStatus.SUBMITTED
        ).all()
        
        for expense in submitted_expenses:
            manager_approval = Approval(
                expense_id=expense.id,
                approver_id=manager.id,
                level=ApprovalLevel.MANAGER,
                status=ApprovalStatus.PENDING,
                comments=None,
                created_at=expense.submitted_at
            )
            db.add(manager_approval)
        
        db.commit()
        print(f"✓ Sample approvals created successfully")
        
    except Exception as e:
        db.rollback()
        print(f"✗ Error creating sample approvals: {str(e)}")
        raise
    finally:
        db.close()


def print_setup_summary():
    """Print setup summary and credentials"""
    print("\n" + "=" * 70)
    print("✓ DATABASE SETUP COMPLETED SUCCESSFULLY!")
    print("=" * 70)
    
    print("\n📋 CREATED DATA SUMMARY:")
    print("  • Users: 7 (1 Admin, 1 Manager, 1 HR, 1 Finance, 3 Employees)")
    print("  • Sample Expenses: 7 (with AI analysis, duplicates, self-declarations)")
    print("  • Approvals: Multi-level workflow examples")
    
    print("\n🔐 TEST USER CREDENTIALS:")
    print("  ┌─ Admin User ──────────────────────────────────────────────────┐")
    print("  │ Email: admin@expensesystem.com                                 │")
    print("  │ Password: admin123                                             │")
    print("  │ Role: System Administrator                                     │")
    print("  └────────────────────────────────────────────────────────────────┘")
    
    print("  ┌─ Manager User ────────────────────────────────────────────────┐")
    print("  │ Email: manager@expensesystem.com                              │")
    print("  │ Password: manager123                                           │")
    print("  │ Role: Approver (Manager Level)                                │")
    print("  └────────────────────────────────────────────────────────────────┘")
    
    print("  ┌─ Finance User ────────────────────────────────────────────────┐")
    print("  │ Email: finance@expensesystem.com                              │")
    print("  │ Password: finance123                                           │")
    print("  │ Role: Approver (Finance Level)                                │")
    print("  └────────────────────────────────────────────────────────────────┘")
    
    print("  ┌─ Employee Users ──────────────────────────────────────────────┐")
    print("  │ Email: employeea@expensesystem.com (Grade A)                  │")
    print("  │ Email: employeeb@expensesystem.com (Grade B)                  │")
    print("  │ Email: employeenoperm@expensesystem.com (No Claim Permission) │")
    print("  │ Password: employee123 (for all employees)                      │")
    print("  └────────────────────────────────────────────────────────────────┘")
    
    print("\n🚀 NEXT STEPS:")
    print("  1. Start the application:")
    print("     • With Docker: docker-compose up")
    print("     • With Uvicorn: uvicorn src.main:app --reload")
    print("  2. Access API Documentation: http://localhost:8000/api/docs")
    print("  3. Login with any test user credentials above")
    print("  4. View sample expenses and approval workflows")
    
    print("\n📊 SAMPLE DATA DETAILS:")
    print("  • Food Expense: 750 INR (Restaurant Bill) - APPROVED")
    print("  • Travel Expense: 2000 INR (Flight Ticket) - APPROVED")
    print("  • Accommodation: 3500 INR (Hotel Receipt) - APPROVED")
    print("  • Medical: 150 INR (Clinic Bill) - PENDING APPROVAL")
    print("  • Communication: 500 INR (Telecom Bill) - PENDING APPROVAL")
    print("  • Self-Declaration: 400 INR (No Receipt) - REJECTED")
    print("  • Dummy Bill: 1500 INR (Fake Bill) - REJECTED (AI Detected)")
    
    print("\n🤖 AI ANALYSIS FEATURES DEMONSTRATED:")
    print("  ✓ Bill authenticity verification (Confidence scores 15%-98%)")
    print("  ✓ GST and stamp detection")
    print("  ✓ Expense limit validation by employee grade")
    print("  ✓ Self-declaration support with reasons")
    print("  ✓ Duplicate detection (file hash comparison)")
    print("  ✓ Fake bill identification (15% confidence flagged as REJECT)")
    
    print("\n" + "=" * 70 + "\n")


def main():
    """Main setup function"""
    print("=" * 70)
    print("EXPENSE REIMBURSEMENT SYSTEM - DATABASE SETUP")
    print("=" * 70)
    
    try:
        create_tables()
        create_initial_users()
        create_sample_expenses()
        create_sample_approvals()
        print_setup_summary()
        
    except Exception as e:
        print(f"\n✗ Database setup failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()