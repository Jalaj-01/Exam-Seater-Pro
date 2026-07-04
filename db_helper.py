import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "users.db")

def get_db_connection():
    """Establish a connection to the SQLite database."""
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize database tables if they do not exist."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        email TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        picture TEXT,
        institute_name TEXT,
        school_email TEXT,
        address TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Create activity_log table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS activity_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT,
        action TEXT NOT NULL,
        details TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    conn.commit()
    conn.close()

def is_user_onboarded(email):
    """Check if the user is registered and has completed the onboarding questionnaire."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT institute_name, school_email FROM users WHERE email = ?",
        (email,)
    )
    row = cursor.fetchone()
    conn.close()
    
    if row is None:
        return False
    
    # User is onboarded if both institute_name and school_email are present
    return bool(row["institute_name"] and row["school_email"])

def register_user(email, name, picture=None):
    """Insert a new user profile or update standard info on Google login."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO users (email, name, picture)
        VALUES (?, ?, ?)
        ON CONFLICT(email) DO UPDATE SET
            name = excluded.name,
            picture = COALESCE(excluded.picture, users.picture)
        """,
        (email, name, picture)
    )
    conn.commit()
    conn.close()

def update_onboarding(email, school_email, institute_name, address):
    """Save onboarding inputs for an existing user."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE users 
        SET school_email = ?, institute_name = ?, address = ?
        WHERE email = ?
        """,
        (school_email, institute_name, address, email)
    )
    conn.commit()
    conn.close()

def get_user(email):
    """Retrieve full user profile profile from database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None

def log_activity(email, action, details=None):
    """Append a log entry tracking user interaction."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO activity_log (email, action, details) VALUES (?, ?, ?)",
        (email, action, details)
    )
    conn.commit()
    conn.close()

def get_all_users():
    """Fetch list of all registered users."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_activity_logs(limit=100):
    """Fetch sorted activity log rows."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT activity_log.*, users.name 
        FROM activity_log 
        LEFT JOIN users ON activity_log.email = users.email 
        ORDER BY timestamp DESC LIMIT ?
        """,
        (limit,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_stats():
    """Calculate aggregate stats for the admin dashboard."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM users WHERE institute_name IS NOT NULL")
    onboarded_users = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM activity_log")
    total_logs = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(DISTINCT email) FROM activity_log WHERE date(timestamp) = date('now')")
    active_today = cursor.fetchone()[0]
    
    conn.close()
    return {
        "total_users": total_users,
        "onboarded_users": onboarded_users,
        "total_logs": total_logs,
        "active_today": active_today
    }

# Make sure tables are prepared on start
init_db()
