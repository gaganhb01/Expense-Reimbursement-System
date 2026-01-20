# Expense Reimbursement Management System
## Complete Setup & Deployment Guide

---

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose installed
- Python 3.11+ (for local development)
- PostgreSQL 15+ (if not using Docker)
- Elasticsearch 8.x (if not using Docker)

### Setup Steps

#### 1. Clone and Navigate to Project
```bash
cd expense-reimbursement-system
```

#### 2. Create Environment File
```bash
cp .env.example .env
```

Edit `.env` and update:
- `SECRET_KEY` - Generate a secure key
- `GEMINI_API_KEY` - Your Google Gemini API key (Already set: AIzaSyDpLSmnEwblRlUwG6zEviC0D90mr3QHCMY)
- Database credentials (if needed)

#### 3. Start with Docker (Recommended)
```bash
# Build and start all services
docker-compose up --build

# Or run in background
docker-compose up -d
```

This will start:
- PostgreSQL database (port 5432)
- Redis cache (port 6379)
- Elasticsearch (port 9200)
- FastAPI application (port 8000)

#### 4. Setup Database (First Time Only)
```bash
# If using Docker:
docker-compose exec app python src/database/setup_database.py

# If running locally:
python src/database/setup_database.py
```

This creates:
- All database tables
- Initial test users with credentials

#### 5. Access the Application
- **API Documentation**: http://localhost:8000/api/docs
- **Alternative Docs**: http://localhost:8000/api/redoc
- **Health Check**: http://localhost:8000/health

---

## 👥 Default User Credentials

After running setup_database.py, these users are available:

| Role | Email | Password | Grade | Can Claim |
|------|-------|----------|-------|-----------|
| Admin | admin@expensesystem.com | admin123 | D | Yes |
| Manager | manager@expensesystem.com | manager123 | C | Yes |
| HR | hr@expensesystem.com | hr123 | C | Yes |
| Finance | finance@expensesystem.com | finance123 | C | Yes |
| Employee A | employeea@expensesystem.com | employee123 | A | Yes |
| Employee B | employeeb@expensesystem.com | employee123 | B | Yes |
| Employee (No Perm) | employeenoperm@expensesystem.com | employee123 | A | No |

---

## 📋 API Endpoint Guide

### Authentication Endpoints

#### 1. Login
```bash
POST /api/auth/login
Content-Type: application/x-www-form-urlencoded

username=employeea@expensesystem.com&password=employee123
```

Response:
```json
{
  "access_token": "eyJhbGc...",
  "refresh_token": "eyJhbGc...",
  "token_type": "bearer"
}
```

#### 2. Get Current User
```bash
GET /api/auth/me
Authorization: Bearer <access_token>
```

### Expense Endpoints

#### 1. Create Expense Claim (With AI Analysis)
```bash
POST /api/expenses/claim
Authorization: Bearer <access_token>
Content-Type: multipart/form-data

Form Data:
- category: "travel" | "food" | "medical" | "accommodation" | "communication" | "other"
- amount: 1200.00
- expense_date: "2026-01-05"
- description: "Travel from Bangalore to Mumbai for client meeting"
- travel_mode: "bus" | "train" | "flight_economy" | "flight_business" | "cab"
- travel_from: "Bangalore"
- travel_to: "Mumbai"
- bill_file: <file upload>
```

**What Happens:**
1. System checks if user has permission to claim expenses
2. Validates and saves the bill file
3. **AI analyzes the bill** and extracts:
   - Bill number, date, vendor name
   - Amount verification
   - GST details
   - Travel mode and class (for travel bills)
   - Required stamps/seals (for medical bills)
   - Authenticity check
4. Checks grade-based limits
5. Generates AI recommendation (APPROVE/REJECT/REVIEW)
6. Creates expense record
7. Notifies manager for approval

#### 2. Get My Expenses
```bash
GET /api/expenses/my-expenses?status=submitted&category=travel
Authorization: Bearer <access_token>
```

#### 3. Get Expense Detail
```bash
GET /api/expenses/{expense_id}
Authorization: Bearer <access_token>
```

