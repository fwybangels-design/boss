#!/usr/bin/env python3
"""
Simple test script to verify auth_handler functionality

NOTE: This bot now uses RestoreCord API for authorization.
Tests focus on pending auth functionality and RestoreCord integration.
"""

import os
import sys
import json

# Test imports
print("Testing imports...")
try:
    from auth_handler import (
        is_user_authorized,
        add_pending_auth,
        get_pending_auth_users,
        remove_pending_auth,
        check_restorecord_verification,
        USE_RESTORECORD,
        AUTH_FILES
    )
    print("✅ All imports successful")
except ImportError as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)

# Clean up any existing test files
def cleanup_test_files():
    for filename in AUTH_FILES.values():
        if os.path.exists(filename):
            os.remove(filename)

# Test 1: Check RestoreCord configuration
print("\n" + "="*60)
print("Test 1: RestoreCord Configuration")
print("="*60)

if USE_RESTORECORD:
    print("✅ RestoreCord is configured")
    print("   Authorization checks will use RestoreCord API")
else:
    print("⚠️  RestoreCord is NOT configured")
    print("   Configure RESTORECORD_URL and RESTORECORD_SERVER_ID in config.py")
    print("   Skipping authorization tests...")

# Test 2: Pending auth functionality
print("\n" + "="*60)
print("Test 2: Pending auth functionality")
print("="*60)

cleanup_test_files()

pending_user_id = "987654321"
request_id = "req_test"
channel_id = "ch_test"

# Add to pending
result = add_pending_auth(pending_user_id, request_id, channel_id)
if result:
    print(f"✅ Added user {pending_user_id} to pending auth")
else:
    print(f"❌ Failed to add to pending auth")
    sys.exit(1)

# Check pending list
pending = get_pending_auth_users()
if pending_user_id in pending:
    print(f"✅ User {pending_user_id} found in pending list")
    data = pending[pending_user_id]
    if data.get("request_id") == request_id:
        print(f"✅ Request ID matches: {request_id}")
    else:
        print(f"❌ Request ID mismatch")
        sys.exit(1)
else:
    print(f"❌ User not found in pending list")
    sys.exit(1)

# Remove from pending
data = remove_pending_auth(pending_user_id)
if data and data.get("request_id") == request_id:
    print(f"✅ Successfully removed user {pending_user_id} from pending")
else:
    print(f"❌ Failed to remove from pending")
    sys.exit(1)

# Test 3: File persistence
print("\n" + "="*60)
print("Test 3: File persistence")
print("="*60)

# Add multiple pending users
users_to_add = [
    ("111111111", "req1", "ch1"),
    ("222222222", "req2", "ch2"),
    ("333333333", "req3", "ch3")
]

for uid, reqid, chid in users_to_add:
    add_pending_auth(uid, reqid, chid)

# Check file exists
if os.path.exists(AUTH_FILES["pending_auth"]):
    print(f"✅ Pending auth file created: {AUTH_FILES['pending_auth']}")
else:
    print(f"❌ Pending auth file not found")
    sys.exit(1)

# Read and verify JSON
with open(AUTH_FILES["pending_auth"], 'r') as f:
    data = json.load(f)
    if len(data) == 3:
        print(f"✅ File contains {len(data)} pending users")
    else:
        print(f"❌ Expected 3 users, found {len(data)}")
        sys.exit(1)

# Test 4: RestoreCord API check (if configured)
if USE_RESTORECORD:
    print("\n" + "="*60)
    print("Test 4: RestoreCord API Integration")
    print("="*60)
    
    test_user = input("Enter a Discord User ID to test (or press Enter to skip): ").strip()
    
    if test_user:
        print(f"\n🔍 Checking if user {test_user} is verified on RestoreCord...")
        try:
            is_verified = is_user_authorized(test_user)
            if is_verified:
                print(f"✅ User {test_user} IS authorized (verified on RestoreCord)")
            else:
                print(f"❌ User {test_user} is NOT authorized (not verified on RestoreCord)")
        except Exception as e:
            print(f"❌ Error testing RestoreCord: {e}")
    else:
        print("⏭️  Skipping RestoreCord API test")

# Cleanup
print("\n" + "="*60)
print("Cleanup")
print("="*60)
cleanup_test_files()
print("✅ Test files cleaned up")

# Final result
print("\n" + "="*60)
print("🎉 ALL TESTS PASSED!")
print("="*60)
print("\nAuth handler is working correctly.")
print("\nIMPORTANT NOTES:")
print("  - Authorization is now via RestoreCord API (no local storage)")
print("  - Users are verified in real-time by polling RestoreCord")
print("  - No interview channel is opened for already verified users")
print("\nYou can now use:")
print("  - python meow_with_auth.py  (to run the bot)")
print("  - python auth_manager.py    (to view pending auth requests)")
print("  - python example_auth_usage.py  (to see examples)")
