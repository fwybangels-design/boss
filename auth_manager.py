#!/usr/bin/env python3
"""
Auth Manager CLI - Tool for managing authorized users
"""
import json
import os
import sys
import time
from auth_handler import (
    manually_authorize_user,
    manually_deauthorize_user,
    list_authorized_users,
    list_pending_auth_users,
    AUTH_FILES
)

def print_header(title):
    """Print a formatted header."""
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)

def display_menu():
    """Display the main menu."""
    print_header("AUTH MANAGER CLI")
    print("1. List Authorized Users")
    print("2. List Pending Auth Users")
    print("3. Authorize a User (add to whitelist)")
    print("4. Deauthorize a User (remove from whitelist)")
    print("5. Import Users from File")
    print("6. Export Authorized Users")
    print("7. Clear All Authorized Users")
    print("8. Exit")
    print("="*60)

def list_auth_users():
    """List all authorized users."""
    print_header("Authorized Users")
    users = list_authorized_users()
    
    if not users:
        print("❌ No authorized users found.")
        return
    
    print(f"Total: {len(users)} user(s)\n")
    for user_id, data in users.items():
        username = data.get("username", "Unknown")
        timestamp = data.get("timestamp", "N/A")
        print(f"  • User ID: {user_id}")
        print(f"    Username: {username}")
        print(f"    Authorized: {timestamp}")
        print()

def list_pending_users():
    """List all pending auth users."""
    print_header("Pending Auth Users")
    users = list_pending_auth_users()
    
    if not users:
        print("❌ No pending auth users found.")
        return
    
    print(f"Total: {len(users)} user(s)\n")
    for user_id, data in users.items():
        request_id = data.get("request_id", "N/A")
        channel_id = data.get("channel_id", "N/A")
        timestamp = data.get("timestamp", "N/A")
        print(f"  • User ID: {user_id}")
        print(f"    Request ID: {request_id}")
        print(f"    Channel ID: {channel_id}")
        print(f"    Pending Since: {timestamp}")
        print()

def authorize_user():
    """Authorize a user."""
    print_header("Authorize User")
    user_id = input("Enter User ID: ").strip()
    
    if not user_id:
        print("❌ User ID cannot be empty.")
        return
    
    username = input("Enter Username (optional): ").strip()
    username = username if username else None
    
    if manually_authorize_user(user_id, username):
        print(f"✅ Successfully authorized user {user_id}")
    else:
        print(f"❌ Failed to authorize user {user_id}")

def deauthorize_user():
    """Deauthorize a user."""
    print_header("Deauthorize User")
    user_id = input("Enter User ID: ").strip()
    
    if not user_id:
        print("❌ User ID cannot be empty.")
        return
    
    if manually_deauthorize_user(user_id):
        print(f"✅ Successfully deauthorized user {user_id}")
    else:
        print(f"❌ User {user_id} was not found in authorized list.")

def import_users_from_file():
    """Import users from a file."""
    print_header("Import Users from File")
    filename = input("Enter filename (one user ID per line): ").strip()
    
    if not os.path.exists(filename):
        print(f"❌ File '{filename}' not found.")
        return
    
    try:
        with open(filename, 'r') as f:
            lines = f.readlines()
        
        count = 0
        for line in lines:
            user_id = line.strip()
            if user_id and not user_id.startswith('#'):  # Skip comments
                if manually_authorize_user(user_id):
                    count += 1
                    print(f"✅ Authorized user {user_id}")
        
        print(f"\n✅ Successfully imported {count} user(s)")
    except Exception as e:
        print(f"❌ Error importing users: {e}")

def export_authorized_users():
    """Export authorized users to a file."""
    print_header("Export Authorized Users")
    filename = input("Enter output filename (default: auth_export.txt): ").strip()
    
    if not filename:
        filename = "auth_export.txt"
    
    users = list_authorized_users()
    
    if not users:
        print("❌ No authorized users to export.")
        return
    
    try:
        with open(filename, 'w') as f:
            f.write("# Authorized Users Export\n")
            f.write(f"# Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            for user_id, data in users.items():
                username = data.get("username", "Unknown")
                timestamp = data.get("timestamp", "N/A")
                f.write(f"# {username} - Authorized: {timestamp}\n")
                f.write(f"{user_id}\n")
        
        print(f"✅ Successfully exported {len(users)} user(s) to {filename}")
    except Exception as e:
        print(f"❌ Error exporting users: {e}")

def clear_all_authorized_users():
    """Clear all authorized users (with confirmation)."""
    print_header("Clear All Authorized Users")
    print("⚠️  WARNING: This will remove ALL authorized users!")
    confirm = input("Type 'YES' to confirm: ").strip()
    
    if confirm != "YES":
        print("❌ Operation cancelled.")
        return
    
    try:
        # Clear the authorized users file
        with open(AUTH_FILES["authorized_users"], 'w') as f:
            json.dump({}, f)
        print("✅ All authorized users have been cleared.")
    except Exception as e:
        print(f"❌ Error clearing users: {e}")

def main():
    """Main entry point."""
    while True:
        display_menu()
        choice = input("\nEnter your choice (1-8): ").strip()
        
        if choice == '1':
            list_auth_users()
        elif choice == '2':
            list_pending_users()
        elif choice == '3':
            authorize_user()
        elif choice == '4':
            deauthorize_user()
        elif choice == '5':
            import_users_from_file()
        elif choice == '6':
            export_authorized_users()
        elif choice == '7':
            clear_all_authorized_users()
        elif choice == '8':
            print("\n👋 Goodbye!")
            sys.exit(0)
        else:
            print("❌ Invalid choice. Please try again.")
        
        input("\nPress Enter to continue...")

if __name__ == "__main__":
    main()
