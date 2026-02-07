#!/usr/bin/env python3
"""
Auth RestoreCord Main Application
Handles authentication for Discord server applications using RestoreCord verification.

This module consolidates:
- Core authentication logic (auth_handler.py)
- CLI management tool (auth_manager.py)
- Configuration testing (test_restorecord.py)
- Example usage (example_auth_usage.py)
"""

import requests
import json
import time
import logging
import os
import threading
import random
import sys

# Import configuration
try:
    from auth_restorecore_config import (
        TOKEN, GUILD_ID, OWN_USER_ID,
        BOT_CLIENT_ID, REDIRECT_URI, AUTH_LINK,
        RESTORECORD_URL, RESTORECORD_API_KEY, RESTORECORD_SERVER_ID,
        USE_RESTORECORD, TELEGRAM_LINK,
        FORWARD_SOURCE_CHANNEL_ID, FORWARD_AUTH_MESSAGE_ID,
        FORWARD_AUTH_ADDITIONAL_TEXT, USE_MESSAGE_FORWARDING,
        CHANNEL_CREATION_WAIT, AUTH_CHECK_INTERVAL, RETRY_AFTER_DEFAULT,
        AUTH_REQUEST_MESSAGE, AUTH_SUCCESS_MESSAGE,
        AUTH_FILES, COOKIES, SERVER_INVITE_LINK
    )
except ImportError:
    print("ERROR: auth_restorecore_config.py not found!")
    print("Please ensure auth_restorecore_config.py exists in the same directory.")
    sys.exit(1)

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# Thread lock for file operations
file_lock = threading.Lock()

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_headers():
    """Get headers with current TOKEN value for API requests."""
    return {
        "accept": "*/*",
        "accept-language": "en-US,en;q=0.9",
        "authorization": TOKEN,
        "origin": "https://discord.com",
        "sec-ch-ua": '"Google Chrome";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
        "x-context-properties": "eyJsb2NhdGlvbiI6ImNoYXRfaW5wdXQifQ==",
    }

# =============================================================================
# AUTH LIST MANAGEMENT
# =============================================================================

