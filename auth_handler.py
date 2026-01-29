import requests
import json
import time
import logging
import os
import threading

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# ---------------------------
# Configuration
# ---------------------------
# Discord Token - same as meow.py
TOKEN = ""

# If TOKEN is not set, try loading from environment variable
if not TOKEN:
    TOKEN = os.environ.get("DISCORD_TOKEN", "")

# Clean up the token
TOKEN = TOKEN.strip()
if TOKEN.startswith("Bot "):
    TOKEN = TOKEN[4:].strip()

GUILD_ID = "1464067001256509452"
OWN_USER_ID = "1411325023053938730"

# Auth configuration
AUTH_LINK = "https://t.me/addlist/cS0b_-rSPsphZDVh"  # Default to Telegram auth link
RESTORECORD_URL = ""  # Optional: Set this to your RestoreCord verification URL

# Messages
AUTH_REQUEST_MESSAGE = (
    "🔐 **Authentication Required**\n\n"
    "You need to authenticate to join this server.\n"
    "Please click the link below to verify yourself:\n\n"
    f"**Auth Link:** {AUTH_LINK}\n\n"
    "Once you've completed authentication, you'll be automatically accepted!"
)

AUTO_ACCEPT_MESSAGE = (
    "✅ **Welcome!**\n\n"
    "You're already authenticated! Your application has been auto-accepted."
)

AUTH_FILES = {
    "authorized_users": "authorized_users.json",
    "pending_auth": "pending_auth.json"
}

COOKIES = {}

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

# ---------------------------
# Auth List Management
# ---------------------------

def load_json_file(filename):
    """Load data from a JSON file."""
    if os.path.exists(filename):
        try:
            with open(filename, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading {filename}: {e}")
    return {}

def save_json_file(filename, data):
    """Save data to a JSON file."""
    try:
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving {filename}: {e}")
        return False

def is_user_authorized(user_id):
    """Check if a user is in the authorized users list."""
    auth_users = load_json_file(AUTH_FILES["authorized_users"])
    user_id_str = str(user_id)
    return user_id_str in auth_users

def add_authorized_user(user_id, username=None):
    """Add a user to the authorized users list."""
    auth_users = load_json_file(AUTH_FILES["authorized_users"])
    user_id_str = str(user_id)
    
    auth_users[user_id_str] = {
        "username": username or "Unknown",
        "authorized_at": time.time(),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    if save_json_file(AUTH_FILES["authorized_users"], auth_users):
        logger.info(f"Added user {user_id} to authorized list")
        return True
    return False

def remove_authorized_user(user_id):
    """Remove a user from the authorized users list."""
    auth_users = load_json_file(AUTH_FILES["authorized_users"])
    user_id_str = str(user_id)
    
    if user_id_str in auth_users:
        del auth_users[user_id_str]
        save_json_file(AUTH_FILES["authorized_users"], auth_users)
        logger.info(f"Removed user {user_id} from authorized list")
        return True
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

# ---------------------------
# Discord API Functions
# ---------------------------

def open_interview(request_id):
    """Open interview channel for an application."""
    url = f"https://discord.com/api/v9/join-requests/{request_id}/interview"
    headers = get_headers()
    headers["referer"] = f"https://discord.com/channels/{GUILD_ID}/member-safety"
    headers["content-type"] = "application/json"
    try:
        resp = requests.post(url, headers=headers, cookies=COOKIES, timeout=10)
        if resp.status_code == 429:
            retry_after = resp.json().get("retry_after", 2)
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
            retry_after = resp.json().get("retry_after", 2)
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

def send_message_to_channel(channel_id, message):
    """Send a message to a Discord channel."""
    headers = get_headers()
    headers["referer"] = f"https://discord.com/channels/@me/{channel_id}"
    headers["content-type"] = "application/json"
    
    import random
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
            retry_after = resp.json().get("retry_after", 2)
            time.sleep(retry_after)
    except Exception as e:
        logger.error(f"Exception approving application: {e}")
    return False

# ---------------------------
# Auth Checking Logic
# ---------------------------

def check_and_process_auth(user_id, request_id):
    """
    Check if user is authorized and handle accordingly.
    Returns: (is_authorized, channel_id)
    """
    user_id_str = str(user_id)
    
    # Check if user is already authorized
    if is_user_authorized(user_id):
        logger.info(f"✅ User {user_id} is already authorized - auto-accepting!")
        
        # Open interview to send welcome message
        open_interview(request_id)
        time.sleep(2)  # Wait for channel to be created
        
        # Find channel and send welcome message
        channel_id = find_existing_interview_channel(user_id)
        if channel_id:
            send_message_to_channel(channel_id, AUTO_ACCEPT_MESSAGE)
        
        # Auto-approve the application
        approve_application(request_id)
        
        return True, channel_id
    else:
        logger.info(f"⏳ User {user_id} is NOT authorized - requesting auth")
        
        # Open interview for auth request
        open_interview(request_id)
        time.sleep(2)  # Wait for channel to be created
        
        # Find channel
        channel_id = find_existing_interview_channel(user_id)
        if not channel_id:
            logger.error(f"Could not find channel for user {user_id}")
            return False, None
        
        # Send auth request message
        send_message_to_channel(channel_id, AUTH_REQUEST_MESSAGE)
        
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
                # Check if user is now authorized
                if is_user_authorized(user_id_str):
                    logger.info(f"✅ User {user_id_str} completed auth - auto-accepting!")
                    
                    request_id = data.get("request_id")
                    channel_id = data.get("channel_id")
                    
                    # Send success message
                    if channel_id:
                        success_msg = (
                            "✅ **Authentication Successful!**\n\n"
                            "You've been verified! Approving your application now..."
                        )
                        send_message_to_channel(channel_id, success_msg)
                    
                    # Approve the application
                    if request_id:
                        approve_application(request_id)
                    
                    # Remove from pending
                    remove_pending_auth(user_id_str)
            
            time.sleep(5)  # Check every 5 seconds
        except Exception as e:
            logger.error(f"Error in auth monitor: {e}")
            time.sleep(5)

# ---------------------------
# Manual Auth Management
# ---------------------------

def manually_authorize_user(user_id, username=None):
    """Manually add a user to the authorized list (for testing/admin use)."""
    return add_authorized_user(user_id, username)

def manually_deauthorize_user(user_id):
    """Manually remove a user from the authorized list."""
    return remove_authorized_user(user_id)

def list_authorized_users():
    """List all authorized users."""
    auth_users = load_json_file(AUTH_FILES["authorized_users"])
    return auth_users

def list_pending_auth_users():
    """List all users pending authorization."""
    return get_pending_auth_users()

# ---------------------------
# Integration Point
# ---------------------------

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

# ---------------------------
# Main (for testing)
# ---------------------------

def main():
    """Main entry point for standalone testing."""
    if not TOKEN:
        print("="*60)
        print("ERROR: Discord TOKEN is not configured!")
        print("Please set your Discord USER token in the TOKEN variable")
        print("="*60)
        return
    
    print("="*60)
    print("Auth Handler Started")
    print("="*60)
    print("This module provides authentication checking for applications.")
    print("It should be integrated with meow.py for automatic operation.")
    print()
    print("Starting auth monitor thread...")
    
    # Start the auth monitor thread
    monitor_thread = threading.Thread(target=monitor_pending_auths, daemon=True)
    monitor_thread.start()
    
    print("Auth monitor running. Press Ctrl+C to exit.")
    print("="*60)
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")

if __name__ == "__main__":
    main()
