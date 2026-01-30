import requests
import json
import time
import logging
import os
import threading
import random

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

# Auth configuration - Discord OAuth2
# You need to create a Discord application and get the client ID
# Visit: https://discord.com/developers/applications
BOT_CLIENT_ID = ""  # Set your Discord application client ID here
REDIRECT_URI = "https://discord.com/oauth2/authorized"  # Your OAuth2 redirect URI

# If BOT_CLIENT_ID is not set, try loading from environment variable
if not BOT_CLIENT_ID:
    BOT_CLIENT_ID = os.environ.get("DISCORD_BOT_CLIENT_ID", "")

# Build Discord OAuth2 authorization URL
# This allows users to authorize the bot which can then add them to the server
if BOT_CLIENT_ID:
    AUTH_LINK = (
        f"https://discord.com/oauth2/authorize?"
        f"client_id={BOT_CLIENT_ID}"
        f"&scope=identify%20guilds.join"
        f"&response_type=code"
        f"&redirect_uri={REDIRECT_URI}"
    )
else:
    # Fallback to a placeholder if no client ID is configured
    AUTH_LINK = "https://discord.com/oauth2/authorize?client_id=YOUR_CLIENT_ID&scope=identify%20guilds.join&response_type=code&redirect_uri=https://discord.com/oauth2/authorized"

# ---------------------------
# RestoreCord Configuration
# ---------------------------
# RestoreCord is a verification system for Discord servers
# To use RestoreCord integration:
# 1. Set RESTORECORD_URL to your RestoreCord instance URL
# 2. Set RESTORECORD_API_KEY with "Read everything" (data access) permission
#    - This allows the bot to check who's verified
#    - The bot will handle adding users to Discord (not RestoreCord)
# 3. Set RESTORECORD_SERVER_ID to your Discord server/guild ID

RESTORECORD_URL = ""  # e.g., "https://verify.yourserver.com" or "https://restorecord.com/verify"
RESTORECORD_API_KEY = ""  # Your RestoreCord API key with "Read everything" permission
RESTORECORD_SERVER_ID = ""  # Your RestoreCord server/guild ID

# If not set above, try loading from environment variables
if not RESTORECORD_URL:
    RESTORECORD_URL = os.environ.get("RESTORECORD_URL", "")
if not RESTORECORD_API_KEY:
    RESTORECORD_API_KEY = os.environ.get("RESTORECORD_API_KEY", "")
if not RESTORECORD_SERVER_ID:
    RESTORECORD_SERVER_ID = os.environ.get("RESTORECORD_SERVER_ID", "")

# Use RestoreCord as auth method?
USE_RESTORECORD = bool(RESTORECORD_URL and RESTORECORD_SERVER_ID)

# If using RestoreCord, update the auth link
if USE_RESTORECORD:
    AUTH_LINK = f"{RESTORECORD_URL}?server={RESTORECORD_SERVER_ID}"

# Legacy/alternative auth options
TELEGRAM_LINK = "https://t.me/addlist/cS0b_-rSPsphZDVh"  # Optional: Telegram group

# ---------------------------
# Message Forwarding Configuration
# ---------------------------
# Instead of sending new messages, the bot can forward pre-existing messages from a "secret server"
# This is useful if you want to forward templated messages that are already formatted
# Set these to enable message forwarding:
FORWARD_SOURCE_CHANNEL_ID = ""  # Channel ID where the template messages exist
FORWARD_AUTH_MESSAGE_ID = ""    # Message ID to forward for auth requests
FORWARD_WELCOME_MESSAGE_ID = ""  # Message ID to forward for welcome/auto-accept messages
FORWARD_SUCCESS_MESSAGE_ID = ""  # Message ID to forward for auth success messages

# If not set above, try loading from environment variables
if not FORWARD_SOURCE_CHANNEL_ID:
    FORWARD_SOURCE_CHANNEL_ID = os.environ.get("FORWARD_SOURCE_CHANNEL_ID", "")
if not FORWARD_AUTH_MESSAGE_ID:
    FORWARD_AUTH_MESSAGE_ID = os.environ.get("FORWARD_AUTH_MESSAGE_ID", "")
if not FORWARD_WELCOME_MESSAGE_ID:
    FORWARD_WELCOME_MESSAGE_ID = os.environ.get("FORWARD_WELCOME_MESSAGE_ID", "")
