"""
Auth RestoreCord Configuration
All configuration variables for the auth restorecore application bot.
"""

import os

# =============================================================================
# DISCORD CREDENTIALS
# =============================================================================

# Discord User Token (required)
TOKEN = ""

# Discord Server/Guild ID
GUILD_ID = "1464067001256509452"

# Your Discord User ID
OWN_USER_ID = "1411325023053938730"

# Load from environment variables if not set
if not TOKEN:
    TOKEN = os.environ.get("DISCORD_TOKEN", "")

# Clean up the token
TOKEN = TOKEN.strip()
if TOKEN.startswith("Bot "):
    TOKEN = TOKEN[4:].strip()

# =============================================================================
# AUTHENTICATION CONFIGURATION
# =============================================================================

# Discord OAuth2 Configuration
BOT_CLIENT_ID = ""  # Your Discord application client ID
REDIRECT_URI = "https://discord.com/oauth2/authorized"  # OAuth2 redirect URI

if not BOT_CLIENT_ID:
    BOT_CLIENT_ID = os.environ.get("DISCORD_BOT_CLIENT_ID", "")

# Build OAuth2 authorization URL
if BOT_CLIENT_ID:
    AUTH_LINK = (
        f"https://discord.com/oauth2/authorize?"
        f"client_id={BOT_CLIENT_ID}"
        f"&scope=identify%20guilds.join"
        f"&response_type=code"
        f"&redirect_uri={REDIRECT_URI}"
    )
else:
    AUTH_LINK = "https://discord.com/oauth2/authorize?client_id=YOUR_CLIENT_ID&scope=identify%20guilds.join&response_type=code&redirect_uri=https://discord.com/oauth2/authorized"

# =============================================================================
# RESTORECORD INTEGRATION
# =============================================================================

# RestoreCord is a verification system for Discord servers
RESTORECORD_URL = ""  # e.g., "https://verify.yourserver.com"
RESTORECORD_API_KEY = ""  # API key with "Read everything" permission
RESTORECORD_SERVER_ID = ""  # Your RestoreCord server/guild ID

if not RESTORECORD_URL:
    RESTORECORD_URL = os.environ.get("RESTORECORD_URL", "")
if not RESTORECORD_API_KEY:
    RESTORECORD_API_KEY = os.environ.get("RESTORECORD_API_KEY", "")
if not RESTORECORD_SERVER_ID:
    RESTORECORD_SERVER_ID = os.environ.get("RESTORECORD_SERVER_ID", "")

# Enable RestoreCord if configured
USE_RESTORECORD = bool(RESTORECORD_URL and RESTORECORD_SERVER_ID)

# Update auth link if using RestoreCord
if USE_RESTORECORD:
    AUTH_LINK = f"{RESTORECORD_URL}?server={RESTORECORD_SERVER_ID}"

# Legacy/alternative auth options
TELEGRAM_LINK = "https://t.me/addlist/cS0b_-rSPsphZDVh"

# =============================================================================
# MESSAGE FORWARDING CONFIGURATION
# =============================================================================

# Secret server channel where template messages exist
FORWARD_SOURCE_CHANNEL_ID = ""  # e.g., "123456789012345678"

# Message IDs to forward for different scenarios
FORWARD_AUTH_MESSAGE_ID = ""  # e.g., "111111111111111111"

# Additional text sent along with forwarded messages
FORWARD_AUTH_ADDITIONAL_TEXT = ""      # e.g., "Please complete verification to join!"

# Load from environment variables
if not FORWARD_SOURCE_CHANNEL_ID:
    FORWARD_SOURCE_CHANNEL_ID = os.environ.get("FORWARD_SOURCE_CHANNEL_ID", "")
if not FORWARD_AUTH_MESSAGE_ID:
    FORWARD_AUTH_MESSAGE_ID = os.environ.get("FORWARD_AUTH_MESSAGE_ID", "")
if not FORWARD_AUTH_ADDITIONAL_TEXT:
    FORWARD_AUTH_ADDITIONAL_TEXT = os.environ.get("FORWARD_AUTH_ADDITIONAL_TEXT", "")

# Enable forwarding if source channel is set
USE_MESSAGE_FORWARDING = bool(FORWARD_SOURCE_CHANNEL_ID)

# =============================================================================
# SERVER INVITE LINK CONFIGURATION
# =============================================================================

# Server invite link to send to users after they are accepted
SERVER_INVITE_LINK = ""  # e.g., "https://discord.gg/example"

# Load from environment variable
if not SERVER_INVITE_LINK:
    SERVER_INVITE_LINK = os.environ.get("SERVER_INVITE_LINK", "")

# =============================================================================
# TIMING CONFIGURATION
# =============================================================================

# How long to wait for Discord to create channels/complete operations
CHANNEL_CREATION_WAIT = 2  # seconds

# How often to check for pending auth completions (lower = faster detection)
AUTH_CHECK_INTERVAL = 2  # seconds

# Default retry delay for rate limits
RETRY_AFTER_DEFAULT = 2  # seconds

# =============================================================================
# MESSAGE TEMPLATES
# =============================================================================

# These messages are used when NOT forwarding, or as fallback
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

# Post-acceptance message with server invite
if SERVER_INVITE_LINK:
    AUTH_SUCCESS_MESSAGE = (
        f"✅ **Authentication successful!** Make sure to join VC {SERVER_INVITE_LINK}"
    )
else:
    AUTH_SUCCESS_MESSAGE = (
        "✅ **Authentication successful!**"
    )

# =============================================================================
# FILE PATHS
# =============================================================================

# Storage files for auth system (auto-created)
AUTH_FILES = {
    "pending_auth": "pending_auth.json"
}

# =============================================================================
# COOKIES (for API requests)
# =============================================================================

COOKIES = {}
