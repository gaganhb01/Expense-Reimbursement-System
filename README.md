# 🎯 Expense Reimbursement Management System

## AI-Powered, Industry-Grade Expense Management Solution

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A comprehensive expense reimbursement system with **AI-powered bill validation**, role-based access control, multi-level approval workflows, and real-time notifications.

---

## ✨ Key Features

### 🤖 AI-Powered Bill Analysis
- **Automatic Bill Reading** using Google Gemini AI
- Extracts bill details (number, date, vendor, amount, GST)
- **Authenticity Check** - Detects fake/altered bills
- **Smart Validation** - Verifies GST, stamps, signatures
- **AI Recommendations** - Suggests approve/reject/review
- Category-specific validation (travel, food, medical)

### 👥 Role-Based Access Control
- **4 Employee Grades** (A, B, C, D) with different limits
- **5 User Roles** (Employee, Manager, HR, Finance, Admin)
- Grade-based expense limits and restrictions
- Permission-based endpoint access

### 🔄 Multi-Level Approval Workflow
- **Manager → HR → Finance** approval chain
- AI-generated recommendations for each level
- Real-time notifications at each stage
- Automated rejection reason generation

### 🔍 Advanced Search & Analytics
- **Elasticsearch** integration for fast search
- Full-text search on descriptions
- Filter by category, status, amount, date
- Comprehensive reporting dashboard

### 📊 Complete Audit Trail
- Every action logged with timestamp
- User action tracking
- Change history for compliance
- Export audit logs

### 🔔 Real-Time Notifications
- In-app notifications
- Email notifications (optional)
- Status change alerts
- Approval/rejection notifications

---

## 🏗️ Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   FastAPI   │────▶│  PostgreSQL  │     │    Redis    │
│  (Backend)  │     │  (Database)  │     │   (Cache)   │
└─────────────┘     └──────────────┘     └─────────────┘
       │                                         │
       │            ┌──────────────┐             │
       └───────────▶│ Elasticsearch│◀────────────┘
                    │   (Search)   │
                    └──────────────┘
                           │
                    ┌──────────────┐
                    │  Gemini AI   │
                    │  (Analysis)  │
                    └──────────────┘
```

---

## 📋 Prerequisites

- **Docker** & Docker Compose (recommended)
- **Python 3.11+** (for local development)
- **PostgreSQL 15+**
- **Redis 7+**
- **Elasticsearch 8.x**
- **Google Gemini API Key**

---

## 🚀 Quick Start

### 1. Clone the Repository
```bash
git clone <repository-url>
cd expense-reimbursement-system
```

### 2. Setup Environment
```bash
cp .env.example .env
# Edit .env and set your Gemini API key and other settings
```

### 3. Start with Docker (Recommended)
```bash
docker-compose up --build
```

This starts:
- PostgreSQL (port 5432)
- Redis (port 6379)
- Elasticsearch (port 9200)
- FastAPI App (port 8000)

### 4. Initialize Database
```bash
docker-compose exec app python src/database/setup_database.py
```

### 5. Access the Application
- **API Docs**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc
- **Health Check**: http://localhost:8000/health

---

## 📚 Documentation

- **[Setup Guide](SETUP_GUIDE.md)** - Complete setup and deployment instructions
- **[Project Structure](PROJECT_STRUCTURE.md)** - Detailed architecture documentation
- **[API Documentation](http://localhost:8000/api/docs)** - Interactive API docs (Swagger)

---

## 🎯 Grade-Based Expense Rules

| Grade | Travel | Food | Medical |
|-------|--------|------|---------|
| **A & B** | Bus/Train only (₹1,500 max) | ₹500 max | ₹5,000 max |
| **C** | + Economy Flight (₹10,000 max) | ₹1,000 max | ₹15,000 max |
| **D** | + Business Class (₹25,000 max) | ₹2,000 max | ₹50,000 max |

---

## 🔐 Default Users

After running `setup_database.py`:

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@expensesystem.com | admin123 |
| Manager | manager@expensesystem.com | manager123 |
| HR | hr@expensesystem.com | hr123 |
| Finance | finance@expensesystem.com | finance123 |
| Employee (A) | employeea@expensesystem.com | employee123 |
| Employee (B) | employeeb@expensesystem.com | employee123 |

---

## 🔥 Key API Endpoints

### Authentication
- `POST /api/auth/login` - Login and get JWT token
- `GET /api/auth/me` - Get current user info
- `POST /api/auth/refresh` - Refresh access token

### Expenses
- `POST /api/expenses/claim` - Create expense claim (with AI analysis)
- `GET /api/expenses/my-expenses` - Get user's expenses
- `GET /api/expenses/{id}` - Get expense detail
- `DELETE /api/expenses/{id}` - Delete expense

### Approvals
- `GET /api/approvals/pending` - Get pending approvals
- `POST /api/approvals/{id}/approve` - Approve expense
- `POST /api/approvals/{id}/reject` - Reject expense

### Notifications
- `GET /api/notifications/my-notifications` - Get user notifications
- `PUT /api/notifications/{id}/read` - Mark as read

### Reports & Search
- `GET /api/reports/search` - Advanced search with filters
- `GET /api/reports/statistics` - Expense statistics
- `GET /api/reports/audit-logs` - Audit trail (Admin only)

---

## 🧪 Testing

### Run Tests
```bash
# With Docker
docker-compose exec app pytest

