import discord
from discord.ext import commands, tasks
import requests
import json
import time
import random
import asyncio
import logging
import os
import sys
from datetime import datetime, timezone

# Global session for connection pooling (for hybrid REST calls where we still need them)
session = requests.Session()

# Global rate limit tracker (for hybrid REST calls)
_global_rate_limit_until = 0.0
_global_rate_limit_lock = asyncio.Lock()

# ---------------------------
# Configuration / constants
# ---------------------------
# PASTE YOUR DISCORD USER TOKEN HERE (between the quotes):
# WARNING: Do NOT commit your token to version control! Keep it secret!
# NOTE: This bot requires a USER token, not a bot token!
TOKEN = ""

# If TOKEN is not set above, try loading from environment variable
if not TOKEN:
    TOKEN = os.environ.get("DISCORD_TOKEN", "")

# Clean up the token: strip whitespace and remove "Bot " prefix if accidentally added
# USER tokens should NEVER have "Bot " prefix - only bot tokens use that
TOKEN = TOKEN.strip()
if TOKEN.startswith("Bot "):
    # Remove "Bot " prefix if user accidentally added it
    TOKEN = TOKEN[4:].strip()

GUILD_ID = "1464067001256509452"
OWN_USER_ID = "1411325023053938730"
OWN_USER_ID_STR = str(OWN_USER_ID)  # Pre-convert for efficient string comparisons

# Server invite link to send to the 2 users after approval
# For security, consider using environment variables instead: os.environ.get("SERVER_INVITE_LINK", "")
SERVER_INVITE_LINK = "https://discord.gg/xWG3ETgs"  # Set this to your Discord server invite link (e.g., "https://discord.gg/example")

# Your current message content / followup text (kept as you asked)
MESSAGE_CONTENT = ("YOU MUST join the tele network https://t.me/addlist/2tSHTebaXgVhOTRh and it will insta accept you,\n"
                   "-# SEND A SCREENSHOT OF YOU IN THE [TELEGRAM](https://t.me/addlist/2tSHTebaXgVhOTRh) TO BE ACCEPTED")

FOLLOW_UP_DELAY = 60  # seconds
FOLLOW_UP_MESSAGE = ("-# Please upload the screenshot of you in the [Telegram channel](https://t.me/addlist/2tSHTebaXgVhOTRh) so we can approve you.\n"
                     "-# If you've already uploaded it, give it a moment to appear.")

# NEW: special reminder message when a user posts an image but hasn't added 2 people to the group DM yet
ADD_TWO_PEOPLE_MESSAGE = ("-# Please also add 2 people to this group DM so we can accept you.\n"
                          "-# uploading a screenshot alone isn't enough. If you've already added them, give it a moment to appear.")

COOKIES = {
    # ...your cookies here...
}

def get_headers():
    """Get headers with current TOKEN value for API requests."""
    # USER tokens should be used directly without "Bot " prefix
    # Only bot tokens need the "Bot " prefix, but this bot uses USER tokens
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
        "user-agent": "Mozilla/5.0",
        "x-context-properties": "eyJsb2NhdGlvbiI6ImNoYXRfaW5wdXQifQ==",
    }

# Configuration
APPLICATION_CHECK_INTERVAL = 30.0  # Check for new applications periodically (backup to events)
SEND_RETRY_DELAY = 1
MAX_TOTAL_SEND_TIME = 180

# Channel finding configuration
CHANNEL_FIND_TIMEOUT = 30

# Follow-up message timing
FOLLOW_UP_DELAY = 60  # Send follow-up reminder after 60 seconds if no screenshot uploaded

# Startup handling
STARTUP_BATCH_SIZE = 5
STARTUP_BATCH_DELAY = 2.0
MAX_STARTUP_APPS = 500

# in-memory state (no threading locks needed with asyncio)
seen_reqs = set()
open_interviews = {}

# Track which users we've sent the "add 2 people" reminder to
add_two_people_reminded = set()

# Track follow-up tasks
follow_up_tasks = {}

# Track user photo status
user_has_photo = {}

# Logging
VERBOSE = False
logger = logging.getLogger("discord_auto_accept")
logger.setLevel(logging.DEBUG if VERBOSE else logging.INFO)
ch = logging.StreamHandler()
ch.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logger.addHandler(ch)

# Initialize Discord bot with necessary intents
intents = discord.Intents.default()
intents.guilds = True
intents.guild_messages = True
intents.dm_messages = True
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Helpers
def make_nonce():
    return str(random.randint(10**17, 10**18 - 1))

async def check_global_rate_limit():
    """Check if we're globally rate limited and sleep if needed."""
    global _global_rate_limit_until
    async with _global_rate_limit_lock:
        now = time.time()
        if now < _global_rate_limit_until:
            wait_time = _global_rate_limit_until - now
            logger.warning("Global rate limit active, waiting %.1fs", wait_time)
            await asyncio.sleep(wait_time)

