#!/usr/bin/env python3
"""
Auth Manager CLI - Tool for managing pending auth requests

NOTE: This bot now uses RestoreCord API for authorization verification.
Authorized users are checked in real-time via RestoreCord API, not stored locally.
This tool only allows you to view pending auth requests.
"""
import json
import os
import sys
import time
from auth_handler import (
    get_pending_auth_users,
    check_restorecord_verification,
    USE_RESTORECORD,
    RESTORECORD_URL,
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
    print("1. List Pending Auth Users")
    print("2. Check User Verification Status (RestoreCord)")
    print("3. View RestoreCord Configuration")
    print("4. Exit")
    print("="*60)

def list_pending_users():
    """List all pending auth users."""
    print_header("Pending Auth Users")
    users = get_pending_auth_users()
    
    if not users:
        print("✅ No pending auth users found.")
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
        
        # Check current verification status
        if USE_RESTORECORD:
            is_verified = check_restorecord_verification(user_id)
            status = "✅ NOW VERIFIED" if is_verified else "⏳ Not yet verified"
            print(f"    Status: {status}")
        
        print()

def check_user_status():
    """Check if a specific user is verified on RestoreCord."""
    print_header("Check User Verification Status")
    
    if not USE_RESTORECORD:
        print("❌ RestoreCord is not configured!")
        print("   Please configure RestoreCord in config.py to use this feature.")
        return
    
    user_id = input("Enter User ID to check: ").strip()
    
    if not user_id:
        print("❌ User ID cannot be empty.")
        return
    
    print(f"\n🔍 Checking RestoreCord verification for user {user_id}...")
    
    try:
        is_verified = check_restorecord_verification(user_id)
        if is_verified:
            print(f"✅ User {user_id} IS verified on RestoreCord")
        else:
            print(f"❌ User {user_id} is NOT verified on RestoreCord")
    except Exception as e:
        print(f"❌ Error checking RestoreCord: {e}")

def view_restorecord_config():
    """View current RestoreCord configuration."""
    print_header("RestoreCord Configuration")
    
    if USE_RESTORECORD:
        print("✅ RestoreCord is ENABLED")
        print(f"   URL: {RESTORECORD_URL}")
        print("\nUsers are verified in real-time via RestoreCord API.")
        print("No local authorized users list is maintained.")
    else:
        print("❌ RestoreCord is NOT configured")
        print("\nTo enable RestoreCord:")
        print("1. Edit config.py")
        print("2. Set RESTORECORD_URL and RESTORECORD_SERVER_ID")
        print("3. Restart the bot")

def main():
    """Main entry point."""
    print("\n" + "="*60)
    print("  ⚠️  NOTE: Authorization via RestoreCord API")
    print("="*60)
    print("This bot now uses RestoreCord for real-time verification.")
    print("Users are NOT stored locally - they're checked via API.")
    print("="*60)
    
    while True:
        display_menu()
        choice = input("\nEnter your choice (1-4): ").strip()
        
        if choice == '1':
            list_pending_users()
        elif choice == '2':
            check_user_status()
        elif choice == '3':
            view_restorecord_config()
        elif choice == '4':
            print("\n👋 Goodbye!")
            sys.exit(0)
        else:
            print("❌ Invalid choice. Please try again.")
        
        input("\nPress Enter to continue...")

if __name__ == "__main__":
    main()
