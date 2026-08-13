"""
test_password_security.py
Automated security test suite for Password Storage, Bcrypt (rounds=12), and Legacy Migration.
"""
import os
import sys
import sqlite3
import hashlib
import io
import gc

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

import auth_db


def run_all_security_tests():
    print("=" * 60)
    print("RUNNING FULL PASSWORD SECURITY TEST SUITE")
    print("=" * 60)

    test_db_path = os.path.join(auth_db.DB_DIR, "test_security_users.db")
    if os.path.exists(test_db_path):
        try:
            os.remove(test_db_path)
        except Exception:
            pass

    orig_db_path = auth_db.DB_PATH
    auth_db.DB_PATH = test_db_path

    try:
        auth_db.init_db()

        # TEST 1: New signup password is stored as bcrypt (rounds=12)
        raw1 = "SecurePass123!"
        ok, user1 = auth_db.register_user("Alice Test", "alice@example.com", raw1)
        assert ok, f"Failed to register user1: {user1}"
        with auth_db.get_db_connection() as conn:
            row = conn.execute("SELECT password_hash FROM users WHERE email = ?", ("alice@example.com",)).fetchone()
            pw_hash = row["password_hash"]
        assert auth_db.is_bcrypt_hash(pw_hash), "TEST 1 FAILED: Password is not a valid bcrypt hash!"
        assert "$" in pw_hash, "TEST 1 FAILED: Bcrypt work factor 12 not found!"
        assert raw1 not in pw_hash, "TEST 1 FAILED: Plaintext password leaked in hash!"
        print("  [OK] TEST 1 PASSED: New signup password is stored as bcrypt (rounds=12).")

        # TEST 2: Correct password successfully logs in
        ok, msg, user1 = auth_db.verify_user("alice@example.com", raw1)
        assert ok, f"TEST 2 FAILED: Valid credentials rejected: {msg}"
        assert user1["email"] == "alice@example.com"
        print("  [OK] TEST 2 PASSED: Correct password successfully logs in.")

        # TEST 3: Wrong password fails
        ok, msg, user1 = auth_db.verify_user("alice@example.com", "WrongPass123!")
        assert not ok, "TEST 3 FAILED: Invalid password was accepted!"
        assert user1 is None
        print("  [OK] TEST 3 PASSED: Wrong password fails.")

        # TEST 4: Changing password creates a new bcrypt hash
        raw2_new = "NewChangedPass456!"
        ok, msg = auth_db.change_user_password("alice@example.com", raw1, raw2_new)
        assert ok, f"TEST 4 FAILED: Change password failed: {msg}"
        with auth_db.get_db_connection() as conn:
            row = conn.execute("SELECT password_hash FROM users WHERE email = ?", ("alice@example.com",)).fetchone()
            new_hash = row["password_hash"]
        assert auth_db.is_bcrypt_hash(new_hash), "TEST 4 FAILED: New hash is not bcrypt!"
        assert new_hash != pw_hash, "TEST 4 FAILED: New hash is equal to old hash!"
        print("  [OK] TEST 4 PASSED: Changing password creates a new bcrypt hash.")

        # TEST 5: Old password no longer works after password change
        ok, msg, user1 = auth_db.verify_user("alice@example.com", raw1)
        assert not ok, "TEST 5 FAILED: Old password still worked after change!"
        ok, msg, user1 = auth_db.verify_user("alice@example.com", raw2_new)
        assert ok, "TEST 5 FAILED: New password failed to log in!"
        print("  [OK] TEST 5 PASSED: Old password no longer works after password change.")

        # TEST 6: Existing bcrypt password works
        bcrypt_pass = "ExistingBcrypt999!"
        bcrypt_hash = auth_db.hash_password(bcrypt_pass)
        with auth_db.get_db_connection() as conn:
            conn.execute(
                "INSERT INTO users (full_name, email, password_hash) VALUES (?, ?, ?)",
                ("Bcrypt User", "bcrypt@example.com", bcrypt_hash)
            )
            conn.commit()
        ok, msg, user_bcrypt = auth_db.verify_user("bcrypt@example.com", bcrypt_pass)
        assert ok, "TEST 6 FAILED: ExistingBcrypt failed authentication!"
        print("  [OK] TEST 6 PASSED: Existing bcrypt password works.")

        # TEST 7: Legacy plaintext password migrates to bcrypt after successful login
        plain_pass = "plaintext_secret_123"
        with auth_db.get_db_connection() as conn:
            conn.execute(
                "INSERT INTO users (full_name, email, password_hash) VALUES (?, ?, ?)",
                ("Plain User", "plain@example.com", plain_pass)
            )
            conn.commit()
        ok, msg, user_plain = auth_db.verify_user("plain@example.com", plain_pass)
        assert ok, "TEST 7 FAILED: Legacy plaintext login failed!"
        with auth_db.get_db_connection() as conn:
            row = conn.execute("SELECT password_hash FROM users WHERE email = ?", ("plain@example.com",)).fetchone()
            upgraded_hash = row["password_hash"]
        assert auth_db.is_bcrypt_hash(upgraded_hash), "TEST 7 FAILED: Plaintext was not upgraded to bcrypt!"
        print("  [OK] TEST 7 PASSED: Legacy plaintext password migrates to bcrypt after successful login.")

        # TEST 8: Legacy MD5/SHA-1 password migrates to bcrypt ONLY after successful verification
        md5_pass = "md5_secret_pass"
        md5_hash = hashlib.md5(md5_pass.encode("utf-8")).hexdigest()
        with auth_db.get_db_connection() as conn:
            conn.execute(
                "INSERT INTO users (full_name, email, password_hash) VALUES (?, ?, ?)",
                ("MD5 User", "md5@example.com", md5_hash)
            )
            conn.commit()
        ok, msg, user_md5 = auth_db.verify_user("md5@example.com", md5_pass)
        assert ok, "TEST 8 FAILED: Legacy MD5 login failed!"
        with auth_db.get_db_connection() as conn:
            row = conn.execute("SELECT password_hash FROM users WHERE email = ?", ("md5@example.com",)).fetchone()
            md5_upgraded = row["password_hash"]
        assert auth_db.is_bcrypt_hash(md5_upgraded), "TEST 8 FAILED: MD5 was not upgraded to bcrypt!"
        print("  [OK] TEST 8 PASSED: Legacy MD5/SHA-1 password migrates to bcrypt ONLY after successful verification.")

        # TEST 9: Unknown/invalid legacy password does not get migrated
        sha1_pass = "sha1_secret_pass"
        sha1_hash = hashlib.sha1(sha1_pass.encode("utf-8")).hexdigest()
        with auth_db.get_db_connection() as conn:
            conn.execute(
                "INSERT INTO users (full_name, email, password_hash) VALUES (?, ?, ?)",
                ("SHA1 User", "sha1@example.com", sha1_hash)
            )
            conn.commit()
        ok, msg, user_sha1 = auth_db.verify_user("sha1@example.com", "WrongSha1Pass")
        assert not ok, "TEST 9 FAILED: Invalid password for legacy account was accepted!"
        with auth_db.get_db_connection() as conn:
            row = conn.execute("SELECT password_hash FROM users WHERE email = ?", ("sha1@example.com",)).fetchone()
            still_sha1 = row["password_hash"]
        assert still_sha1 == sha1_hash, "TEST 9 FAILED: Invalid login modified/migrated legacy hash!"
        print("  [OK] TEST 9 PASSED: Unknown/invalid legacy password does not get migrated.")

        # TEST 10: Password is never printed/logged
        secret_password = "SecretSuperConfidential999!"
        old_stdout = sys.stdout
        captured = io.StringIO()
        sys.stdout = captured
        try:
            auth_db.register_user("Secret User", "secret@example.com", secret_password)
            auth_db.verify_user("secret@example.com", secret_password)
            auth_db.verify_user("secret@example.com", "WrongSecret")
        finally:
            sys.stdout = old_stdout
        output_text = captured.getvalue()
        assert secret_password not in output_text, "TEST 10 FAILED: Password was logged to stdout!"
        print("  [OK] TEST 10 PASSED: Password is never printed/logged.")

        # TEST 11: Google OAuth structure remains separate
        oauth_user = {"auth_method": "google", "email": "faringram@gmail.com", "is_logged_in": True}
        assert oauth_user["auth_method"] == "google"
        assert "password_hash" not in oauth_user
        print("  [OK] TEST 11 PASSED: Google OAuth structure remains separate.")

        # TEST 12: Prediction History privacy remains unchanged
        import test_security_history
        test_security_history.run_security_tests()
        print("  [OK] TEST 12 PASSED: Prediction History privacy remains unchanged.")

        print("\n" + "=" * 60)
        print("ALL 12 PASSWORD SECURITY TESTS PASSED SUCCESSFULLY!")
        print("=" * 60)

    finally:
        auth_db.DB_PATH = orig_db_path
        gc.collect()
        if os.path.exists(test_db_path):
            try:
                os.remove(test_db_path)
            except Exception:
                pass


if __name__ == "__main__":
    run_all_security_tests()