async def set_global_rate_limit(retry_after):
    """Set global rate limit based on retry_after seconds."""
    global _global_rate_limit_until
    async with _global_rate_limit_lock:
        _global_rate_limit_until = time.time() + retry_after
        logger.warning("Set global rate limit for %.1fs", retry_after)

def iso_to_epoch(ts_str):
    if not ts_str:
        return 0.0
    try:
        dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp()
    except Exception:
        try:
            from datetime import datetime as _dt
            dt = _dt.strptime(ts_str.split(".")[0], "%Y-%m-%dT%H:%M:%S")
            return dt.replace(tzinfo=timezone.utc).timestamp()
        except Exception:
            return 0.0

def _log_resp_short(prefix, resp):
    try:
        if resp is None:
            logger.debug("%s: no response", prefix)
            return
        if VERBOSE:
            logger.debug("%s: status=%s text=%s", prefix, getattr(resp, "status_code", "N/A"), getattr(resp, "text", ""))
        else:
            logger.debug("%s: status=%s", prefix, getattr(resp, "status_code", "N/A"))
    except Exception:
        logger.exception("Error while logging response")

# API calls
async def get_pending_applications():
    """
    Fetch all pending applications from Discord API with pagination.
    Handles rate limiting with exponential backoff.
    """
    await check_global_rate_limit()  # Respect global rate limit
    
    all_apps = []
    after = None
    page_count = 0
    
    while True:
        # Build URL with pagination
        url = f"https://discord.com/api/v9/guilds/{GUILD_ID}/requests?status=SUBMITTED&limit=100"
        if after:
            url += f"&after={after}"
        
        headers = get_headers()
        headers["referer"] = f"https://discord.com/channels/{GUILD_ID}/member-safety"
        
        try:
            # Use asyncio to run requests in executor to not block event loop
            loop = asyncio.get_event_loop()
            resp = await loop.run_in_executor(None, lambda: session.get(url, headers=headers, cookies=COOKIES, timeout=10))
            _log_resp_short(f"get_pending_applications (page {page_count + 1})", resp)
            
            # Handle rate limiting with exponential backoff
            if resp and resp.status_code == 429:
                try:
                    data = resp.json()
                    retry_after = float(data.get("retry_after", 5))
                except Exception:
                    retry_after = 5.0
                await set_global_rate_limit(retry_after)  # Set global rate limit
                logger.warning("Rate limited fetching applications page %d, waiting %.1fs before retry", 
                              page_count + 1, retry_after)
                await asyncio.sleep(retry_after)
                continue  # Retry this page
            
            if not resp or resp.status_code != 200:
                logger.warning("Failed to fetch applications page %d, status=%s", page_count + 1, getattr(resp, "status_code", "N/A"))
                break
            
            data = resp.json() if resp else {}
            if not isinstance(data, dict):
                break
            
            apps = data.get("guild_join_requests", [])
            if not apps:
                # No more applications to fetch
                break
            
            all_apps.extend(apps)
            page_count += 1
            
            # Check if there are more pages
            # Discord pagination uses "after" cursor from the last item's ID
            if len(apps) < 100:
                # Last page (partial page)
                break
            
            # Get the ID of the last application for pagination
            last_app = apps[-1]
            after = last_app.get("id")
            if not after:
                break
            
            logger.info("📄 Fetched page %d with %d applications (total so far: %d)", page_count, len(apps), len(all_apps))
            
            # Delay between pages to avoid rate limiting
            await asyncio.sleep(0.5)  # Increased from 0.2s to reduce rate limit risk
            
        except Exception:
            logger.exception("Exception fetching pending applications (page %d)", page_count + 1)
            break
    
    if page_count > 0:
        logger.info("✅ Fetched %d total applications across %d pages", len(all_apps), page_count)
    
    return all_apps

async def open_interview(request_id):
    await check_global_rate_limit()  # Respect global rate limit
    url = f"https://discord.com/api/v9/join-requests/{request_id}/interview"
    headers = get_headers()
    headers["referer"] = f"https://discord.com/channels/{GUILD_ID}/member-safety"
    headers["content-type"] = "application/json"
    try:
        loop = asyncio.get_event_loop()
        resp = await loop.run_in_executor(None, lambda: session.post(url, headers=headers, cookies=COOKIES, timeout=5))
        _log_resp_short(f"open_interview {request_id}", resp)
        if resp and resp.status_code == 429:
            try:
                data = resp.json()
                retry_after = float(data.get("retry_after", 2))
                await set_global_rate_limit(retry_after)
            except Exception:
                pass
        logger.info("Opened interview for request %s (status=%s)", request_id, getattr(resp, "status_code", "N/A"))
    except Exception:
        logger.exception("Exception opening interview")

