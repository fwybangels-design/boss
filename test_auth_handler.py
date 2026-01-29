#!/usr/bin/env python3
"""
Simple test script to verify auth_handler functionality
"""

import os
import sys
import json

# Test imports
print("Testing imports...")
try:
    from auth_handler import (
        is_user_authorized,
        add_authorized_user,
        remove_authorized_user,
        list_authorized_users,
        add_pending_auth,
        get_pending_auth_users,
        remove_pending_auth,
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

# Test 1: Add and check authorized user
print("\n" + "="*60)
print("Test 1: Add and check authorized user")
print("="*60)

cleanup_test_files()

test_user_id = "123456789"
test_username = "test_user"

# Add user
result = add_authorized_user(test_user_id, test_username)
if result:
    print(f"✅ Successfully added user {test_user_id}")
else:
    print(f"❌ Failed to add user {test_user_id}")
    sys.exit(1)

# Check if authorized
if is_user_authorized(test_user_id):
    print(f"✅ User {test_user_id} is authorized")
else:
    print(f"❌ User {test_user_id} is NOT authorized (should be)")
    sys.exit(1)

# Check unauthorized user
if not is_user_authorized("999999999"):
    print(f"✅ Unauthorized user correctly identified")
else:
    print(f"❌ Unauthorized user incorrectly authorized")
    sys.exit(1)

# Test 2: List authorized users
print("\n" + "="*60)
print("Test 2: List authorized users")
print("="*60)

users = list_authorized_users()
if test_user_id in users:
    print(f"✅ User {test_user_id} found in authorized list")
    data = users[test_user_id]
    if data.get("username") == test_username:
        print(f"✅ Username matches: {test_username}")
    else:
        print(f"❌ Username mismatch")
        sys.exit(1)
else:
    print(f"❌ User {test_user_id} not found in list")
    sys.exit(1)

# Test 3: Pending auth
print("\n" + "="*60)
print("Test 3: Pending auth functionality")
print("="*60)

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

# Test 4: Remove authorized user
print("\n" + "="*60)
print("Test 4: Remove authorized user")
print("="*60)

result = remove_authorized_user(test_user_id)
if result:
    print(f"✅ Successfully removed user {test_user_id}")
else:
    print(f"❌ Failed to remove user")
    sys.exit(1)

# Verify removal
if not is_user_authorized(test_user_id):
    print(f"✅ User {test_user_id} is no longer authorized")
else:
    print(f"❌ User {test_user_id} still authorized (should not be)")
    sys.exit(1)

# Test 5: File persistence
print("\n" + "="*60)
print("Test 5: File persistence")
print("="*60)

# Add multiple users
users_to_add = [
    ("111111111", "user1"),
    ("222222222", "user2"),
    ("333333333", "user3")
]

for uid, uname in users_to_add:
    add_authorized_user(uid, uname)

# Check file exists
if os.path.exists(AUTH_FILES["authorized_users"]):
    print(f"✅ Auth file created: {AUTH_FILES['authorized_users']}")
else:
    print(f"❌ Auth file not found")
    sys.exit(1)

# Read and verify JSON
with open(AUTH_FILES["authorized_users"], 'r') as f:
    data = json.load(f)
    if len(data) == 3:
        print(f"✅ File contains {len(data)} users")
    else:
        print(f"❌ Expected 3 users, found {len(data)}")
        sys.exit(1)

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
print("You can now use:")
print("  - python meow_with_auth.py  (to run the bot)")
print("  - python auth_manager.py    (to manage users)")
print("  - python example_auth_usage.py  (to see examples)")
