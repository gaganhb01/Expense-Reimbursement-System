"""
Application Configuration Settings
"""

from pydantic_settings import BaseSettings
from typing import List, Dict, Any, ClassVar
import os


class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    APP_NAME: str = "Expense Reimbursement System"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Database
    DATABASE_URL: str
    DATABASE_HOST: str = "localhost"
    DATABASE_PORT: int = 5432
    DATABASE_NAME: str = "expense_db"
    DATABASE_USER: str = "expense_user"
    DATABASE_PASSWORD: str = "expense_password"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    
    # Elasticsearch
    ELASTICSEARCH_URL: str = "http://localhost:9200"
    ELASTICSEARCH_INDEX: str = "expense_claims"
    
    # JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Google Gemini AI
    GEMINI_API_KEY: str
    GEMINI_MODEL: str = "gemini-2.5-flash-preview"
    
    # File Upload
    MAX_FILE_SIZE: int = 10485760  # 10MB
    ALLOWED_EXTENSIONS: str = "pdf,jpg,jpeg,png"  # Comma-separated string
    UPLOAD_DIRECTORY: str = "uploads"
    
    @property
    def allowed_extensions_list(self) -> List[str]:
        """Convert comma-separated string to list"""
        return [ext.strip() for ext in self.ALLOWED_EXTENSIONS.split(",")]
    
    # Email (Optional)
    MAIL_USERNAME: str = ""
    MAIL_PASSWORD: str = ""
    MAIL_FROM: str = ""
    MAIL_PORT: int = 587
    MAIL_SERVER: str = "smtp.gmail.com"
    MAIL_TLS: bool = True
    MAIL_SSL: bool = False

    # SMTP Configuration - New fields 
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    FROM_EMAIL: str = ""
    FROM_NAME: str = "Expense Reimbursement System"
    
    # CORS
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:8000"  # Comma-separated string
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Convert comma-separated string to list"""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/app.log"
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    
    # Expense Rules by Grade
    EXPENSE_RULES: ClassVar[Dict[str, Dict[str, Any]]] = {
        "A": {
            "travel": {
                "allowed_modes": ["bus", "train"],
                "max_amount": 1500,
                "max_per_day": 1500
            },
            "food": {
                "max_amount": 500,
                "max_per_day": 500
            },
            "accommodation": {
                "max_amount": 2000,
                "max_per_day": 2000
            },
            "medical": {
                "max_amount": 1000,
                "max_per_day": 1000
            },
            "communication": {
                "max_amount": 300,
                "max_per_day": 300
            },
            "other": {
                "max_amount": 500,
                "max_per_day": 500
            }
        },
        "B": {
            "travel": {
                "allowed_modes": ["bus", "train", "cab"],
                "max_amount": 2000,
                "max_per_day": 2000
            },
            "food": {
                "max_amount": 700,
                "max_per_day": 700
            },
            "accommodation": {
                "max_amount": 3000,
                "max_per_day": 3000
            },
            "medical": {
                "max_amount": 1500,
                "max_per_day": 1500
            },
            "communication": {
                "max_amount": 500,
                "max_per_day": 500
            },
            "other": {
                "max_amount": 700,
                "max_per_day": 700
            }
        },
        "C": {
            "travel": {
                "allowed_modes": ["bus", "train", "cab", "flight_economy"],
                "max_amount": 3000,
                "max_per_day": 3000
            },
            "food": {
                "max_amount": 1000,
                "max_per_day": 1000
            },
            "accommodation": {
                "max_amount": 5000,
                "max_per_day": 5000
            },
            "medical": {
                "max_amount": 2000,
                "max_per_day": 2000
            },
            "communication": {
                "max_amount": 700,
                "max_per_day": 700
            },
            "other": {
                "max_amount": 1000,
                "max_per_day": 1000
            }
        },
        "D": {
            "travel": {
                "allowed_modes": ["bus", "train", "cab", "flight_economy", "flight_business"],
                "max_amount": 5000,
                "max_per_day": 5000
            },
            "food": {
                "max_amount": 1500,
                "max_per_day": 1500
            },
            "accommodation": {
                "max_amount": 7000,
                "max_per_day": 7000
            },
            "medical": {
                "max_amount": 3000,
                "max_per_day": 3000
            },
            "communication": {
                "max_amount": 1000,
                "max_per_day": 1000
            },
            "other": {
                "max_amount": 1500,
                "max_per_day": 1500
            }
        }
    }
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Create settings instance
settings = Settings()


# Ensure upload directory exists
os.makedirs(settings.UPLOAD_DIRECTORY, exist_ok=True)
os.makedirs("logs", exist_ok=True)