# Locally
pytest
```

### Test Coverage
```bash
pytest --cov=src --cov-report=html
```

---

## 🤖 AI Validation Process

When an employee submits an expense:

1. **Bill Upload** - System saves the bill file
2. **AI Analysis** - Gemini AI analyzes the bill:
   - Extracts all key information
   - Verifies authenticity
   - Checks for required elements (GST, stamps, etc.)
   - Validates against grade limits
3. **Recommendation** - AI suggests APPROVE/REJECT/REVIEW
4. **Manager Review** - Manager sees AI summary and makes decision
5. **Workflow** - Approved claims move through HR → Finance
6. **Notification** - Employee notified of decision

---

## 📊 Example Workflow

```
Employee (Grade A) → Uploads bus ticket for ₹1,200
                  ↓
              AI Analysis
                  ↓
      "Valid ticket, within limits"
      Recommendation: APPROVE
                  ↓
            Manager Review
                  ↓
              Approved
                  ↓
             HR Review
                  ↓
              Approved
                  ↓
           Finance Review
                  ↓
         Final Approval
                  ↓
        Employee Notified
```

---

## 🛠️ Technology Stack

- **Backend**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL 15
- **Cache**: Redis 7
- **Search**: Elasticsearch 8.x
- **AI**: Google Gemini AI (gemini-2.5-flash)
- **Authentication**: JWT + OAuth2
- **Container**: Docker + Docker Compose
- **Testing**: Pytest
- **Documentation**: OpenAPI (Swagger)

---

## 🔒 Security Features

- ✅ JWT-based authentication
- ✅ Password hashing (bcrypt)
- ✅ Role-based authorization
- ✅ API rate limiting
- ✅ File validation (type, size)
- ✅ SQL injection prevention
- ✅ XSS protection
- ✅ CORS configuration
- ✅ Comprehensive audit logging

---

## 📝 Logging

All logs stored in `logs/` directory:
- `app.log` - Application logs
- `error.log` - Error logs only
- `audit.log` - Audit trail

---

## 🚀 Production Deployment

### Security Checklist
- [ ] Change `SECRET_KEY` to strong random string
- [ ] Set `DEBUG=False`
- [ ] Use HTTPS only
- [ ] Configure firewall rules
- [ ] Enable database backups
- [ ] Use Redis password
- [ ] Enable Elasticsearch security
- [ ] Set up monitoring

See [SETUP_GUIDE.md](SETUP_GUIDE.md) for detailed production deployment instructions.

---

## 📞 Support

- **Documentation**: Check `/api/docs` for API reference
- **Setup Issues**: See [SETUP_GUIDE.md](SETUP_GUIDE.md)
- **Architecture**: See [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)

---

## 📄 License

MIT License - See [LICENSE](LICENSE) file for details

---

## 🎉 Features Highlights

- ✨ **AI-Powered** - Smart bill validation and recommendations
- 🔐 **Secure** - Industry-standard security practices
- 📊 **Comprehensive** - Complete workflow from claim to payment
- 🚀 **Fast** - Elasticsearch for lightning-fast search
- 📱 **Modern** - RESTful API with OpenAPI documentation
- 🐳 **Containerized** - Easy deployment with Docker
- 📈 **Scalable** - Microservices-ready architecture
- 🔍 **Transparent** - Complete audit trail
- 🔔 **Real-time** - Instant notifications
- 🌐 **Production-Ready** - Built for enterprise use

---

**Built with ❤️ using FastAPI, PostgreSQL, Redis, Elasticsearch, and Google Gemini AI**