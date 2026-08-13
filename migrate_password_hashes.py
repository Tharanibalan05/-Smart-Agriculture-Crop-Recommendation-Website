"""
migrate_password_hashes.py
Safe database password migration script for Smart Agriculture.
"""
import os
import sys
import sqlite3
import re

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

from auth_db import (
    get_db_connection,
    init_db,
    is_bcrypt_hash,
    hash_password,
)


def run_migration():
    init_db()
    
    users_scanned = 0
    bcrypt_count = 0
    legacy_plaintext_count = 0
    legacy_weak_hash_count = 0
    migrated_offline_count = 0
    reset_required_count = 0

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, email, password_hash, password_needs_reset FROM users")
        rows = cursor.fetchall()
        users_scanned = len(rows)

        for row in rows:
            user_id = row["id"]
            stored = row["password_hash"]
            
            if is_bcrypt_hash(stored):
                bcrypt_count += 1
                continue
            
            is_hex_hash = bool(
                (len(stored) in (32, 40, 64)) and re.match(r"^0[-9a-fA-F]+$", stored)
            )

            if is_hex_hash:
                legacy_weak_hash_count += 1
                conn.execute(
                    "UPDATE users SET password_needs_reset = 1 WHERE id = ?",
                    (user_id,)
                )
                reset_required_count += 1
            else:
                legacy_plaintext_count += 1
                try:
                    new_bcrypt_hash = hash_password(stored)
                    conn.execute(
                        "UPDATE users SET password_hash = ?, password_needs_reset = 0 WHERE id = ?",
                        (new_bcrypt_hash, user_id)
                    )
                    migrated_offline_count += 1
                except Exception:
                    conn.execute(
                        "UPDATE users SET password_needs_reset = 1 WHERE id = ?",
                        (user_id,)
                    )
                    reset_required_count += 1

        conn.commit()

    print("=" * 60)
    print("PASSWORD SECURITY MIGRATION SUMMARY")
    print("=" * 60)
    print(f"Users scanned: {users_scanned}")
    print(f"Bcrypt passwords: {bcrypt_count}")
    print("Legacy plaintext: ", legacy_plaintext_count)
    print("Legacy weak hashes: ", legacy_weak_hash_count)
    print("Successfully migrated offline: ", migrated_offline_count)
    print("Manual password reset required: ", reset_required_count)
    print("=" * 60)


if __name__ == "__main__":
    run_migration()