async def find_existing_interview_channel(user_id):
    await check_global_rate_limit()  # Respect global rate limit
    url = "https://discord.com/api/v9/users/@me/channels"
    headers = get_headers()
    headers.pop("content-type", None)
    try:
        loop = asyncio.get_event_loop()
        resp = await loop.run_in_executor(None, lambda: session.get(url, headers=headers, cookies=COOKIES, timeout=5))
        _log_resp_short("find_existing_interview_channel", resp)
        if resp and resp.status_code == 429:
            try:
                data = resp.json()
                retry_after = float(data.get("retry_after", 2))
                await set_global_rate_limit(retry_after)
            except Exception:
                pass
        channels = resp.json() if resp and resp.status_code == 200 else []
        matches = []
        if isinstance(channels, list):
            for c in channels:
                if isinstance(c, dict) and c.get("type") == 3:
                    recipient_ids = [u.get("id") for u in c.get("recipients", []) if isinstance(u, dict) and "id" in u]
                    if str(user_id) in [str(r) for r in recipient_ids]:
                        matches.append(c)
        if not matches:
            return None
        # prefer newest by snowflake numeric id
        def id_key(ch):
            try:
                return int(ch.get("id") or 0)
            except Exception:
                return 0
        best = max(matches, key=id_key)
        return best.get("id")
    except Exception:
        logger.exception("Exception finding interview channel")
        return None

async def get_channel_recipients(channel_id):
    """Get the list of recipient user IDs in a group DM channel. Handles rate limits with retry."""
    await check_global_rate_limit()  # Respect global rate limit
    url = f"https://discord.com/api/v9/channels/{channel_id}"
    headers = get_headers()
    headers["referer"] = f"https://discord.com/channels/@me/{channel_id}"
    headers.pop("content-type", None)
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            loop = asyncio.get_event_loop()
            resp = await loop.run_in_executor(None, lambda: session.get(url, headers=headers, cookies=COOKIES, timeout=10))
            _log_resp_short("get_channel_recipients", resp)
            
            # Handle rate limiting with retry
            if resp and resp.status_code == 429:
                try:
                    data = resp.json()
                    retry = float(data.get("retry_after", 2))
                except Exception:
                    retry = 2.0
                await set_global_rate_limit(retry)  # Set global rate limit
                logger.warning("Rate limited getting recipients for channel %s, retrying in %.1fs (attempt %d/%d)", 
                              channel_id, retry, attempt + 1, max_retries)
                await asyncio.sleep(retry)
                continue
            
            if resp and resp.status_code == 200:
                channel_data = resp.json()
                recipients = channel_data.get("recipients", [])
                recipient_ids = [u.get("id") for u in recipients if isinstance(u, dict) and "id" in u]
                return recipient_ids
            
            logger.warning("Failed to get recipients from channel %s: status=%s (attempt %d/%d)", 
                          channel_id, getattr(resp, "status_code", "N/A"), attempt + 1, max_retries)
            if attempt < max_retries - 1:
                await asyncio.sleep(0.5)
                continue
            return []
            
        except Exception:
            logger.exception("Exception getting channel recipients (attempt %d/%d)", attempt + 1, max_retries)
            if attempt < max_retries - 1:
                await asyncio.sleep(1.0)
                continue
            return []
    
    return []

async def check_two_people_added(channel_id, applicant_user_id):
    """
    Check if the applicant has added 2 people to the group DM.
    Returns (bool, list of added user IDs excluding bot and applicant).
    """
    recipients = await get_channel_recipients(channel_id)
    if not recipients:
        return False, []
    
    # Convert applicant ID to string once for efficient comparison
    applicant_id_str = str(applicant_user_id)
    
    # Filter out the bot and the applicant
    added_users = [
        uid for uid in recipients 
        if str(uid) != OWN_USER_ID_STR and str(uid) != applicant_id_str
    ]
    
    # Need at least 2 people added
    has_two_people = len(added_users) >= 2
    return has_two_people, added_users


async def message_already_sent(channel_id, content_without_mention, mention_user_id=None, min_ts=0.0):
    await check_global_rate_limit()  # Respect global rate limit
    url = f"https://discord.com/api/v9/channels/{channel_id}/messages?limit=50"
    headers = get_headers()
    headers["referer"] = f"https://discord.com/channels/@me/{channel_id}"
    headers.pop("content-type", None)
    try:
        loop = asyncio.get_event_loop()
        resp = await loop.run_in_executor(None, lambda: session.get(url, headers=headers, cookies=COOKIES, timeout=10))
        _log_resp_short("message_already_sent", resp)
        if resp and resp.status_code == 429:
            try:
                data = resp.json()
                retry_after = float(data.get("retry_after", 2))
                await set_global_rate_limit(retry_after)
            except Exception:
                pass
        messages = resp.json() if resp and resp.status_code == 200 else []
        if not isinstance(messages, list):
            return False
        for m in messages:
            msg_ts = iso_to_epoch(m.get("timestamp") or m.get("edited_timestamp"))
            if msg_ts < min_ts:
                continue
            if str(m.get("author", {}).get("id")) != str(OWN_USER_ID):
                continue
            msg_content = m.get("content", "") or ""
            if mention_user_id:
                mentions = m.get("mentions", []) or []
                mentioned_ids = {str(u.get("id")) for u in mentions if isinstance(u, dict) and "id" in u}
                if str(mention_user_id) not in mentioned_ids:
                    continue
            if content_without_mention in msg_content:
                return True
        return False
    except Exception:
        logger.exception("Exception in message_already_sent")
        return False

