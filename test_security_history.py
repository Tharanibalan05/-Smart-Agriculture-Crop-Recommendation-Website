"""
test_security_history.py
Automated security test suite for Per-User Prediction History Isolation.
"""
import os
import sys
import pandas as pd

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass
from utils import (
    HISTORY_PATH,
    HISTORY_COLUMNS,
    append_prediction_history,
    load_history,
    load_user_history,
    clear_user_history,
)

def run_security_tests():
    print("=" * 60)
    print("🔒 RUNNING PREDICTION HISTORY PRIVACY & SECURITY SUITE")
    print("=" * 60)

    user_a = "user_a@example.com"
    user_b = "user_b@example.com"

    # Backup existing history file if present
    backup_path = HISTORY_PATH + ".bak"
    if os.path.exists(HISTORY_PATH):
        if os.path.exists(backup_path):
            os.remove(backup_path)
        os.rename(HISTORY_PATH, backup_path)

    try:
        # Step 1: Create prediction record for USER_A
        record_a1 = {
            'timestamp': '2026-08-11 10:00:00',
            'user_email': user_a,
            'location': 'User A Location (Coimbatore)',
            'N': 90, 'P': 40, 'K': 40, 'ph': 6.5,
            'temperature': 28.0, 'humidity': 70.0, 'rainfall': 200.0,
            'best_crop': 'Rice', 'confidence': 95.0,
            'profit': 45000, 'risk': 'Low'
        }
        append_prediction_history(record_a1)

        # Step 2: Create prediction record for USER_B
        record_b1 = {
            'timestamp': '2026-08-11 11:00:00',
            'user_email': user_b,
            'location': 'User B Location (Madurai)',
            'N': 50, 'P': 30, 'K': 20, 'ph': 7.0,
            'temperature': 32.0, 'humidity': 60.0, 'rainfall': 100.0,
            'best_crop': 'Groundnut', 'confidence': 88.0,
            'profit': 32000, 'risk': 'Medium'
        }
        append_prediction_history(record_b1)

        # TEST 1: USER_A loads history
        df_a = load_user_history(user_a)
        print(f"\n[Test 1] USER_A History Count: {len(df_a)}")
        assert len(df_a) == 1, f"Expected 1 record for USER_A, got {len(df_a)}"
        assert df_a['user_email'].iloc[0] == user_a
        assert df_a['best_crop'].iloc[0] == 'Rice'
        assert user_b not in df_a['user_email'].values, "SECURITY VIOLATION: USER_A saw USER_B's record!"
        print("  ✅ TEST 1 PASSED: USER_A sees ONLY USER_A's history.")

        # TEST 2: USER_B loads history
        df_b = load_user_history(user_b)
        print(f"\n[Test 2] USER_B History Count: {len(df_b)}")
        assert len(df_b) == 1, f"Expected 1 record for USER_B, got {len(df_b)}"
        assert df_b['user_email'].iloc[0] == user_b
        assert df_b['best_crop'].iloc[0] == 'Groundnut'
        assert user_a not in df_b['user_email'].values, "SECURITY VIOLATION: USER_B saw USER_A's record!"
        print("  ✅ TEST 2 PASSED: USER_B sees ONLY USER_B's history.")

        # TEST 3: Unauthenticated / Unspecified User loads history
        df_guest = load_history(None)
        df_empty_str = load_history("")
        print(f"\n[Test 3] Unauthenticated User History Count: {len(df_guest)}")
        assert df_guest.empty, "SECURITY VIOLATION: Unauthenticated user accessed history!"
        assert df_empty_str.empty, "SECURITY VIOLATION: Empty email string accessed history!"
        print("  ✅ TEST 3 PASSED: Unauthenticated user gets 0 records.")

        # TEST 4: CSV Export Isolation for USER_A vs USER_B
        csv_a = df_a.to_csv(index=False)
        csv_b = df_b.to_csv(index=False)
        assert user_b not in csv_a, "SECURITY VIOLATION: USER_A CSV export contains USER_B email/data!"
        assert user_a not in csv_b, "SECURITY VIOLATION: USER_B CSV export contains USER_A email/data!"
        print("\n[Test 4] CSV Export Isolation:")
        print("  ✅ TEST 4 PASSED: CSV exports are strictly isolated per user.")

        # TEST 5: Clear History for USER_A only
        print("\n[Test 5] Clearing USER_A's history...")
        clear_user_history(user_a)

        df_a_after = load_user_history(user_a)
        df_b_after = load_user_history(user_b)

        assert df_a_after.empty, f"Expected USER_A history to be empty, but found {len(df_a_after)} records!"
        assert len(df_b_after) == 1, f"Expected USER_B history to remain intact (1 record), but found {len(df_b_after)}!"
        assert df_b_after['best_crop'].iloc[0] == 'Groundnut'
        print("  ✅ TEST 5 PASSED: USER_A clearing history deleted ONLY USER_A's records. USER_B's data remains safe.")

        print("\n" + "=" * 60)
        print("🎉 ALL SECURITY & PRIVACY TESTS PASSED SUCCESSFULLY!")
        print("=" * 60)

    finally:
        # Restore original history file
        if os.path.exists(HISTORY_PATH):
            os.remove(HISTORY_PATH)
        if os.path.exists(backup_path):
            os.rename(backup_path, HISTORY_PATH)

if __name__ == "__main__":
    run_security_tests()
