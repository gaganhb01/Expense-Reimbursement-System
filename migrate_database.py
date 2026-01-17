"""
Database Migration - Add Trip Support and Multi-Bill Fields
Run this to upgrade your database
"""

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Database connection details
DATABASE_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'expense_db',
    'user': 'expense_user',
    'password': 'expense_password'
}


def run_migration():
    """Run database migration"""
    
    # Connect to database
    conn = psycopg2.connect(**DATABASE_CONFIG)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()
    
    print("🔧 Starting database migration...")
    
    try:
        # 1. Add trip fields to expenses table
        print("  → Adding trip fields...")
        cursor.execute("""
            ALTER TABLE expenses 
            ADD COLUMN IF NOT EXISTS trip_start_date DATE,
            ADD COLUMN IF NOT EXISTS trip_end_date DATE,
            ADD COLUMN IF NOT EXISTS trip_purpose TEXT,
            ADD COLUMN IF NOT EXISTS trip_duration_days INTEGER;
        """)
        
        # 2. Add multi-bill fields
        print("  → Adding multi-bill fields...")
        cursor.execute("""
            ALTER TABLE expenses
            ADD COLUMN IF NOT EXISTS is_multi_bill BOOLEAN DEFAULT FALSE,
            ADD COLUMN IF NOT EXISTS bill_count INTEGER DEFAULT 1,
            ADD COLUMN IF NOT EXISTS bill_files JSONB DEFAULT '[]'::jsonb;
        """)
        
        # 3. Add per-day breakdown
        print("  → Adding per-day breakdown field...")
        cursor.execute("""
            ALTER TABLE expenses
            ADD COLUMN IF NOT EXISTS per_day_breakdown JSONB DEFAULT '[]'::jsonb;
        """)
        
        # 4. Add daily limit validation
        print("  → Adding daily limit fields...")
        cursor.execute("""
            ALTER TABLE expenses
            ADD COLUMN IF NOT EXISTS is_within_daily_limits BOOLEAN DEFAULT TRUE,
            ADD COLUMN IF NOT EXISTS daily_limit_violations JSONB DEFAULT '[]'::jsonb;
        """)
        
        # 5. Add OCR text field
        print("  → Adding OCR text field...")
        cursor.execute("""
            ALTER TABLE expenses
            ADD COLUMN IF NOT EXISTS ocr_text TEXT;
        """)
        
        # 6. Add average per day
        print("  → Adding average per day field...")
        cursor.execute("""
            ALTER TABLE expenses
            ADD COLUMN IF NOT EXISTS average_per_day FLOAT DEFAULT 0.0;
        """)
        
        # 7. Create indexes for performance
        print("  → Creating indexes...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_expenses_trip_dates 
            ON expenses(trip_start_date, trip_end_date);
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_expenses_is_multi_bill 
            ON expenses(is_multi_bill);
        """)
        
        print("✅ Migration completed successfully!")
        print("\nNew fields added:")
        print("  - trip_start_date, trip_end_date, trip_purpose, trip_duration_days")
        print("  - is_multi_bill, bill_count, bill_files")
        print("  - per_day_breakdown, average_per_day")
        print("  - is_within_daily_limits, daily_limit_violations")
        print("  - ocr_text")
        
    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        raise
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    print("=" * 60)
    print("DATABASE MIGRATION - EXPENSE REIMBURSEMENT SYSTEM")
    print("=" * 60)
    run_migration()
    print("\n🎉 Database is ready for advanced features!")