async def find_own_message_timestamp(channel_id, content_without_mention, mention_user_id=None):
    """
    Return the newest epoch timestamp of the most recent message in the channel
    authored by OWN_USER_ID that contains content_without_mention and (if provided)
    mentions mention_user_id. Returns 0.0 if not found.
    """
    await check_global_rate_limit()  # Respect global rate limit
    url = f"https://discord.com/api/v9/channels/{channel_id}/messages?limit=100"
    headers = get_headers()
    headers["referer"] = f"https://discord.com/channels/@me/{channel_id}"
    headers.pop("content-type", None)
    try:
        loop = asyncio.get_event_loop()
        resp = await loop.run_in_executor(None, lambda: session.get(url, headers=headers, cookies=COOKIES, timeout=10))
        _log_resp_short("find_own_message_timestamp", resp)
        if resp and resp.status_code == 429:
            try:
                data = resp.json()
                retry_after = float(data.get("retry_after", 2))
                await set_global_rate_limit(retry_after)
            except Exception:
                pass
        messages = resp.json() if resp and getattr(resp, "status_code", None) == 200 else []
        if not isinstance(messages, list):
            return 0.0
        newest_ts = 0.0
        for m in messages:
            if str(m.get("author", {}).get("id")) != str(OWN_USER_ID):
                continue
            msg_content = m.get("content", "") or ""
            if content_without_mention not in msg_content:
                continue
            if mention_user_id:
                mentions = m.get("mentions", []) or []
                mentioned_ids = {str(u.get("id")) for u in mentions if isinstance(u, dict) and "id" in u}
                if str(mention_user_id) not in mentioned_ids:
                    continue
            msg_ts = iso_to_epoch(m.get("timestamp") or m.get("edited_timestamp"))
            if msg_ts > newest_ts:
                newest_ts = msg_ts
        return newest_ts
    except Exception:
        logger.exception("[!] Exception in find_own_message_timestamp")
        return 0.0

async def send_interview_message(channel_id, message, mention_user_id=None):
    await check_global_rate_limit()  # Respect global rate limit
    headers = get_headers()
    headers["referer"] = f"https://discord.com/channels/@me/{channel_id}"
    headers["content-type"] = "application/json"
    data = {
        "content": message,
        "nonce": make_nonce(),
        "tts": False,
        "flags": 0
    }
    if mention_user_id:
        data["allowed_mentions"] = {"parse": [], "users": [str(mention_user_id)]}
    url = f"https://discord.com/api/v9/channels/{channel_id}/messages"
    try:
        loop = asyncio.get_event_loop()
        resp = await loop.run_in_executor(None, lambda: session.post(url, headers=headers, cookies=COOKIES, data=json.dumps(data), timeout=10))
        _log_resp_short(f"send_interview_message to {channel_id}", resp)
        if resp and resp.status_code == 429:
            try:
                data = resp.json()
                retry_after = float(data.get("retry_after", 2))
                await set_global_rate_limit(retry_after)
            except Exception:
                pass
        if getattr(resp, "status_code", None) in (200, 201):
            logger.info("Sent message to channel %s", channel_id)
            return True
        else:
            logger.warning("Failed to send message to %s status=%s", channel_id, getattr(resp, "status_code", "N/A"))
            return False
    except Exception:
        logger.exception("Exception sending message")
        return False

async def notify_added_users(applicant_user_id, channel_id):
    """
    After an applicant is approved, notify the users that were added to the group DM
    by sending them a message asking them to join the server.
    """
    logger.info("📧 notify_added_users called for applicant=%s channel=%s", applicant_user_id, channel_id)
    
    if not SERVER_INVITE_LINK:
        logger.warning("SERVER_INVITE_LINK not configured. Skipping notification to added users.")
        return
    
    # Get the list of users who were added to the group DM
    logger.info("🔍 Checking for added users in channel %s", channel_id)
    _, added_users = await check_two_people_added(channel_id, applicant_user_id)
    logger.info("✅ Found %d added users: %s", len(added_users), added_users)
    
    if len(added_users) < 2:
        logger.warning("⚠️  Less than 2 people added to group DM for applicant %s (found %d), skipping notification", 
                      applicant_user_id, len(added_users))
        return
    
    # Take the first 2 users who were added
    user1 = added_users[0]
    user2 = added_users[1]
    
    logger.info("📨 Preparing to send notification to users %s and %s", user1, user2)
    
    # Send message mentioning the 2 users with the server invite
    message = f"<@{user1}> <@{user2}> join {SERVER_INVITE_LINK} so i can let u in"
    
    # We need to send this message with allowed_mentions for both users
    headers = get_headers()
    headers["referer"] = f"https://discord.com/channels/@me/{channel_id}"
    headers["content-type"] = "application/json"
    data = {
        "content": message,
        "nonce": make_nonce(),
        "tts": False,
        "flags": 0,
        "allowed_mentions": {"parse": [], "users": [str(user1), str(user2)]}
    }
    url = f"https://discord.com/api/v9/channels/{channel_id}/messages"
    
    logger.info("🚀 Sending notification message to channel %s", channel_id)
    try:
        await check_global_rate_limit()  # Respect global rate limit
        loop = asyncio.get_event_loop()
        resp = await loop.run_in_executor(None, lambda: session.post(url, headers=headers, cookies=COOKIES, data=json.dumps(data), timeout=10))
        _log_resp_short(f"notify_added_users to {channel_id}", resp)
        if resp and resp.status_code == 429:
            try:
                retry_data = resp.json()
                retry_after = float(retry_data.get("retry_after", 2))
                await set_global_rate_limit(retry_after)
            except Exception:
                pass
        if getattr(resp, "status_code", None) in (200, 201):
            logger.info("✅ Successfully sent notification to users %s and %s in channel %s", user1, user2, channel_id)
        else:
            logger.warning("❌ Failed to send notification status=%s response=%s", 
                          getattr(resp, "status_code", "N/A"), 
                          getattr(resp, "text", "N/A")[:200])
    except Exception:
        logger.exception("❌ Exception sending notification to added users")