if not FORWARD_SUCCESS_MESSAGE_ID:
    FORWARD_SUCCESS_MESSAGE_ID = os.environ.get("FORWARD_SUCCESS_MESSAGE_ID", "")

# Enable message forwarding if source channel is configured
USE_MESSAGE_FORWARDING = bool(FORWARD_SOURCE_CHANNEL_ID)

# Timing constants
CHANNEL_CREATION_WAIT = 2  # Seconds to wait for Discord to create channel
AUTH_CHECK_INTERVAL = 2  # Seconds between pending auth checks (faster = more real-time detection)
RETRY_AFTER_DEFAULT = 2  # Default retry delay for rate limits

# Messages - dynamically generated based on auth method
if USE_RESTORECORD:
    AUTH_REQUEST_MESSAGE = (
        "🔐 **RestoreCord Verification Required**\n\n"
        "To join this server, you need to verify through RestoreCord.\n\n"
        "**How it works:**\n"
        "1. Click the verification link below\n"
        "2. Complete the verification process on RestoreCord\n"
        "3. Once verified, you'll be **automatically accepted within 2-3 seconds!** ⚡\n\n"
        f"**Verification Link:** {AUTH_LINK}\n\n"
        "**Note:** After you verify on RestoreCord, our bot will detect it almost instantly "
        "(within 2-3 seconds) and automatically approve your application. Just wait a moment! "
        "RestoreCord helps us maintain a safe community.\n\n"
        "Complete the verification to get in! 🚀"
    )
else:
    AUTH_REQUEST_MESSAGE = (
        "🔐 **Discord Bot Authorization Required**\n\n"
        "To join this server, you need to authorize our Discord bot.\n\n"
        "**How it works:**\n"
        "1. Click the authorization link below\n"
        "2. Review and accept the bot permissions\n"
        "3. Once authorized, you'll be **automatically accepted within 2-3 seconds!** ⚡\n\n"
        f"**Authorization Link:** {AUTH_LINK}\n\n"
        "**Note:** By authorizing, you allow our bot to add you to Discord servers. "
        "This is a standard Discord OAuth2 flow and is completely safe. "
        "After authorization, the bot will detect it almost instantly!\n\n"
        "Once you've authorized the bot, you'll be automatically accepted to the server!"
    )

AUTO_ACCEPT_MESSAGE = (
    "✅ **Welcome!**\n\n"
    "You're already verified on RestoreCord!\n"
    "Your application has been auto-accepted.\n\n"
    "Welcome to the server! 🎉"
)

AUTH_FILES = {
    "authorized_users": "authorized_users.json",
    "pending_auth": "pending_auth.json"
}

COOKIES = {}