### Approval Endpoints

#### 1. Get Pending Approvals (Manager/HR/Finance)
```bash
GET /api/approvals/pending
Authorization: Bearer <manager_token>
```

#### 2. Approve Expense
```bash
POST /api/approvals/{expense_id}/approve
Authorization: Bearer <manager_token>
Content-Type: application/json

{
  "comments": "Approved. All documents are in order."
}
```

#### 3. Reject Expense
```bash
POST /api/approvals/{expense_id}/reject
Authorization: Bearer <manager_token>
Content-Type: application/json

{
  "comments": "Missing GST details on the bill"
}
```

**What Happens:**
- AI generates detailed rejection reason
- Employee gets notification with explanation
- Audit log is created

### Notification Endpoints

#### 1. Get My Notifications
```bash
GET /api/notifications/my-notifications?unread_only=true
Authorization: Bearer <access_token>
```

#### 2. Mark as Read
```bash
PUT /api/notifications/{notification_id}/read
Authorization: Bearer <access_token>
```

---

## 🎯 Complete Workflow Example

### Employee Claims Expense

1. **Login**
```bash
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=employeea@expensesystem.com&password=employee123"
```

2. **Create Expense Claim**
```bash
curl -X POST "http://localhost:8000/api/expenses/claim" \
  -H "Authorization: Bearer <access_token>" \
  -F "category=travel" \
  -F "amount=1200" \
  -F "expense_date=2026-01-05" \
  -F "description=Bus travel for client meeting" \
  -F "travel_mode=bus" \
  -F "travel_from=Bangalore" \
  -F "travel_to=Mumbai" \
  -F "bill_file=@/path/to/bus_ticket.pdf"
```

**AI Analysis Results:**
```json
{
  "expense_number": "EXP-20260106-A1B2C3",
  "status": "submitted",
  "ai_analysis": {
    "is_authentic": true,
    "confidence_score": 92,
    "bill_number": "TKT123456",
    "vendor_name": "Karnataka State Transport",
    "has_gst": true,
    "travel_mode": "bus",
    "recommendation": "APPROVE",
    "summary": "Valid bus ticket from Bangalore to Mumbai dated 05-Jan-2026. Amount matches claimed amount. GST details present.",
    "red_flags": []
  },
  "is_within_limits": true
}
```

3. **Check Claim Status**
```bash
curl -X GET "http://localhost:8000/api/expenses/my-expenses" \
  -H "Authorization: Bearer <access_token>"
```

### Manager Reviews and Approves

1. **Login as Manager**
```bash
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=manager@expensesystem.com&password=manager123"
```

2. **Get Pending Approvals**
```bash
curl -X GET "http://localhost:8000/api/approvals/pending" \
  -H "Authorization: Bearer <manager_token>"
```

**Manager Sees:**
- Employee details
- Expense category and amount
- AI-generated summary and recommendation
- Confidence score
- Any red flags or issues

3. **Approve Expense**
```bash
curl -X POST "http://localhost:8000/api/approvals/EXP-20260106-A1B2C3/approve" \
  -H "Authorization: Bearer <manager_token>" \
  -H "Content-Type: application/json" \
  -d '{"comments": "Approved based on AI analysis"}'
```

4. **Employee Gets Notification**
```json
{
  "type": "expense_approved",
  "title": "Expense Approved",
  "message": "Your expense claim EXP-20260106-A1B2C3 has been approved by Manager",
  "is_read": false
}
```

---

## 🔧 Expense Grade Rules

### Grade A & B (Entry Level)
- **Travel**: Bus/Train only, max ₹1,500
- **Food**: Max ₹500 per claim
- **Medical**: Max ₹5,000 per claim
- **AI Checks**: Ticket type, class, amount limits

### Grade C (Mid Level)
- **Travel**: Bus/Train/Economy Flight, max ₹10,000
- **Food**: Max ₹1,000 per claim
- **Medical**: Max ₹15,000 per claim

### Grade D (Senior Level)
- **Travel**: All modes including Business class, max ₹25,000
- **Food**: Max ₹2,000 per claim
- **Medical**: Max ₹50,000 per claim