async def approve_application(request_id):
    await check_global_rate_limit()  # Respect global rate limit
    url = f"https://discord.com/api/v9/guilds/{GUILD_ID}/requests/id/{request_id}"
    headers = get_headers()
    headers["content-type"] = "application/json"
    headers["referer"] = f"https://discord.com/channels/{GUILD_ID}/member-safety"
    data = {"action": "APPROVED"}
    try:
        loop = asyncio.get_event_loop()
        resp = await loop.run_in_executor(None, lambda: session.patch(url, headers=headers, cookies=COOKIES, data=json.dumps(data), timeout=10))
        _log_resp_short(f"approve_application {request_id}", resp)
        if resp and resp.status_code == 429:
            try:
                retry_data = resp.json()
                retry_after = float(retry_data.get("retry_after", 2))
                await set_global_rate_limit(retry_after)
            except Exception:
                pass
        if getattr(resp, "status_code", None) == 200:
            logger.info("✅ Approved application %s", request_id)
        else:
            logger.warning("❌ Failed to approve application %s status=%s", request_id, getattr(resp, "status_code", "N/A"))
    except Exception:
        logger.exception("❌ Exception approving application %s", request_id)



async def channel_has_image_from_user(channel_id, user_id, min_ts=0.0):
    """Check if user has sent an image in the channel after min_ts. Handles rate limits with retry."""
    await check_global_rate_limit()  # Respect global rate limit
    url = f"https://discord.com/api/v9/channels/{channel_id}/messages?limit=100"  # Increased from 50 to 100
    headers = get_headers()
    headers["referer"] = f"https://discord.com/channels/@me/{channel_id}"
    headers.pop("content-type", None)
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            loop = asyncio.get_event_loop()
            resp = await loop.run_in_executor(None, lambda: session.get(url, headers=headers, cookies=COOKIES, timeout=10))
            _log_resp_short("channel_has_image_from_user", resp)
            
            # Handle rate limiting with retry
            if getattr(resp, "status_code", None) == 429:
                try:
                    data = resp.json()
                    retry = float(data.get("retry_after", 2))
                except Exception:
                    retry = 2.0
                await set_global_rate_limit(retry)  # Set global rate limit
                logger.warning("Rate limited checking images in channel %s, retrying in %.1fs (attempt %d/%d)", 
                              channel_id, retry, attempt + 1, max_retries)
                await asyncio.sleep(retry)
                continue  # Retry instead of returning False
            
            if getattr(resp, "status_code", None) != 200:
                logger.warning("Failed to fetch messages from channel %s: status=%s (attempt %d/%d)", 
                              channel_id, getattr(resp, "status_code", "N/A"), attempt + 1, max_retries)
                if attempt < max_retries - 1:
                    await asyncio.sleep(0.5)  # Brief delay before retry
                    continue
                return False
            
            messages = resp.json()
            if not isinstance(messages, list):
                logger.warning("Invalid message format from channel %s (attempt %d/%d)", 
                              channel_id, attempt + 1, max_retries)
                if attempt < max_retries - 1:
                    await asyncio.sleep(0.5)
                    continue
                return False
            
            # Check messages for images
            for m in messages:
                msg_ts = iso_to_epoch(m.get("timestamp") or m.get("edited_timestamp"))
                if msg_ts < min_ts:
                    continue
                if str(m.get("author", {}).get("id")) != str(user_id):
                    continue
                attachments = m.get("attachments", []) or []
                for a in attachments:
                    content_type = (a.get("content_type") or "").lower()
                    filename = (a.get("filename") or "").lower()
                    if content_type.startswith("image/") or filename.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp")):
                        logger.info("✅ Found image attachment in channel %s from user %s: %s", channel_id, user_id, filename)
                        return True
            return False
            
        except Exception:
            logger.exception("Exception in channel_has_image_from_user (attempt %d/%d)", attempt + 1, max_retries)
            if attempt < max_retries - 1:
                await asyncio.sleep(1.0)  # Wait before retry
                continue
            return False
    
    # Should not reach here, but return False as fallback
    return False