# Thread lock for file operations
file_lock = threading.Lock()

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
    Check if a user is in the authorized users list.
    If RestoreCord is enabled, also check RestoreCord verification status.
    """
    auth_users = load_json_file(AUTH_FILES["authorized_users"])
    user_id_str = str(user_id)
    
    # Check local authorized list first
    if user_id_str in auth_users:
        return True
    
    # If RestoreCord is enabled, check verification status
    if USE_RESTORECORD:
        is_verified = check_restorecord_verification(user_id)
        if is_verified:
            # Auto-add to local list for faster future checks
            add_authorized_user(user_id, "RestoreCord_Verified")
            logger.info(f"✅ User {user_id} verified on RestoreCord - auto-authorizing")
            return True
    
    return False

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
# RestoreCord API Functions
# ---------------------------

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
        # Different RestoreCord instances may have different API endpoints
        # Common patterns:
        # - https://restorecord.com/api/check?server=SERVER_ID&user=USER_ID
        # - https://your-instance.com/api/verified?guild=GUILD_ID&user=USER_ID
        
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
            # Different RestoreCord instances may return different response formats
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

def sync_restorecord_users():
    """
    Sync verified users from RestoreCord to local authorized users list.
    This can be called periodically to auto-add verified users.
    """
    if not USE_RESTORECORD:
        return
    
    try:
        # Get all verified users from RestoreCord
        api_url = f"{RESTORECORD_URL}/api/members"
        params = {"server": RESTORECORD_SERVER_ID}
        
        headers = {}
        if RESTORECORD_API_KEY:
            headers["Authorization"] = f"Bearer {RESTORECORD_API_KEY}"
        
        resp = requests.get(api_url, params=params, headers=headers, timeout=30)
        
        if resp.status_code == 200:
            data = resp.json()
            verified_users = []
            
            # Parse response based on common formats
            if isinstance(data, list):
                verified_users = [str(user.get("user_id") or user.get("id")) for user in data]
            elif isinstance(data, dict) and "members" in data:
                verified_users = [str(user.get("user_id") or user.get("id")) for user in data["members"]]
            
            # Add to authorized list
            count = 0
            for user_id in verified_users:
                if user_id and not is_user_authorized(user_id):
                    if add_authorized_user(user_id, "RestoreCord_Verified"):
                        count += 1
            
            if count > 0:
                logger.info(f"Synced {count} verified users from RestoreCord")
        else:
            logger.error(f"Failed to sync RestoreCord users: {resp.status_code}")
            
    except Exception as e:
        logger.error(f"Error syncing RestoreCord users: {e}")

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

def forward_message_to_channel(channel_id, source_channel_id, message_id):
    """
    Forward a message from one channel to another.
    This uses Discord's native message forwarding API.
    
    Args:
        channel_id: Destination channel ID
        source_channel_id: Source channel ID where the message exists
        message_id: ID of the message to forward
    
    Returns:
        bool: True if successful, False otherwise
    """
    headers = get_headers()
    headers["referer"] = f"https://discord.com/channels/@me/{channel_id}"
    headers["content-type"] = "application/json"
    
    # Discord's forward message API payload
    # Type 1 = FORWARD (creates point-in-time snapshot of the message)
    # Type 0 = DEFAULT (standard reply/reference)
    data = {
        "message_reference": {
            "channel_id": str(source_channel_id),
            "message_id": str(message_id),
            "type": 1
        },
        "nonce": str(random.randint(10**17, 10**18-1)),
        "tts": False
    }
    
    url = f"https://discord.com/api/v9/channels/{channel_id}/messages"
    
    try:
        resp = requests.post(url, headers=headers, cookies=COOKIES, data=json.dumps(data), timeout=10)
        if resp.status_code == 200 or resp.status_code == 201:
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
    If message forwarding is enabled and a message ID is configured for the message type,
    it will forward the pre-configured message instead of sending new content.
    
    Args:
        channel_id: Destination channel ID
        message: Message content to send (used if forwarding is disabled)
        message_type: Type of message - "auth_request", "welcome", "auth_success", or "default"
    
    Returns:
        bool: True if successful, False otherwise
    """
    # Check if we should forward instead of sending
    if USE_MESSAGE_FORWARDING and FORWARD_SOURCE_CHANNEL_ID:
        message_id = None
        
        # Determine which message to forward based on type
        if message_type == "auth_request" and FORWARD_AUTH_MESSAGE_ID:
            message_id = FORWARD_AUTH_MESSAGE_ID
        elif message_type == "welcome" and FORWARD_WELCOME_MESSAGE_ID:
            message_id = FORWARD_WELCOME_MESSAGE_ID
        elif message_type == "auth_success" and FORWARD_SUCCESS_MESSAGE_ID:
            message_id = FORWARD_SUCCESS_MESSAGE_ID
        
        # If we have a message ID configured, forward it
        if message_id:
            logger.info(f"Using message forwarding for {message_type} message")
            return forward_message_to_channel(channel_id, FORWARD_SOURCE_CHANNEL_ID, message_id)
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

# ---------------------------
# Helper Functions
# ---------------------------

def open_interview_and_send_message(request_id, user_id, message, message_type="default"):
    """
    Helper function to open interview, find channel, and send message.
    Reduces code duplication and improves maintainability.
    
    Args:
        request_id: Application request ID
        user_id: User ID to send message to
        message: Message content to send
        message_type: Type of message for forwarding ("auth_request", "welcome", "auth_success", or "default")
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
        
        # Use helper function to open interview and send welcome message
        channel_id = open_interview_and_send_message(request_id, user_id, AUTO_ACCEPT_MESSAGE, "welcome")
        
        # Auto-approve the application
        approve_application(request_id)
        
        return True, channel_id
    else:
        logger.info(f"⏳ User {user_id} is NOT authorized - requesting auth")
        
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
                        send_message_to_channel(channel_id, success_msg, "auth_success")
                    
                    # Approve the application
                    if request_id:
                        approve_application(request_id)
                    
                    # Remove from pending
                    remove_pending_auth(user_id_str)
            
            time.sleep(AUTH_CHECK_INTERVAL)  # Check every N seconds
        except Exception as e:
            logger.error(f"Error in auth monitor: {e}")
            time.sleep(AUTH_CHECK_INTERVAL)

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