def load_json_file(filename):
    """Load data from a JSON file (thread-safe)."""
    with file_lock:
        if os.path.exists(filename):
            try:
                with open(filename, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading {filename}: {e}")
        return {}

def save_json_file(filename, data):
    """Save data to a JSON file (thread-safe with atomic write)."""
    with file_lock:
        try:
            # Write to temporary file first for atomic operation
            temp_filename = filename + '.tmp'
            with open(temp_filename, 'w') as f:
                json.dump(data, f, indent=2)
            # Atomic rename
            os.replace(temp_filename, filename)
            return True
        except Exception as e:
            logger.error(f"Error saving {filename}: {e}")
            return False

def is_user_authorized(user_id):
    """
    Check if a user is authorized/verified.
    Uses RestoreCord API polling to check verification status in real-time.
    No local file storage - always checks the authoritative source.
    """
    # If RestoreCord is enabled, check verification status via API
    if USE_RESTORECORD:
        is_verified = check_restorecord_verification(user_id)
        if is_verified:
            logger.info(f"✅ User {user_id} is verified on RestoreCord")
            return True
        else:
            logger.info(f"❌ User {user_id} is NOT verified on RestoreCord")
            return False
    else:
        # If RestoreCord is not configured, users are not authorized by default
        logger.warning("RestoreCord is not configured - cannot verify users")
        return False

def add_pending_auth(user_id, request_id, channel_id):
    """Add a user to the pending auth list."""
    pending = load_json_file(AUTH_FILES["pending_auth"])
    user_id_str = str(user_id)
    
    pending[user_id_str] = {
        "request_id": request_id,
        "channel_id": channel_id,
        "pending_since": time.time(),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    if save_json_file(AUTH_FILES["pending_auth"], pending):
        logger.info(f"Added user {user_id} to pending auth list")
        return True
    return False

def remove_pending_auth(user_id):
    """Remove a user from the pending auth list."""
    pending = load_json_file(AUTH_FILES["pending_auth"])
    user_id_str = str(user_id)
    
    if user_id_str in pending:
        data = pending[user_id_str]
        del pending[user_id_str]
        save_json_file(AUTH_FILES["pending_auth"], pending)
        logger.info(f"Removed user {user_id} from pending auth list")
        return data
    return None

def get_pending_auth_users():
    """Get all users pending authorization."""
    return load_json_file(AUTH_FILES["pending_auth"])

# =============================================================================
# RESTORECORD API FUNCTIONS
# =============================================================================

def check_restorecord_verification(user_id):
    """
    Check if a user is verified on RestoreCord.
    Returns True if verified, False otherwise.
    """
    if not USE_RESTORECORD:
        logger.warning("RestoreCord is not configured")
        return False
    
    try:
        # Build RestoreCord API endpoint
        api_url = f"{RESTORECORD_URL}/api/check"
        params = {
            "server": RESTORECORD_SERVER_ID,
            "user": str(user_id)
        }
        
        headers = {}
        if RESTORECORD_API_KEY:
            headers["Authorization"] = f"Bearer {RESTORECORD_API_KEY}"
        
        resp = requests.get(api_url, params=params, headers=headers, timeout=10)
        
        if resp.status_code == 200:
            data = resp.json()
            # Check common response patterns:
            if isinstance(data, dict):
                # Pattern 1: {"verified": true}
                if "verified" in data:
                    return data["verified"] == True
                # Pattern 2: {"status": "verified"}
                if "status" in data:
                    return data["status"] in ["verified", "approved"]
                # Pattern 3: {"member": {..., "verified": true}}
                if "member" in data and isinstance(data["member"], dict):
                    return data["member"].get("verified", False) == True
            
            logger.warning(f"Unexpected RestoreCord response format: {data}")
            return False
        elif resp.status_code == 404:
            # User not found = not verified
            logger.info(f"User {user_id} not found in RestoreCord (not verified)")
            return False
        else:
            logger.error(f"RestoreCord API error: {resp.status_code} - {resp.text}")
            return False
            
    except Exception as e:
        logger.error(f"Error checking RestoreCord verification: {e}")
        return False

# =============================================================================
# DISCORD API FUNCTIONS
# =============================================================================

def open_interview(request_id):
    """Open interview channel for an application."""
    url = f"https://discord.com/api/v9/join-requests/{request_id}/interview"
    headers = get_headers()
    headers["referer"] = f"https://discord.com/channels/{GUILD_ID}/member-safety"
    headers["content-type"] = "application/json"
    try:
        resp = requests.post(url, headers=headers, cookies=COOKIES, timeout=10)
        if resp.status_code == 429:
            retry_after = resp.json().get("retry_after", RETRY_AFTER_DEFAULT)
            time.sleep(retry_after)
        return resp.status_code in (200, 201)
    except Exception as e:
        logger.error(f"Error opening interview: {e}")
        return False

def find_existing_interview_channel(user_id):
    """Find the group DM channel for a user."""
    url = "https://discord.com/api/v9/users/@me/channels"
    headers = get_headers()
    headers.pop("content-type", None)
    try:
        resp = requests.get(url, headers=headers, cookies=COOKIES, timeout=10)
        if resp.status_code == 429:
            retry_after = resp.json().get("retry_after", RETRY_AFTER_DEFAULT)
            time.sleep(retry_after)
            return None
        channels = resp.json()
        if not isinstance(channels, list):
            return None
        for c in channels:
            if isinstance(c, dict) and c.get("type") == 3:
                recipient_ids = [u["id"] for u in c.get("recipients", [])]
                if str(user_id) in [str(r) for r in recipient_ids]:
                    return c["id"]
    except Exception as e:
        logger.error(f"Error finding channel: {e}")
    return None

def forward_message_to_channel(channel_id, source_channel_id, message_id, additional_text=""):
    """
    Forward a message from one channel to another.
    This uses Discord's native message forwarding API.
    """
    headers = get_headers()
    headers["referer"] = f"https://discord.com/channels/@me/{channel_id}"
    headers["content-type"] = "application/json"
    
    # Discord's forward message API payload
    data = {
        "message_reference": {
            "channel_id": str(source_channel_id),
            "message_id": str(message_id),
            "type": 1
        },
        "nonce": str(random.randint(10**17, 10**18-1)),
        "tts": False
    }
    
    # Add optional additional text if provided
    if additional_text:
        data["content"] = additional_text
    
    url = f"https://discord.com/api/v9/channels/{channel_id}/messages"
    
    try:
        resp = requests.post(url, headers=headers, cookies=COOKIES, data=json.dumps(data), timeout=10)
        if resp.status_code == 200 or resp.status_code == 201:
            if additional_text:
                logger.info(f"Forwarded message {message_id} with additional text to channel {channel_id}")
            else:
                logger.info(f"Forwarded message {message_id} to channel {channel_id}")
            return True
        elif resp.status_code == 429:
            retry_after = resp.json().get("retry_after", 10)
            logger.warning(f"Rate limited! Waiting {retry_after}s")
            time.sleep(retry_after)
        else:
            logger.warning(f"Failed to forward message. Status: {resp.status_code}, Response: {resp.text}")
    except Exception as e:
        logger.error(f"Exception forwarding message: {e}")
    return False

def send_message_to_channel(channel_id, message, message_type="default"):
    """
    Send a message to a Discord channel.
    If message forwarding is enabled and message_type is "auth_request",
    it will forward the pre-configured auth request message instead of sending new content.
    """
    # Check if we should forward instead of sending (only for auth_request)
    if USE_MESSAGE_FORWARDING and FORWARD_SOURCE_CHANNEL_ID and message_type == "auth_request":
        if FORWARD_AUTH_MESSAGE_ID:
            logger.info(f"Using message forwarding for {message_type} message")
            return forward_message_to_channel(channel_id, FORWARD_SOURCE_CHANNEL_ID, FORWARD_AUTH_MESSAGE_ID, FORWARD_AUTH_ADDITIONAL_TEXT)
        else:
            logger.info(f"No message ID configured for {message_type}, falling back to regular send")
    
    # Fallback to regular message sending
    headers = get_headers()
    headers["referer"] = f"https://discord.com/channels/@me/{channel_id}"
    headers["content-type"] = "application/json"
    
    data = {
        "content": message,
        "nonce": str(random.randint(10**17, 10**18-1)),
        "tts": False,
        "flags": 0
    }
    url = f"https://discord.com/api/v9/channels/{channel_id}/messages"
    
    try:
        resp = requests.post(url, headers=headers, cookies=COOKIES, data=json.dumps(data), timeout=10)
        if resp.status_code == 200 or resp.status_code == 201:
            logger.info(f"Sent message to channel {channel_id}")
            return True
        elif resp.status_code == 429:
            retry_after = resp.json().get("retry_after", 10)
            logger.warning(f"Rate limited! Waiting {retry_after}s")
            time.sleep(retry_after)
        else:
            logger.warning(f"Failed to send message. Status: {resp.status_code}")
    except Exception as e:
        logger.error(f"Exception sending message: {e}")
    return False

def approve_application(request_id):
    """Approve an application."""
    url = f"https://discord.com/api/v9/guilds/{GUILD_ID}/requests/id/{request_id}"
    headers = get_headers()
    headers["content-type"] = "application/json"
    headers["referer"] = f"https://discord.com/channels/{GUILD_ID}/member-safety"
    data = {"action": "APPROVED"}
    try:
        resp = requests.patch(url, headers=headers, cookies=COOKIES, data=json.dumps(data), timeout=10)
        if resp.status_code == 200:
            logger.info(f"✅ Approved application {request_id}")
            return True
        else:
            logger.warning(f"Failed to approve. Status: {resp.status_code}")
        if resp.status_code == 429:
            retry_after = resp.json().get("retry_after", RETRY_AFTER_DEFAULT)
            time.sleep(retry_after)
    except Exception as e:
        logger.error(f"Exception approving application: {e}")
    return False

def open_interview_and_send_message(request_id, user_id, message, message_type="default"):
    """
    Helper function to open interview, find channel, and send message.
    Reduces code duplication and improves maintainability.
    """
    # Open interview
    if not open_interview(request_id):
        logger.warning(f"Failed to open interview for request {request_id}")
        return None
    
    # Wait for channel creation
    time.sleep(CHANNEL_CREATION_WAIT)
    
    # Find channel
    channel_id = find_existing_interview_channel(user_id)
    if not channel_id:
        logger.error(f"Could not find channel for user {user_id}")
        return None
    
    # Send message
    send_message_to_channel(channel_id, message, message_type)
    
    return channel_id

# =============================================================================
# AUTH CHECKING LOGIC
# =============================================================================

def check_and_process_auth(user_id, request_id):
    """
    Check if user is authorized and handle accordingly.
    
    Already verified users are auto-approved immediately without any interview.
    Returns: (is_authorized, channel_id)
    """
    user_id_str = str(user_id)
    
    # Check if user is already authorized via RestoreCord API
    if is_user_authorized(user_id):
        logger.info(f"✅ User {user_id} is already verified - auto-approving WITHOUT opening interview!")
        
        # Do NOT open interview channel or send any messages
        # Just auto-approve immediately
        approve_application(request_id)
        
        return True, None
    else:
        logger.info(f"⏳ User {user_id} is NOT verified - requesting auth")
        
        # Use helper function to open interview and send auth request
        channel_id = open_interview_and_send_message(request_id, user_id, AUTH_REQUEST_MESSAGE, "auth_request")
        
        if not channel_id:
            logger.error(f"Could not process auth request for user {user_id}")
            return False, None
        
        # Add to pending auth list
        add_pending_auth(user_id, request_id, channel_id)
        
        return False, channel_id

def monitor_pending_auths():
    """Monitor pending auth users and auto-approve when they complete auth."""
    logger.info("🔍 Auth monitor thread started")
    
    while True:
        try:
            pending = get_pending_auth_users()
            
            for user_id_str, data in list(pending.items()):
                # Check if user is now authorized via RestoreCord API
                if is_user_authorized(user_id_str):
                    logger.info(f"✅ User {user_id_str} completed auth - auto-accepting!")
                    
                    request_id = data.get("request_id")
                    channel_id = data.get("channel_id")
                    
                    # Approve the application first
                    if request_id:
                        approve_application(request_id)
                    
                    # Send success message AFTER approval (not forwarded)
                    if channel_id:
                        send_message_to_channel(channel_id, AUTH_SUCCESS_MESSAGE, "default")
                    
                    # Remove from pending
                    remove_pending_auth(user_id_str)
            
            time.sleep(AUTH_CHECK_INTERVAL)  # Check every N seconds
        except Exception as e:
            logger.error(f"Error in auth monitor: {e}")
            time.sleep(AUTH_CHECK_INTERVAL)

def process_application_with_auth(user_id, request_id):
    """
    Main entry point for processing an application with auth checking.
    This should be called instead of the normal process_application.
    """
    logger.info(f"🔐 Processing application with auth check: user={user_id}, reqid={request_id}")
    
    is_authorized, channel_id = check_and_process_auth(user_id, request_id)
    
    if is_authorized:
        logger.info(f"✅ User {user_id} was auto-accepted (already authorized)")
    else:
        logger.info(f"⏳ User {user_id} needs to complete auth before acceptance")
    
    return is_authorized, channel_id

# =============================================================================
# CLI MANAGEMENT TOOL
# =============================================================================

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
    print("4. Test RestoreCord Configuration")
    print("5. Start Auth Monitor (Background)")
    print("6. Exit")
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
        print("   Please configure RestoreCord in auth_restorecore_config.py to use this feature.")
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
        print("1. Edit auth_restorecore_config.py")
        print("2. Set RESTORECORD_URL and RESTORECORD_SERVER_ID")
        print("3. Restart the bot")

def test_configuration():
    """Test RestoreCord configuration."""
    print_header("CONFIGURATION CHECK")
    
    # Check RestoreCord configuration
    print("\n📋 RestoreCord Configuration:")
    print(f"  URL: {RESTORECORD_URL or '❌ NOT SET'}")
    print(f"  Server ID: {RESTORECORD_SERVER_ID or '❌ NOT SET'}")
    print(f"  API Key: {'✅ SET' if RESTORECORD_API_KEY else '❌ NOT SET (may not be required)'}")
    print(f"  Enabled: {'✅ YES' if USE_RESTORECORD else '❌ NO'}")
    
    # Check Discord OAuth2 configuration
    print("\n🔐 Discord OAuth2 Configuration:")
    print(f"  Client ID: {BOT_CLIENT_ID or '❌ NOT SET'}")
    
    # Show active auth method
    print("\n🎯 Active Auth Method:")
    if USE_RESTORECORD:
        print("  ✅ RestoreCord Verification")
        print(f"  Auth Link: {AUTH_LINK}")
    elif BOT_CLIENT_ID:
        print("  ✅ Discord OAuth2 Bot Authorization")
        print(f"  Auth Link: {AUTH_LINK}")
    else:
        print("  ⚠️  No auth method configured!")
        print("  You need to set either:")
        print("    - RestoreCord: RESTORECORD_URL + RESTORECORD_SERVER_ID")
        print("    - Discord OAuth2: BOT_CLIENT_ID")
    
    # Test RestoreCord API if configured
    if USE_RESTORECORD:
        print("\n" + "="*60)
        print("  TESTING RESTORECORD CONNECTION")
        print("="*60)
        
        test_user = input("\nEnter a Discord User ID to test (or press Enter to skip): ").strip()
        
        if test_user:
            print(f"\n🔍 Checking if user {test_user} is verified on RestoreCord...")
            try:
                is_verified = check_restorecord_verification(test_user)
                if is_verified:
                    print(f"✅ User {test_user} IS verified on RestoreCord")
                else:
                    print(f"❌ User {test_user} is NOT verified on RestoreCord")
            except Exception as e:
                print(f"❌ Error testing RestoreCord: {e}")
        else:
            print("⏭️  Skipping API test")

def start_monitor():
    """Start the auth monitor thread."""
    print_header("Starting Auth Monitor")
    
    if not TOKEN:
        print("❌ Discord TOKEN is not configured!")
        print("Please set your Discord USER token in auth_restorecore_config.py")
        return
    
    print("Starting auth monitor thread...")
    
    # Start the auth monitor thread
    monitor_thread = threading.Thread(target=monitor_pending_auths, daemon=True)
    monitor_thread.start()
    
    print("✅ Auth monitor running in background.")
    print("⏳ Press Ctrl+C to stop.")
    print("="*60)
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n⏹️  Stopping auth monitor...")

def run_cli():
    """Run the CLI management interface."""
    print("\n" + "="*60)
    print("  ⚠️  NOTE: Authorization via RestoreCord API")
    print("="*60)
    print("This bot uses RestoreCord for real-time verification.")
    print("Users are NOT stored locally - they're checked via API.")
    print("="*60)
    
    while True:
        display_menu()
        choice = input("\nEnter your choice (1-6): ").strip()
        
        if choice == '1':
            list_pending_users()
        elif choice == '2':
            check_user_status()
        elif choice == '3':
            view_restorecord_config()
        elif choice == '4':
            test_configuration()
        elif choice == '5':
            start_monitor()
        elif choice == '6':
            print("\n👋 Goodbye!")
            sys.exit(0)
        else:
            print("❌ Invalid choice. Please try again.")
        
        input("\nPress Enter to continue...")

# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Auth RestoreCord Application Bot',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s                    # Run CLI interface
  %(prog)s --monitor          # Start auth monitor
  %(prog)s --test             # Test configuration
  %(prog)s --check-user ID    # Check user verification status
        '''
    )
    
    parser.add_argument('--monitor', action='store_true',
                       help='Start the auth monitor thread')
    parser.add_argument('--test', action='store_true',
                       help='Test RestoreCord configuration')
    parser.add_argument('--check-user', metavar='USER_ID',
                       help='Check if a user is verified on RestoreCord')
    parser.add_argument('--list-pending', action='store_true',
                       help='List all pending auth users')
    
    args = parser.parse_args()
    
    # Handle command line arguments
    if args.monitor:
        start_monitor()
    elif args.test:
        test_configuration()
    elif args.check_user:
        print(f"🔍 Checking RestoreCord verification for user {args.check_user}...")
        is_verified = check_restorecord_verification(args.check_user)
        if is_verified:
            print(f"✅ User {args.check_user} IS verified on RestoreCord")
        else:
            print(f"❌ User {args.check_user} is NOT verified on RestoreCord")
    elif args.list_pending:
        list_pending_users()
    else:
        # No arguments provided, run CLI
        run_cli()

if __name__ == "__main__":
    main()