---

## 🤖 AI Validation Details

The AI system checks:

### For All Bills:
- ✅ Authenticity (original vs fake)
- ✅ Amount matches claimed amount
- ✅ Date is not future-dated
- ✅ Clear and legible
- ✅ Complete information

### For Food/Restaurant Bills:
- ✅ GST number present
- ✅ GSTIN format valid
- ✅ Tax breakdown shown
- ✅ Restaurant name and address

### For Travel Bills:
- ✅ PNR or ticket number
- ✅ Travel dates
- ✅ Class of travel
- ✅ Route information
- ✅ Mode matches grade limits

### For Medical Bills:
- ✅ Doctor/Hospital seal
- ✅ Doctor signature
- ✅ Medical registration number
- ✅ Prescription or diagnosis
- ✅ Treatment details

---

## 📊 Elasticsearch Search (For Managers)

Search expenses with advanced filters:

```bash
GET /api/reports/search?q=travel&category=travel&status=approved
Authorization: Bearer <manager_token>
```

Search Parameters:
- `q`: Full-text search
- `category`: Filter by category
- `status`: Filter by status
- `employee_id`: Filter by employee
- `min_amount`, `max_amount`: Amount range
- `from_date`, `to_date`: Date range

---

## 🔒 Security Features

1. **JWT Authentication**: All endpoints (except login) require valid token
2. **Role-Based Access**: Permissions checked on every request
3. **Grade-Based Limits**: Automatic validation
4. **File Validation**: Type and size checks
5. **Audit Logging**: Every action is logged
6. **Password Hashing**: Bcrypt with salt

---

## 📝 Logging

Logs are stored in `logs/` directory:
- `app.log`: All application logs
- `error.log`: Errors only
- `audit.log`: Audit trail

View real-time logs:
```bash
# If using Docker:
docker-compose logs -f app

# If running locally:
tail -f logs/app.log
```

---

## 🧪 Testing

Run tests:
```bash
# If using Docker:
docker-compose exec app pytest

# If running locally:
pytest
```

---

## 🛠️ Troubleshooting

### Common Issues

1. **Database Connection Error**
```bash
# Check if PostgreSQL is running
docker-compose ps postgres

# View logs
docker-compose logs postgres
```

2. **Elasticsearch Not Starting**
```bash
# Increase Docker memory (8GB recommended)
# Check logs
docker-compose logs elasticsearch
```

3. **AI Service Errors**
```bash
# Verify Gemini API key in .env
# Check logs for API errors
docker-compose logs app | grep "AI"
```

4. **File Upload Fails**
```bash
# Check upload directory permissions
chmod 755 uploads/

# Check file size limits in .env
```

---

## 🚀 Production Deployment

### Security Checklist:
- [ ] Change SECRET_KEY to strong random string
- [ ] Use environment-specific .env files
- [ ] Set DEBUG=False
- [ ] Use HTTPS only
- [ ] Configure firewall rules
- [ ] Set up database backups
- [ ] Configure log rotation
- [ ] Use Redis password
- [ ] Enable Elasticsearch security

### Environment Variables:
```env
# Production settings
ENVIRONMENT=production
DEBUG=False
SECRET_KEY=<super-strong-random-key>

# Use secure database
DATABASE_URL=postgresql://user:pass@prod-db:5432/expense_db

# Redis with password
REDIS_URL=redis://:password@redis:6379/0

# Restrict CORS
CORS_ORIGINS=https://yourdomain.com
```

---

## 📞 Support

For issues or questions:
1. Check logs in `logs/` directory
2. Review API documentation at `/api/docs`
3. Check this guide for common solutions
4. Review audit logs for detailed action history

---

## 🎉 You're All Set!

The system is now ready to use. Start by:
1. Logging in with test credentials
2. Creating a test expense claim
3. Reviewing the AI analysis
4. Approving/Rejecting as a manager
5. Checking notifications

**API Docs**: http://localhost:8000/api/docs

Happy expense managing! 🎯