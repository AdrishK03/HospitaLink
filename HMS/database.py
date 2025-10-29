"""
database.py
-----------
Database configuration, connection management, and initialization
for the Hospital Management System.

This module handles:
- PostgreSQL connection setup
- Database table creation
- Default admin user creation
- Appointment status fixes
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from werkzeug.security import generate_password_hash
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
DATABASE_URL = os.environ.get("DATABASE_URL")
ADMIN_EMAIL = 'admin@hospital.com'
ADMIN_PASSWORD = 'admin123'

# Fix Render's "postgres://" format for psycopg2
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)


def get_db():
    """
    Establish and return a new PostgreSQL database connection.
    
    Returns:
        connection: PostgreSQL connection with RealDictCursor
        
    Raises:
        EnvironmentError: If DATABASE_URL is not set
    """
    if not DATABASE_URL:
        raise EnvironmentError("DATABASE_URL not set. Cannot connect to PostgreSQL.")
    
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    return conn


def fix_appointment_status():
    """
    Update all appointments with NULL/None status to 'Pending'.
    Run on startup to fix any legacy data issues.
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        conn = get_db()
        c = conn.cursor()
        
        # Update NULL/empty status to 'Pending'
        c.execute("UPDATE appointments SET status = 'Pending' WHERE status IS NULL OR status = ''")
        rows_affected = c.rowcount
        
        conn.commit()
        conn.close()
        
        if rows_affected > 0:
            print(f"✅ Fixed {rows_affected} appointments with NULL/None status")
        return True
    except Exception as e:
        print(f"⚠️ Error fixing appointment statuses: {e}")
        return False


def create_tables():
    """
    Create all required database tables if they don't exist.
    
    Tables created:
        - users: System users (admin, doctor, patient)
        - appointments: Patient appointments
        - medical_records: Patient medical history
        - billing: Billing and payment records
    """
    conn = get_db()
    c = conn.cursor()

    # Users Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            specialization TEXT,
            contact TEXT,
            approved INTEGER DEFAULT 0
        )
    ''')

    # Appointments Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS appointments (
            id SERIAL PRIMARY KEY,
            patient_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            doctor_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            reason TEXT,
            status TEXT DEFAULT 'Pending'
        )
    ''')

    # Medical Records Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS medical_records (
            id SERIAL PRIMARY KEY,
            patient_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            doctor_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            diagnosis TEXT,
            prescription TEXT,
            report_filename TEXT,
            date TEXT NOT NULL
        )
    ''')

    # Billing Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS billing (
            id SERIAL PRIMARY KEY,
            patient_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            doctor_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            appointment_id INTEGER,
            description TEXT,
            total_amount REAL NOT NULL,
            status TEXT DEFAULT 'Unpaid',
            date TEXT NOT NULL
        )
    ''')

    conn.commit()
    conn.close()
    print("✅ Database tables created successfully!")


def create_default_admin():
    """
    Create default admin user if it doesn't exist.
    
    Default credentials:
        Email: admin@hospital.com
        Password: admin123
    """
    conn = get_db()
    c = conn.cursor()
    
    # Check if admin exists
    c.execute("SELECT id FROM users WHERE email = %s", (ADMIN_EMAIL,))
    if not c.fetchone():
        admin_password_hash = generate_password_hash(ADMIN_PASSWORD)
        c.execute(
            "INSERT INTO users (name, email, password, role, approved) VALUES (%s, %s, %s, %s, %s)",
            ('Admin', ADMIN_EMAIL, admin_password_hash, 'admin', 1)
        )
        conn.commit()
        print(f"✅ Default admin created: {ADMIN_EMAIL}")
    else:
        print(f"ℹ️  Admin already exists: {ADMIN_EMAIL}")
    
    conn.close()


def init_db():
    """
    Initialize the entire database.
    
    This function:
        1. Creates all tables
        2. Creates default admin user
        3. Fixes any appointment status issues
        
    Call this on application startup.
    """
    try:
        print("🚀 Initializing database...")
        
        # Step 1: Create tables
        create_tables()
        
        # Step 2: Create default admin
        create_default_admin()
        
        # Step 3: Fix appointment statuses
        print("🔧 Checking for appointments with NULL status...")
        fix_appointment_status()
        
        print("✅ Database initialization complete!")
        return True
        
    except Exception as e:
        print(f"❌ ERROR during database initialization: {e}")
        return False


# For backward compatibility (if called from deployment scripts)
def setup_database():
    """
    Wrapper function for deployment scripts.
    Redirects to init_db().
    """
    print("⚠️ WARNING: setup_database() called. Redirecting to init_db().")
    return init_db()


if __name__ == '__main__':
    """
    Allow running this file directly to initialize database.
    Usage: python database.py
    """
    print("=" * 60)
    print("Hospital Management System - Database Setup")
    print("=" * 60)
    
    if not DATABASE_URL:
        print("❌ ERROR: DATABASE_URL environment variable not set!")
        print("Please set DATABASE_URL before running database setup.")
        exit(1)
    
    success = init_db()
    
    if success:
        print("\n" + "=" * 60)
        print("✅ Database setup completed successfully!")
        print("=" * 60)
        print(f"\nDefault Admin Credentials:")
        print(f"  Email: {ADMIN_EMAIL}")
        print(f"  Password: {ADMIN_PASSWORD}")
        print("\n⚠️  Please change the admin password after first login!")
    else:
        print("\n" + "=" * 60)
        print("❌ Database setup failed!")
        print("=" * 60)
        exit(1)
