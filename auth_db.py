"""
SQLite Database & Authentication Utility Module using Bcrypt.
Manages user registration, secure password hashing, and authentication for Smart Agriculture.
"""
import os
import re
import sqlite3
import hashlib
import bcrypt

DB_DIR = os.path.join(os.path.dirname(__file__), "data")
DB_PATH = os.path.join(DB_DIR, "users.db")
BCRYPT_WORK_FACTOR = 12


def get_db_connection():
    """Ensure data directory exists and return a SQLite connection."""
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


_DB_INITIALIZED = False

def init_db():
    """Initialize the users table if it does not exist and ensure schema is up to date."""
    global _DB_INITIALIZED
    if _DB_INITIALIZED:
        return

    with get_db_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                password_needs_reset INTEGER DEFAULT 0
            );
        """)
        # Ensure password_needs_reset column exists if table was created previously
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        if "password_needs_reset" not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN password_needs_reset INTEGER DEFAULT 0")
        conn.commit()
    _DB_INITIALIZED = True


def hash_password(password: str) -> str:
    """Hash a password using bcrypt with a work factor (rounds) of 12."""
    if not password:
        raise ValueError("Password cannot be empty")
    salt = bcrypt.gensalt(rounds=BCRYPT_WORK_FACTOR)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def is_bcrypt_hash(stored_hash: str) -> bool:
    """Check if stored_hash matches standard bcrypt format ($2a$, $2b$, $2y$)."""
    if not stored_hash or not isinstance(stored_hash, str):
        return False
    return stored_hash.startswith(("$2a$", "$2b$", "$2y$"))


def verify_and_upgrade_password(stored_password: str, supplied_password: str) -> tuple[bool, str | None]:
    """
    Verify supplied_password against stored_password (bcrypt, legacy plaintext, MD5, SHA-1, SHA-256).
    Returns (valid: bool, upgraded_hash_or_none: str|None).
    - For valid bcrypt: returns (True, None)
    - For valid legacy format: returns (True, new_bcrypt_hash)
    - For invalid password: returns (False, None)
    """
    if not stored_password or not supplied_password:
        return False, None

    supplied_bytes = supplied_password.encode("utf-8")

    # 1. Bcrypt hash check
    if is_bcrypt_hash(stored_password):
        try:
            stored_bytes = stored_password.encode("utf-8")
            if bcrypt.checkpw(supplied_bytes, stored_bytes):
                return True, None
            return False, None
        except Exception:
            return False, None

    # 2. Legacy MD5 check (32 hex characters)
    if len(stored_password) == 32 and re.match(r"^[0-9a-fA-F]{32}$", stored_password):
        md5_hash = hashlib.md5(supplied_bytes).hexdigest().lower()
        if md5_hash == stored_password.lower():
            upgraded = hash_password(supplied_password)
            return True, upgraded
        return False, None

    # 3. Legacy SHA-1 check (40 hex characters)
    if len(stored_password) == 40 and re.match(r"^[0-9a-fA-F]{40}$", stored_password):
        sha1_hash = hashlib.sha1(supplied_bytes).hexdigest().lower()
        if sha1_hash == stored_password.lower():
            upgraded = hash_password(supplied_password)
            return True, upgraded
        return False, None

    # 4. Legacy SHA-256 check (64 hex characters)
    if len(stored_password) == 64 and re.match(r"^[0-9a-fA-F]{64}$", stored_password):
        sha256_hash = hashlib.sha256(supplied_bytes).hexdigest().lower()
        if sha256_hash == stored_password.lower():
            upgraded = hash_password(supplied_password)
            return True, upgraded
        return False, None

    # 5. Legacy Plaintext check
    if supplied_password == stored_password:
        upgraded = hash_password(supplied_password)
        return True, upgraded

    return False, None


def register_user(full_name: str, email: str, raw_password: str):
    """
    Validate, hash password with bcrypt (rounds=12), and insert new user into SQLite DB.
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

    # Hash password using bcrypt with work factor 12
    pw_hash = hash_password(password_str)

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO users (full_name, email, password_hash, password_needs_reset) VALUES (?, ?, ?, 0)",
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
    Look up user by email, verify password with verify_and_upgrade_password(),
    and immediately replace legacy stored passwords with bcrypt hashes upon successful login.
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
                "SELECT id, full_name, email, password_hash, password_needs_reset FROM users WHERE email = ?",
                (email_clean,)
            )
            row = cursor.fetchone()

        if not row:
            # Generic error against account enumeration
            return False, "Invalid email or password", None

        stored_hash = row["password_hash"]
        valid, upgraded_hash = verify_and_upgrade_password(stored_hash, password_str)

        if valid:
            # Immediately persist upgraded bcrypt hash to database
            if upgraded_hash is not None:
                with get_db_connection() as conn:
                    conn.execute(
                        "UPDATE users SET password_hash = ?, password_needs_reset = 0 WHERE id = ?",
                        (upgraded_hash, row["id"])
                    )
                    conn.commit()

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


def change_user_password(email: str, old_password: str, new_password: str):
    """
    Verify old password and update to new bcrypt hash (rounds=12).
    Returns (success: bool, message: str).
    """
    init_db()
    email_clean = str(email or "").strip().lower()
    old_str = str(old_password or "")
    new_str = str(new_password or "")

    if not email_clean or not old_str or not new_str:
        return False, "All fields are required."

    if len(new_str) < 8:
        return False, "New password must be at least 8 characters long."

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, password_hash FROM users WHERE email = ?",
                (email_clean,)
            )
            row = cursor.fetchone()

        if not row:
            return False, "User not found."

        stored_hash = row["password_hash"]
        valid, _ = verify_and_upgrade_password(stored_hash, old_str)

        if not valid:
            return False, "Incorrect old password."

        new_hash = hash_password(new_str)

        with get_db_connection() as conn:
            conn.execute(
                "UPDATE users SET password_hash = ?, password_needs_reset = 0 WHERE id = ?",
                (new_hash, row["id"])
            )
            conn.commit()

        return True, "Password updated successfully."

    except Exception as e:
        return False, f"Error changing password: {str(e)}"


def reset_user_password(email: str, new_password: str):
    """
    Directly update user password to new bcrypt hash (for administrative/reset flows).
    Returns (success: bool, message: str).
    """
    init_db()
    email_clean = str(email or "").strip().lower()
    new_str = str(new_password or "")

    if not email_clean or not new_str:
        return False, "Email and new password are required."

    if len(new_str) < 8:
        return False, "New password must be at least 8 characters long."

    try:
        new_hash = hash_password(new_str)
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET password_hash = ?, password_needs_reset = 0 WHERE email = ?",
                (new_hash, email_clean)
            )
            conn.commit()
            if cursor.rowcount == 0:
                return False, "User not found."

        return True, "Password reset successfully."

    except Exception as e:
        return False, f"Error resetting password: {str(e)}"