# ---------------------------
# Event-driven behaviors
# ---------------------------

async def process_application(reqid, user_id):
    """Process a single application - open interview, find channel, send message, schedule follow-up."""
    logger.info("Starting processing for reqid=%s user=%s", reqid, user_id)

    # open interview
    await open_interview(reqid)

    # Wait for channel to be created
    start_time = time.time()
    channel_id = None
    while time.time() - start_time < CHANNEL_FIND_TIMEOUT:
        channel_id = await find_existing_interview_channel(user_id)
        if channel_id:
            break
        await asyncio.sleep(1.0)

    if not channel_id:
        logger.warning("Could not find group DM for reqid=%s", reqid)
        return

    # If our message already exists, use its Discord timestamp as opened_at
    if await message_already_sent(channel_id, MESSAGE_CONTENT, mention_user_id=user_id, min_ts=0.0):
        prior_ts = await find_own_message_timestamp(channel_id, MESSAGE_CONTENT, mention_user_id=user_id)
        if prior_ts > 0.0:
            opened_at = prior_ts
        else:
            opened_at = time.time()
        logger.info("Message already present in %s. Will not re-send. opened_at=%s", channel_id, opened_at)
        open_interviews[str(user_id)] = {"reqid": reqid, "channel_id": channel_id, "opened_at": opened_at}
        # clear prior reminder state so the user can be reminded again on re-apply
        add_two_people_reminded.discard(str(user_id))
    else:
        composed_message = f"<@{user_id}>\n{MESSAGE_CONTENT}"
        sent_ok = await send_interview_message(channel_id, composed_message, mention_user_id=user_id)
        if not sent_ok:
            logger.warning("Failed to send interview message to %s for reqid=%s", channel_id, reqid)
            return
        # After sending, try to use the Discord timestamp of our sent message if available
        sent_ts = await find_own_message_timestamp(channel_id, MESSAGE_CONTENT, mention_user_id=user_id)
        if sent_ts > 0.0:
            opened_at = sent_ts
        else:
            opened_at = time.time()
        open_interviews[str(user_id)] = {"reqid": reqid, "channel_id": channel_id, "opened_at": opened_at}
        # clear prior reminder state so the user can be reminded again on re-apply
        add_two_people_reminded.discard(str(user_id))
        logger.info("Sent message to %s for reqid=%s; using opened_at=%s", channel_id, reqid, opened_at)

    logger.info("Registered reqid=%s for user=%s (channel=%s opened_at=%s)", reqid, user_id, channel_id, opened_at)

    # Schedule follow-up task
    async def send_follow_up():
        await asyncio.sleep(FOLLOW_UP_DELAY)
        # Check if user still needs follow-up (hasn't sent image yet)
        if str(user_id) in open_interviews:
            info = open_interviews.get(str(user_id), {})
            channel = info.get("channel_id")
            opened = info.get("opened_at", 0.0)
            if channel and not (str(user_id) in user_has_photo and user_has_photo[str(user_id)]):
                if not await channel_has_image_from_user(channel, user_id, min_ts=opened):
                    followup_composed = f"<@{user_id}>\n{FOLLOW_UP_MESSAGE}"
                    await send_interview_message(channel, followup_composed, mention_user_id=user_id)
                    logger.info("Sent follow-up reminder to user %s", user_id)
    
    # Cancel any existing follow-up task for this user
    if str(user_id) in follow_up_tasks:
        follow_up_tasks[str(user_id)].cancel()
    
    # Schedule new follow-up task
    follow_up_tasks[str(user_id)] = asyncio.create_task(send_follow_up())

async def check_and_approve_if_ready(user_id):
    """Check if user meets both conditions and approve if so."""
    user_id_str = str(user_id)
    if user_id_str not in open_interviews:
        return
    
    info = open_interviews[user_id_str]
    reqid = info.get("reqid")
    channel_id = info.get("channel_id")
    opened_at = info.get("opened_at", 0.0)
    
    if not reqid or not channel_id:
        return
    
    has_two_people, added_users = await check_two_people_added(channel_id, user_id)
    has_image = user_has_photo.get(user_id_str, False) or await channel_has_image_from_user(channel_id, user_id, min_ts=opened_at)
    
    logger.info("CHECK APPROVAL: user=%s has_two_people=%s has_image=%s", user_id, has_two_people, has_image)
    
    # If image present but not 2 people added, send the "add 2 people" reminder once
    if has_image and not has_two_people:
        if user_id_str not in add_two_people_reminded:
            logger.info("Attempting add-2-people reminder for user %s in channel %s", user_id, channel_id)
            reminder = f"<@{user_id}>\n{ADD_TWO_PEOPLE_MESSAGE}"
            sent = False
            try:
                sent = await send_interview_message(channel_id, reminder, mention_user_id=user_id)
            except Exception:
                logger.exception("Exception while sending add-2-people reminder to %s", user_id)
            if sent:
                add_two_people_reminded.add(user_id_str)
                logger.info("Sent add-2-people reminder to user %s in channel %s", user_id, channel_id)
            else:
                logger.warning("Failed to send add-2-people reminder to %s in channel %s; will retry later", user_id, channel_id)
    
    # Approve if both conditions met
    if has_two_people and has_image:
        logger.info("🎉 APPROVING reqid=%s for user=%s (both conditions met)", reqid, user_id)
        await approve_application(reqid)
        
        # Send notification to the 2 added users
        logger.info("📧 Sending notification to added users for user %s in channel %s", user_id, channel_id)
        try:
            await notify_added_users(user_id, channel_id)
            logger.info("✅ Successfully sent notification to added users for user %s", user_id)
        except Exception:
            logger.exception("❌ Exception while notifying added users for %s", user_id)
        
        # Clean up
        del open_interviews[user_id_str]
        user_has_photo.pop(user_id_str, None)
        add_two_people_reminded.discard(user_id_str)
        if user_id_str in follow_up_tasks:
            follow_up_tasks[user_id_str].cancel()
            del follow_up_tasks[user_id_str]

