#!/usr/bin/env python3
"""
Example usage of the auth_handler module
This demonstrates how to use the auth handler programmatically
"""

from auth_handler import (
    is_user_authorized,
    add_authorized_user,
    remove_authorized_user,
    list_authorized_users,
    add_pending_auth,
    get_pending_auth_users,
    remove_pending_auth
)

def example_authorize_user():
    """Example: Authorize a user"""
    print("=" * 60)
    print("Example: Authorizing a user")
    print("=" * 60)
    
    user_id = "123456789012345678"
    username = "example_user"
    
    # Add user to authorized list
    if add_authorized_user(user_id, username):
        print(f"✅ Successfully authorized user {user_id} ({username})")
    
    # Check if user is authorized
    if is_user_authorized(user_id):
        print(f"✅ User {user_id} is confirmed as authorized")
    
    print()

def example_check_authorization():
    """Example: Check if a user is authorized"""
    print("=" * 60)
    print("Example: Checking user authorization")
    print("=" * 60)
    
    authorized_user = "123456789012345678"
    unauthorized_user = "999999999999999999"
    
    # Check authorized user
    if is_user_authorized(authorized_user):
        print(f"✅ User {authorized_user} is AUTHORIZED")
    else:
        print(f"❌ User {authorized_user} is NOT authorized")
    
    # Check unauthorized user
    if is_user_authorized(unauthorized_user):
        print(f"✅ User {unauthorized_user} is AUTHORIZED")
    else:
        print(f"❌ User {unauthorized_user} is NOT authorized")
    
    print()

def example_list_users():
    """Example: List all authorized users"""
    print("=" * 60)
    print("Example: Listing authorized users")
    print("=" * 60)
    
    users = list_authorized_users()
    
    if not users:
        print("No authorized users found.")
    else:
        print(f"Found {len(users)} authorized user(s):\n")
        for user_id, data in users.items():
            print(f"  • User ID: {user_id}")
            print(f"    Username: {data.get('username', 'Unknown')}")
            print(f"    Authorized: {data.get('timestamp', 'N/A')}")
            print()
    
    print()

def example_pending_auth():
    """Example: Working with pending auth users"""
    print("=" * 60)
    print("Example: Managing pending auth users")
    print("=" * 60)
    
    user_id = "888888888888888888"
    request_id = "req_12345"
    channel_id = "channel_67890"
    
    # Add user to pending auth
    if add_pending_auth(user_id, request_id, channel_id):
        print(f"✅ Added user {user_id} to pending auth")
    
    # List pending auth users
    pending = get_pending_auth_users()
    print(f"\nPending auth users: {len(pending)}")
    for uid, data in pending.items():
        print(f"  • User {uid}: Request {data.get('request_id')}")
    
    # Simulate authorization
    print(f"\nSimulating authorization of user {user_id}...")
    add_authorized_user(user_id, "pending_user")
    
    # Check if now authorized
    if is_user_authorized(user_id):
        print(f"✅ User {user_id} is now AUTHORIZED")
        
        # Remove from pending
        data = remove_pending_auth(user_id)
        if data:
            print(f"✅ Removed user {user_id} from pending auth")
    
    print()

def example_cleanup():
    """Example: Clean up test data"""
    print("=" * 60)
    print("Cleaning up example data...")
    print("=" * 60)
    
    test_users = ["123456789012345678", "888888888888888888"]
    
    for user_id in test_users:
        if is_user_authorized(user_id):
            remove_authorized_user(user_id)
            print(f"✅ Removed test user {user_id}")
    
    print("✅ Cleanup complete")
    print()

def main():
    """Run all examples"""
    print("\n" + "=" * 60)
    print("  AUTH HANDLER - EXAMPLE USAGE")
    print("=" * 60)
    print()
    
    # Run examples
    example_authorize_user()
    example_check_authorization()
    example_list_users()
    example_pending_auth()
    
    # Ask if user wants to cleanup
    print("=" * 60)
    cleanup = input("Clean up test data? (y/n): ").strip().lower()
    if cleanup == 'y':
        example_cleanup()
    
    print("\n" + "=" * 60)
    print("  Examples complete!")
    print("=" * 60)
    print("\nFor more information, see AUTH_HANDLER_README.md")
    print()

if __name__ == "__main__":
    main()
