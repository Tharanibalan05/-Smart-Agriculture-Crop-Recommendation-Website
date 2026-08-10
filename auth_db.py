"""
SQLite Database & Authentication Utility Module using Bcrypt.
Manages user registration, secure password hashing, and authentication for Smart Agriculture.
"""
import os
import re
import sqlite3
import bcrypt
from datetime import datetime

DB_DIR = os.path.join(os.path.dirname(__file__), "data")
DB_PATH = os.path.join(DB_DIR, "users.db")


def get_db_connection():
    """Ensure data directory exists and return a SQLite connection."""
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize the users table if it does not exist."""
    with get_db_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()


def register_user(full_name: str, email: str, raw_password: str):
    """
    Validate, hash password with bcrypt, and insert new user into SQLite DB.
    Returns (success: bool, result_message_or_dict: str|dict).
    """
    init_db()
    name_clean = str(full_name or "").strip()
    email_clean = str(email or "").strip().lower()
    password_str = str(raw_password or "")

    # Validation
    if not name_clean:
        return False, "Full Name is required."
    
    if not email_clean or not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email_clean):
        return False, "Please enter a valid email address."

    if len(password_str) < 8:
        return False, "Password must be at least 8 characters long."

    # Hash password using bcrypt
    salt = bcrypt.gensalt()
    pw_hash = bcrypt.hashpw(password_str.encode("utf-8"), salt).decode("utf-8")

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO users (full_name, email, password_hash) VALUES (?, ?, ?)",
                (name_clean, email_clean, pw_hash)
            )
            conn.commit()
            user_id = cursor.lastrowid

        user_data = {
            "id": user_id,
            "name": name_clean,
            "email": email_clean,
            "auth_method": "local"
        }
        return True, user_data

    except sqlite3.IntegrityError:
        return False, "Email already registered. Please sign in instead."
    except Exception as e:
        return False, f"Database error during registration: {str(e)}"


def verify_user(email: str, raw_password: str):
    """
    Look up user by email and verify password using bcrypt.checkpw().
    Returns (success: bool, message: str, user_dict: dict|None).
    """
    init_db()
    email_clean = str(email or "").strip().lower()
    password_str = str(raw_password or "")

    if not email_clean or not password_str:
        return False, "Invalid email or password", None

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, full_name, email, password_hash FROM users WHERE email = ?",
                (email_clean,)
            )
            row = cursor.fetchone()

        if not row:
            # Generic error against account enumeration
            return False, "Invalid email or password", None

        stored_hash = row["password_hash"]
        if bcrypt.checkpw(password_str.encode("utf-8"), stored_hash.encode("utf-8")):
            user_data = {
                "id": row["id"],
                "name": row["full_name"],
                "email": row["email"],
                "auth_method": "local"
            }
            return True, "Login successful", user_data
        else:
            return False, "Invalid email or password", None

    except Exception as e:
        return False, f"Authentication error: {str(e)}", None