# Discord event handlers
@bot.event
async def on_ready():
    logger.info("="*60)
    logger.info("🚀 Bot logged in as %s - EVENT-DRIVEN MODE", bot.user)
    logger.info("="*60)
    
    # Handle startup applications
    logger.info("🔍 Checking for existing applications at startup...")
    startup_apps = await get_pending_applications()
    if startup_apps:
        logger.info("📋 Found %d applications at startup", len(startup_apps))
        
        # Mark all as seen first, then process slowly
        startup_to_process = []
        for app in startup_apps:
            reqid = app.get("id")
            user_id = app.get("user_id")
            if reqid and user_id and reqid not in seen_reqs:
                seen_reqs.add(reqid)
                startup_to_process.append({"reqid": reqid, "user_id": str(user_id)})
        
        if startup_to_process:
            logger.info("🐢 Processing %d startup applications SLOWLY", len(startup_to_process))
            total = len(startup_to_process)
            if total > MAX_STARTUP_APPS:
                logger.warning("⚠️  Limiting to %d applications", MAX_STARTUP_APPS)
                startup_to_process = startup_to_process[:MAX_STARTUP_APPS]
                total = len(startup_to_process)
            
            # Process in small batches with delays
            for i in range(0, total, STARTUP_BATCH_SIZE):
                batch = startup_to_process[i:i+STARTUP_BATCH_SIZE]
                batch_num = (i // STARTUP_BATCH_SIZE) + 1
                total_batches = (total + STARTUP_BATCH_SIZE - 1) // STARTUP_BATCH_SIZE
                
                logger.info("📦 Processing startup batch %d/%d (%d applications)", batch_num, total_batches, len(batch))
                
                # Process batch concurrently
                tasks = []
                for app in batch:
                    reqid = app["reqid"]
                    user_id = app["user_id"]
                    tasks.append(process_application(reqid, user_id))
                
                await asyncio.gather(*tasks, return_exceptions=True)
                
                # Delay between batches
                if i + STARTUP_BATCH_SIZE < total:
                    logger.info("⏳ Waiting %ds before next startup batch...", STARTUP_BATCH_DELAY)
                    await asyncio.sleep(STARTUP_BATCH_DELAY)
            
            logger.info("✅ Completed processing %d startup applications", total)
        else:
            logger.info("All startup applications already processed")
    else:
        logger.info("No applications at startup")
    
    logger.info("="*60)
    logger.info("🎯 Bot ready - listening for events")
    logger.info("="*60)
    
    # Start background task to check for new applications periodically (backup)
    check_new_applications.start()

@bot.event
async def on_message(message):
    """Detect when a photo is sent in an interview channel - INSTANT detection."""
    # Ignore messages from the bot itself
    if str(message.author.id) == OWN_USER_ID_STR:
        return
    
    # Check if this is a group DM (type 3)
    if not isinstance(message.channel, discord.GroupChannel):
        return
    
    user_id_str = str(message.author.id)
    channel_id = str(message.channel.id)
    
    # Check if this user has an open interview
    if user_id_str not in open_interviews:
        return
    
    # Verify this is the correct channel
    info = open_interviews[user_id_str]
    if info.get("channel_id") != channel_id:
        return
    
    # Check if message has image attachments
    has_image = False
    for attachment in message.attachments:
        content_type = (attachment.content_type or "").lower()
        filename = (attachment.filename or "").lower()
        if content_type.startswith("image/") or filename.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp")):
            has_image = True
            logger.info("⚡ INSTANT: User %s sent image in channel %s - %s", user_id_str, channel_id, filename)
            break
    
    if has_image:
        # Mark user as having sent photo
        user_has_photo[user_id_str] = True
        
        # Cancel follow-up reminder since they sent the photo
        if user_id_str in follow_up_tasks:
            follow_up_tasks[user_id_str].cancel()
            del follow_up_tasks[user_id_str]
        
        # Check if ready to approve
        await check_and_approve_if_ready(message.author.id)

@bot.event
async def on_private_channel_update(before, after):
    """Detect when group DM recipients change - INSTANT detection of member additions."""
    if not isinstance(after, discord.GroupChannel):
        return
    
    # Check if recipients changed (handle case where before is None)
    before_recipients = set(str(u.id) for u in before.recipients) if before and hasattr(before, 'recipients') else set()
    after_recipients = set(str(u.id) for u in after.recipients) if hasattr(after, 'recipients') else set()
    
    if before_recipients != after_recipients:
        channel_id = str(after.id)
        added_users = after_recipients - before_recipients
        if added_users:
            logger.info("⚡ INSTANT: User(s) added to channel %s: %s", channel_id, added_users)
        
        # Check if any user in our open_interviews is in this channel
        for user_id_str, info in list(open_interviews.items()):
            if info.get("channel_id") == channel_id:
                logger.info("⚡ Checking approval readiness for applicant %s after recipient change", user_id_str)
                await check_and_approve_if_ready(int(user_id_str))
                break

@tasks.loop(seconds=APPLICATION_CHECK_INTERVAL)
async def check_new_applications():
    """Periodically check for new applications (backup to events)."""
    try:
        apps = await get_pending_applications()
        for app in apps:
            reqid = app.get("id")
            user_id = app.get("user_id")
            if not reqid or not user_id:
                continue

            if reqid in seen_reqs:
                continue
            
            # mark as seen immediately
            seen_reqs.add(reqid)

            # Process INSTANTLY
            logger.info("⚡ NEW APPLICATION - Processing INSTANTLY: reqid=%s", reqid)
            asyncio.create_task(process_application(reqid, str(user_id)))
    except Exception:
        logger.exception("Exception in check_new_applications")

@check_new_applications.before_loop
async def before_check_new_applications():
    await bot.wait_until_ready()

async def main():
    logger.info("="*60)
    logger.info("🚀 Starting meow.py - EVENT-DRIVEN ARCHITECTURE")
    logger.info("="*60)
    
    # Validate TOKEN before starting
    if not TOKEN:
        logger.error("="*60)
        logger.error("❌ ERROR: Discord TOKEN is not configured!")
        logger.error("="*60)
        logger.error("Please set your Discord USER token using one of these methods:")
        logger.error("  1. Paste your token in the TOKEN variable at the top of meow.py (RECOMMENDED)")
        logger.error("     Find the line: TOKEN = \"\"")
        logger.error("     Replace it with: TOKEN = \"your_user_token_here\"")
        logger.error("")
        logger.error("  2. Or set the DISCORD_TOKEN environment variable:")
        logger.error("     export DISCORD_TOKEN='your_user_token_here'")
        logger.error("")
        logger.error("IMPORTANT: This bot requires a USER token, not a bot token!")
        logger.error("To get your Discord USER token:")
        logger.error("  1. Open Discord in your web browser")
        logger.error("  2. Press F12 to open Developer Tools")
        logger.error("  3. Go to the 'Network' tab")
        logger.error("  4. Type a message in any channel")
        logger.error("  5. Look for a request and check the 'authorization' header")
        logger.error("  6. Copy the token value (it should be a long string)")
        logger.error("")
        logger.error("WARNING: Never share your user token with anyone!")
        logger.error("="*60)
        session.close()  # Close requests session before exit
        sys.exit(1)
    
    try:
        await bot.start(TOKEN)
    except discord.errors.LoginFailure as e:
        logger.error("="*60)
        logger.error("❌ AUTHENTICATION FAILED: Invalid Discord token")
        logger.error("="*60)
        logger.error("The provided Discord USER token is invalid or has been revoked.")
        logger.error("Error details: %s", str(e))
        logger.error("")
        logger.error("IMPORTANT: This bot requires a USER token, not a bot token!")
        logger.error("")
        logger.error("To get your Discord USER token:")
        logger.error("  1. Open Discord in your web browser (discord.com)")
        logger.error("  2. Press F12 to open Developer Tools")
        logger.error("  3. Go to the 'Network' tab")
        logger.error("  4. Type a message in any channel")
        logger.error("  5. Find a request (like 'messages') and click it")
        logger.error("  6. Look at the Request Headers section")
        logger.error("  7. Find 'authorization' header and copy its value")
        logger.error("  8. Paste that value in the TOKEN variable at the top of meow.py")
        logger.error("     Or set it using: export DISCORD_TOKEN='your_user_token'")
        logger.error("")
        logger.error("WARNING: Never share your user token with anyone!")
        logger.error("="*60)
        await bot.close()
        session.close()  # Close requests session before exit
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        await bot.close()
        session.close()  # Close requests session before exit
    except Exception as e:
        logger.error("="*60)
        logger.error("❌ UNEXPECTED ERROR occurred during bot startup")
        logger.error("="*60)
        logger.exception("Error details: %s", str(e))
        logger.error("="*60)
        await bot.close()
        session.close()  # Close requests session before exit
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
