import requests
import json
import time
import random
import threading
import logging
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

# ---------------------------
# Configuration / constants
# ---------------------------
TOKEN = ""
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

HEADERS_TEMPLATE = {
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

POLL_INTERVAL = 1.0  # Check for new applications every second (reasonable rate for Discord API)
APPROVAL_POLL_INTERVAL = 0.05  # Fast polling for image/2-people detection (50ms) per user thread
SEND_RETRY_DELAY = 0.5  # Faster retry for message sending
MAX_TOTAL_SEND_TIME = 180

# Optimized polling configuration for faster application opening
# Start with fast polling (0.05s) for quick response in typical cases
# Use 2.0x backoff multiplier to quickly reduce API load while still being responsive
# Cap at 2.0s to balance responsiveness with API efficiency
INITIAL_POLL_DELAY = 0.05  # Initial delay provides quick response (50ms)
MAX_POLL_DELAY = 2.0  # Maximum delay balances API load with reasonable retry speed
BACKOFF_MULTIPLIER = 2.0  # Aggressive backoff for efficient API usage (0.05→0.1→0.2→0.4→0.8→1.6→2.0s)

# Monitoring loop configuration  
MONITOR_POLL_INTERVAL = 0.05  # Fast polling for image detection (50ms) - per user thread, scales well
CHANNEL_REFRESH_INTERVAL = 10.0  # Check for new channels infrequently since it's a rare edge case

# Concurrent processing configuration
MAX_WORKERS = 100  # Increased for handling many applications concurrently

# NOTE: Thread Management Strategy
# - Each active application gets 2 daemon threads (followup + approval monitoring)
# - Daemon threads are lightweight (mostly sleeping) with minimal memory overhead (~8KB per thread)
# - Threads auto-terminate when user approved or conditions not met
# - In practice, active monitoring is bounded by pending applications (typically < 100)
# - If thread exhaustion becomes an issue (>1000 concurrent apps), consider adding a Semaphore
# - Current design prioritizes responsiveness over resource constraints

# Batch processing timing constants
CHANNEL_CREATION_DELAY = 0.2  # Reduced delay after opening interviews to allow Discord to create channels
MAX_CHANNEL_FIND_RETRIES = 8  # Increased retries with smaller delays for better reliability
CHANNEL_FIND_RETRY_DELAY = 0.2  # Reduced delay between channel finding retries

# Old application processing configuration
# These settings control how old (pre-existing) applications are processed at startup
# to avoid overwhelming Discord's API with too many requests at once.
# Recommended ranges: OLD_APP_DELAY = 0.5-2.0 seconds, OLD_APP_BATCH_SIZE = 5-20 applications
# For servers with 50-100+ unprocessed applications, use longer delays (1.5-2.0s) and smaller batches (5-10)
# For servers with <20 unprocessed applications, shorter delays (0.5-1.0s) and larger batches (15-20) work well
OLD_APP_DELAY = 1.0  # Delay in seconds between batches
OLD_APP_BATCH_SIZE = 10  # Number of applications per batch

# in-memory state only (matches original behavior)
seen_reqs = set()
open_interviews = {}
open_interviews_lock = threading.Lock()
seen_reqs_lock = threading.Lock()

# NEW: track which users we've sent the "add 2 people" reminder to (in-memory only)
add_two_people_reminded = set()
add_two_people_reminded_lock = threading.Lock()

# Logging
VERBOSE = False
logger = logging.getLogger("discord_auto_accept")
logger.setLevel(logging.DEBUG if VERBOSE else logging.INFO)
ch = logging.StreamHandler()
ch.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logger.addHandler(ch)

# Helpers
def make_nonce():
    return str(random.randint(10**17, 10**18 - 1))

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
def get_pending_applications():
    """
    Fetch all pending applications from Discord API with pagination.
    Handles rate limiting with exponential backoff.
    """
    all_apps = []
    after = None
    page_count = 0
    
    while True:
        # Build URL with pagination
        url = f"https://discord.com/api/v9/guilds/{GUILD_ID}/requests?status=SUBMITTED&limit=100"
        if after:
            url += f"&after={after}"
        
        headers = HEADERS_TEMPLATE.copy()
        headers["referer"] = f"https://discord.com/channels/{GUILD_ID}/member-safety"
        
        try:
            resp = requests.get(url, headers=headers, cookies=COOKIES, timeout=10)
            _log_resp_short(f"get_pending_applications (page {page_count + 1})", resp)
            
            # Handle rate limiting with exponential backoff
            if resp and resp.status_code == 429:
                try:
                    data = resp.json()
                    retry_after = float(data.get("retry_after", 5))
                except Exception:
                    retry_after = 5.0
                logger.warning("⚠️ Rate limited fetching applications page %d, waiting %.1fs before retry", 
                              page_count + 1, retry_after)
                time.sleep(retry_after)
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
            
            # Small delay between pages to avoid rate limiting (only happens on startup for 100+ apps)
            time.sleep(0.2)
            
        except Exception:
            logger.exception("Exception fetching pending applications (page %d)", page_count + 1)
            break
    
    if page_count > 0:
        logger.info("✅ Fetched %d total applications across %d pages", len(all_apps), page_count)
    
    return all_apps

def open_interview(request_id):
    url = f"https://discord.com/api/v9/join-requests/{request_id}/interview"
    headers = HEADERS_TEMPLATE.copy()
    headers["referer"] = f"https://discord.com/channels/{GUILD_ID}/member-safety"
    headers["content-type"] = "application/json"
    try:
        resp = requests.post(url, headers=headers, cookies=COOKIES, timeout=10)
        _log_resp_short(f"open_interview {request_id}", resp)
        logger.info("Opened interview for request %s (status=%s)", request_id, getattr(resp, "status_code", "N/A"))
    except Exception:
        logger.exception("Exception opening interview")

def open_interviews_batch(request_ids):
    """Open multiple interviews concurrently using thread pool."""
    if not request_ids:
        return
    
    logger.info("Opening %d interviews concurrently", len(request_ids))
    with ThreadPoolExecutor(max_workers=min(len(request_ids), MAX_WORKERS)) as executor:
        futures = {executor.submit(open_interview, rid): rid for rid in request_ids}
        for future in as_completed(futures):
            try:
                future.result()
            except Exception:
                logger.exception("Exception in batch interview opening")
    logger.info("Completed opening %d interviews", len(request_ids))

def find_existing_interview_channel(user_id):
    url = "https://discord.com/api/v9/users/@me/channels"
    headers = HEADERS_TEMPLATE.copy()
    headers.pop("content-type", None)
    try:
        resp = requests.get(url, headers=headers, cookies=COOKIES, timeout=10)
        _log_resp_short("find_existing_interview_channel", resp)
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

def find_channels_batch(user_ids):
    """Find interview channels for multiple users by fetching channels once and matching all users."""
    if not user_ids:
        return {}
    
    url = "https://discord.com/api/v9/users/@me/channels"
    headers = HEADERS_TEMPLATE.copy()
    headers.pop("content-type", None)
    
    try:
        resp = requests.get(url, headers=headers, cookies=COOKIES, timeout=10)
        _log_resp_short("find_channels_batch", resp)
        channels = resp.json() if resp and resp.status_code == 200 else []
        
        # Build a mapping of user_id -> channel_id
        user_to_channel = {}
        user_ids_str = {str(uid) for uid in user_ids}
        
        if isinstance(channels, list):
            for c in channels:
                if isinstance(c, dict) and c.get("type") == 3:
                    recipient_ids = [u.get("id") for u in c.get("recipients", []) if isinstance(u, dict) and "id" in u]
                    recipient_ids_str = {str(rid) for rid in recipient_ids}
                    
                    # Check which of our target users are in this channel
                    matched_users = user_ids_str.intersection(recipient_ids_str)
                    for user_id in matched_users:
                        channel_id = c.get("id")
                        # Prefer newest channel (highest snowflake ID)
                        # Safely handle None or empty channel_id values
                        if channel_id and (user_id not in user_to_channel or int(channel_id) > int(user_to_channel.get(user_id) or '0' or 0)):
                            user_to_channel[user_id] = channel_id
        
        return user_to_channel
    except Exception:
        logger.exception("Exception in find_channels_batch")
        return {}

def get_channel_recipients(channel_id):
    """Get the list of recipient user IDs in a group DM channel. Handles rate limits with retry."""
    url = f"https://discord.com/api/v9/channels/{channel_id}"
    headers = HEADERS_TEMPLATE.copy()
    headers["referer"] = f"https://discord.com/channels/@me/{channel_id}"
    headers.pop("content-type", None)
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, headers=headers, cookies=COOKIES, timeout=10)
            _log_resp_short("get_channel_recipients", resp)
            
            # Handle rate limiting with retry
            if resp and resp.status_code == 429:
                try:
                    data = resp.json()
                    retry = float(data.get("retry_after", 2))
                except Exception:
                    retry = 2.0
                logger.warning("Rate limited getting recipients for channel %s, retrying in %.1fs (attempt %d/%d)", 
                              channel_id, retry, attempt + 1, max_retries)
                time.sleep(retry)
                continue
            
            if resp and resp.status_code == 200:
                channel_data = resp.json()
                recipients = channel_data.get("recipients", [])
                recipient_ids = [u.get("id") for u in recipients if isinstance(u, dict) and "id" in u]
                return recipient_ids
            
            logger.warning("Failed to get recipients from channel %s: status=%s (attempt %d/%d)", 
                          channel_id, getattr(resp, "status_code", "N/A"), attempt + 1, max_retries)
            if attempt < max_retries - 1:
                time.sleep(0.5)
                continue
            return []
            
        except Exception:
            logger.exception("Exception getting channel recipients (attempt %d/%d)", attempt + 1, max_retries)
            if attempt < max_retries - 1:
                time.sleep(1.0)
                continue
            return []
    
    return []

def check_two_people_added(channel_id, applicant_user_id):
    """
    Check if the applicant has added 2 people to the group DM.
    Returns (bool, list of added user IDs excluding bot and applicant).
    """
    recipients = get_channel_recipients(channel_id)
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


def message_already_sent(channel_id, content_without_mention, mention_user_id=None, min_ts=0.0):
    url = f"https://discord.com/api/v9/channels/{channel_id}/messages?limit=50"
    headers = HEADERS_TEMPLATE.copy()
    headers["referer"] = f"https://discord.com/channels/@me/{channel_id}"
    headers.pop("content-type", None)
    try:
        resp = requests.get(url, headers=headers, cookies=COOKIES, timeout=10)
        _log_resp_short("message_already_sent", resp)
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

def find_own_message_timestamp(channel_id, content_without_mention, mention_user_id=None):
    """
    Return the newest epoch timestamp of the most recent message in the channel
    authored by OWN_USER_ID that contains content_without_mention and (if provided)
    mentions mention_user_id. Returns 0.0 if not found.
    """
    url = f"https://discord.com/api/v9/channels/{channel_id}/messages?limit=100"
    headers = HEADERS_TEMPLATE.copy()
    headers["referer"] = f"https://discord.com/channels/@me/{channel_id}"
    headers.pop("content-type", None)
    try:
        resp = requests.get(url, headers=headers, cookies=COOKIES, timeout=10)
        _log_resp_short("find_own_message_timestamp", resp)
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

def send_interview_message(channel_id, message, mention_user_id=None):
    headers = HEADERS_TEMPLATE.copy()
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
        resp = requests.post(url, headers=headers, cookies=COOKIES, data=json.dumps(data), timeout=10)
        _log_resp_short(f"send_interview_message to {channel_id}", resp)
        if getattr(resp, "status_code", None) in (200, 201):
            logger.info("Sent message to channel %s", channel_id)
            return True
        else:
            logger.warning("Failed to send message to %s status=%s", channel_id, getattr(resp, "status_code", "N/A"))
            return False
    except Exception:
        logger.exception("Exception sending message")
        return False

def send_messages_batch(messages_to_send):
    """Send multiple messages concurrently. messages_to_send is a list of (channel_id, message, mention_user_id) tuples."""
    if not messages_to_send:
        return {}
    
    logger.info("Sending %d messages concurrently", len(messages_to_send))
    results = {}
    
    def send_one(channel_id, message, mention_user_id):
        success = send_interview_message(channel_id, message, mention_user_id)
        return (channel_id, success)
    
    with ThreadPoolExecutor(max_workers=min(len(messages_to_send), MAX_WORKERS)) as executor:
        futures = {
            executor.submit(send_one, channel_id, message, mention_user_id): channel_id 
            for channel_id, message, mention_user_id in messages_to_send
        }
        for future in as_completed(futures):
            try:
                channel_id, success = future.result()
                results[channel_id] = success
            except Exception:
                logger.exception("Exception in batch message sending")
    
    logger.info("Completed sending %d messages", len(messages_to_send))
    return results

def notify_added_users(applicant_user_id, channel_id):
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
    _, added_users = check_two_people_added(channel_id, applicant_user_id)
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
    headers = HEADERS_TEMPLATE.copy()
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
        resp = requests.post(url, headers=headers, cookies=COOKIES, data=json.dumps(data), timeout=10)
        _log_resp_short(f"notify_added_users to {channel_id}", resp)
        if getattr(resp, "status_code", None) in (200, 201):
            logger.info("✅ Successfully sent notification to users %s and %s in channel %s", user1, user2, channel_id)
        else:
            logger.warning("❌ Failed to send notification status=%s response=%s", 
                          getattr(resp, "status_code", "N/A"), 
                          getattr(resp, "text", "N/A")[:200])
    except Exception:
        logger.exception("❌ Exception sending notification to added users")


def approve_application(request_id):
    url = f"https://discord.com/api/v9/guilds/{GUILD_ID}/requests/id/{request_id}"
    headers = HEADERS_TEMPLATE.copy()
    headers["content-type"] = "application/json"
    headers["referer"] = f"https://discord.com/channels/{GUILD_ID}/member-safety"
    data = {"action": "APPROVED"}
    try:
        resp = requests.patch(url, headers=headers, cookies=COOKIES, data=json.dumps(data), timeout=10)
        _log_resp_short(f"approve_application {request_id}", resp)
        if getattr(resp, "status_code", None) == 200:
            logger.info("✅ Approved application %s", request_id)
        else:
            logger.warning("❌ Failed to approve application %s status=%s", request_id, getattr(resp, "status_code", "N/A"))
    except Exception:
        logger.exception("❌ Exception approving application %s", request_id)



def channel_has_image_from_user(channel_id, user_id, min_ts=0.0):
    """Check if user has sent an image in the channel after min_ts. Handles rate limits with retry."""
    url = f"https://discord.com/api/v9/channels/{channel_id}/messages?limit=100"  # Increased from 50 to 100
    headers = HEADERS_TEMPLATE.copy()
    headers["referer"] = f"https://discord.com/channels/@me/{channel_id}"
    headers.pop("content-type", None)
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, headers=headers, cookies=COOKIES, timeout=10)
            _log_resp_short("channel_has_image_from_user", resp)
            
            # Handle rate limiting with retry
            if getattr(resp, "status_code", None) == 429:
                try:
                    data = resp.json()
                    retry = float(data.get("retry_after", 2))
                except Exception:
                    retry = 2.0
                logger.warning("Rate limited checking images in channel %s, retrying in %.1fs (attempt %d/%d)", 
                              channel_id, retry, attempt + 1, max_retries)
                time.sleep(retry)
                continue  # Retry instead of returning False
            
            if getattr(resp, "status_code", None) != 200:
                logger.warning("Failed to fetch messages from channel %s: status=%s (attempt %d/%d)", 
                              channel_id, getattr(resp, "status_code", "N/A"), attempt + 1, max_retries)
                if attempt < max_retries - 1:
                    time.sleep(0.5)  # Brief delay before retry
                    continue
                return False
            
            messages = resp.json()
            if not isinstance(messages, list):
                logger.warning("Invalid message format from channel %s (attempt %d/%d)", 
                              channel_id, attempt + 1, max_retries)
                if attempt < max_retries - 1:
                    time.sleep(0.5)
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
                time.sleep(1.0)  # Wait before retry
                continue
            return False
    
    # Should not reach here, but return False as fallback
    return False

# ---------------------------
# Main behaviors (simple/original-style flow)
# ---------------------------
def process_application_independently(app):
    """
    Process a single application completely independently in its own thread.
    No shared delays or waits with other applications.
    """
    reqid = app['reqid']
    user_id = str(app['user_id'])
    
    logger.info("Starting independent processing for reqid=%s user=%s", reqid, user_id)
    
    # Step 1: Open interview
    open_interview(reqid)
    
    # Step 2: Wait for channel to be created (this app waits independently)
    time.sleep(CHANNEL_CREATION_DELAY)
    
    # Step 3: Find the channel (retry independently if needed)
    channel_id = None
    for retry in range(MAX_CHANNEL_FIND_RETRIES):
        channel_id = find_existing_interview_channel(user_id)
        if channel_id:
            break
        time.sleep(CHANNEL_FIND_RETRY_DELAY)
    
    if not channel_id:
        logger.warning("Could not find channel for user %s after retries", user_id)
        return
    
    # Step 4: Check if message already sent
    if message_already_sent(channel_id, MESSAGE_CONTENT, mention_user_id=user_id, min_ts=0.0):
        prior_ts = find_own_message_timestamp(channel_id, MESSAGE_CONTENT, mention_user_id=user_id)
        opened_at = prior_ts if prior_ts > 0.0 else time.time()
        logger.info("Message already present in %s. Will not re-send.", channel_id)
        with open_interviews_lock:
            open_interviews[user_id] = {"reqid": reqid, "channel_id": channel_id, "opened_at": opened_at}
        with add_two_people_reminded_lock:
            add_two_people_reminded.discard(user_id)
    else:
        # Step 5: Send message
        composed_message = f"<@{user_id}>\n{MESSAGE_CONTENT}"
        sent_ok = send_interview_message(channel_id, composed_message, mention_user_id=user_id)
        
        if not sent_ok:
            logger.warning("Failed to send message to channel %s for user %s", channel_id, user_id)
            return
        
        # Get timestamp of sent message
        sent_ts = find_own_message_timestamp(channel_id, MESSAGE_CONTENT, mention_user_id=user_id)
        opened_at = sent_ts if sent_ts > 0.0 else time.time()
        
        with open_interviews_lock:
            open_interviews[user_id] = {"reqid": reqid, "channel_id": channel_id, "opened_at": opened_at}
        with add_two_people_reminded_lock:
            add_two_people_reminded.discard(user_id)
        logger.info("Sent message to %s for reqid=%s; opened_at=%s", channel_id, reqid, opened_at)
    
    # Step 6: Start independent monitoring threads for this user
    # Thread 1: Follow-up message monitoring
    followup_thread = threading.Thread(target=monitor_user_followup, args=(user_id,))
    followup_thread.daemon = True
    followup_thread.name = f"followup-{user_id[:8]}"
    followup_thread.start()
    
    # Thread 2: Approval condition monitoring
    approval_thread = threading.Thread(target=monitor_user_approval, args=(user_id,))
    approval_thread.daemon = True
    approval_thread.name = f"approval-{user_id[:8]}"
    approval_thread.start()
    
    logger.info("Started independent monitoring threads for user %s", user_id)

def process_application_batch(applications):
    """
    Process multiple applications COMPLETELY INDEPENDENTLY.
    Each application gets its own thread and doesn't wait for any other application.
    """
    if not applications:
        return
    
    logger.info("Launching %d INDEPENDENT application threads (no shared waits)", len(applications))
    
    # Launch a completely independent thread for each application
    for app in applications:
        thread = threading.Thread(target=process_application_independently, args=(app,))
        thread.daemon = True
        thread.name = f"app-{app.get('user_id', 'unknown')[:8]}"
        thread.start()
    
    logger.info("All %d applications now processing independently", len(applications))

def process_old_applications_slowly(applications):
    """
    Process old applications with rate limiting to avoid overwhelming Discord API.
    This is used at startup for applications that existed before the bot started.
    """
    if not applications:
        logger.info("No old applications to process")
        return
    
    total = len(applications)
    logger.info("🐢 Processing %d old applications with rate limiting (slower to ensure all get opened)", total)
    
    # Process in smaller batches with delays between batches
    for i in range(0, total, OLD_APP_BATCH_SIZE):
        batch = applications[i:i+OLD_APP_BATCH_SIZE]
        batch_num = i // OLD_APP_BATCH_SIZE + 1
        total_batches = (total + OLD_APP_BATCH_SIZE - 1) // OLD_APP_BATCH_SIZE
        
        logger.info("📦 Processing old application batch %d/%d (%d applications)", 
                   batch_num, total_batches, len(batch))
        
        # Process this batch using the normal batch processing
        process_application_batch(batch)
        
        # Add delay between batches (except after the last batch)
        has_more_batches = (i + OLD_APP_BATCH_SIZE < total)
        if has_more_batches:
            logger.info("⏳ Waiting %.1f seconds before next batch of old applications...", OLD_APP_DELAY)
            time.sleep(OLD_APP_DELAY)
    
    logger.info("✅ Completed processing all %d old applications", total)

def monitor_user_followup(user_id):
    """Monitor a user for image upload and send follow-up if needed."""
    with open_interviews_lock:
        if user_id not in open_interviews:
            return
        info = open_interviews[user_id]
        channel_id = info.get("channel_id")
        opened_at = info.get("opened_at", time.time())
    
    if not channel_id:
        return
    
    follow_up_sent = False
    monitor_start = time.time()
    last_channel_check = monitor_start
    
    while True:
        current_time = time.time()
        if current_time - monitor_start >= MAX_TOTAL_SEND_TIME:
            break
        
        # refresh channel if user creates a new DM (but only periodically to reduce API calls)
        if current_time - last_channel_check >= CHANNEL_REFRESH_INTERVAL:
            new_channel = find_existing_interview_channel(user_id)
            if new_channel and new_channel != channel_id:
                logger.info("Switching to newer channel %s for user %s", new_channel, user_id)
                channel_id = new_channel
                opened_at = time.time()
                with open_interviews_lock:
                    if user_id in open_interviews:
                        open_interviews[user_id]["channel_id"] = channel_id
                        open_interviews[user_id]["opened_at"] = opened_at
            last_channel_check = current_time
        
        if channel_has_image_from_user(channel_id, user_id, min_ts=opened_at):
            logger.info("Image detected for user %s in channel %s; stopping monitor.", user_id, channel_id)
            break
        
        elapsed = current_time - monitor_start
        if not follow_up_sent and elapsed >= FOLLOW_UP_DELAY:
            # re-check immediately before sending follow-up to reduce races
            if not channel_has_image_from_user(channel_id, user_id, min_ts=opened_at):
                followup_composed = f"<@{user_id}>\n{FOLLOW_UP_MESSAGE}"
                send_interview_message(channel_id, followup_composed, mention_user_id=user_id)
                follow_up_sent = True
        time.sleep(MONITOR_POLL_INTERVAL)
    
    logger.info("Finished monitoring user %s", user_id)

def process_application(reqid, user_id):
    logger.info("Starting processing for reqid=%s user=%s", reqid, user_id)

    # open interview (original simple behavior)
    open_interview(reqid)

    start_time = time.time()
    channel_id = None
    poll_delay = INITIAL_POLL_DELAY
    while time.time() - start_time < MAX_TOTAL_SEND_TIME:
        channel_id = find_existing_interview_channel(user_id)
        if channel_id:
            break
        time.sleep(poll_delay)
        # Exponential backoff: gradually increase delay to reduce API load
        poll_delay = min(poll_delay * BACKOFF_MULTIPLIER, MAX_POLL_DELAY)

    if not channel_id:
        logger.warning("Could not find group DM for reqid=%s", reqid)
        return

    # If our message already exists, use its Discord timestamp as opened_at (not time.time())
    if message_already_sent(channel_id, MESSAGE_CONTENT, mention_user_id=user_id, min_ts=0.0):
        prior_ts = find_own_message_timestamp(channel_id, MESSAGE_CONTENT, mention_user_id=user_id)
        if prior_ts > 0.0:
            opened_at = prior_ts
        else:
            opened_at = time.time()
        logger.info("Message already present in %s. Will not re-send. opened_at=%s", channel_id, opened_at)
        with open_interviews_lock:
            open_interviews[str(user_id)] = {"reqid": reqid, "channel_id": channel_id, "opened_at": opened_at}
        # NEW: clear prior reminder state so the user can be reminded again on re-apply
        with add_two_people_reminded_lock:
            add_two_people_reminded.discard(str(user_id))
    else:
        composed_message = f"<@{user_id}>\n{MESSAGE_CONTENT}"
        sent_ok = send_interview_message(channel_id, composed_message, mention_user_id=user_id)
        if not sent_ok:
            logger.warning("Failed to send interview message to %s for reqid=%s", channel_id, reqid)
            return
        # After sending, try to use the Discord timestamp of our sent message if available
        sent_ts = find_own_message_timestamp(channel_id, MESSAGE_CONTENT, mention_user_id=user_id)
        if sent_ts > 0.0:
            opened_at = sent_ts
        else:
            opened_at = time.time()
        with open_interviews_lock:
            open_interviews[str(user_id)] = {"reqid": reqid, "channel_id": channel_id, "opened_at": opened_at}
        # NEW: clear prior reminder state so the user can be reminded again on re-apply
        with add_two_people_reminded_lock:
            add_two_people_reminded.discard(str(user_id))
        logger.info("Sent message to %s for reqid=%s; using opened_at=%s", channel_id, reqid, opened_at)

    logger.info("Registered reqid=%s for user=%s (channel=%s opened_at=%s)", reqid, user_id, channel_id, opened_at)

    # monitor for image and follow-up
    follow_up_sent = False
    monitor_start = time.time()
    last_channel_check = monitor_start
    
    while True:
        current_time = time.time()
        if current_time - monitor_start >= MAX_TOTAL_SEND_TIME:
            break
            
        # refresh channel if user creates a new DM (but only periodically to reduce API calls)
        if current_time - last_channel_check >= CHANNEL_REFRESH_INTERVAL:
            new_channel = find_existing_interview_channel(user_id)
            if new_channel and new_channel != channel_id:
                logger.info("Switching to newer channel %s for user %s", new_channel, user_id)
                channel_id = new_channel
                # Use fresh timestamp for accuracy when channel switches
                opened_at = time.time()
                with open_interviews_lock:
                    if str(user_id) in open_interviews:
                        open_interviews[str(user_id)]["channel_id"] = channel_id
                        open_interviews[str(user_id)]["opened_at"] = opened_at
            last_channel_check = current_time

        if channel_has_image_from_user(channel_id, user_id, min_ts=opened_at):
            logger.info("Image detected for user %s in channel %s; stopping monitor.", user_id, channel_id)
            break

        elapsed = current_time - monitor_start
        if not follow_up_sent and elapsed >= FOLLOW_UP_DELAY:
            # re-check immediately before sending follow-up to reduce races
            if not channel_has_image_from_user(channel_id, user_id, min_ts=opened_at):
                followup_composed = f"<@{user_id}>\n{FOLLOW_UP_MESSAGE}"
                send_interview_message(channel_id, followup_composed, mention_user_id=user_id)
                follow_up_sent = True
        time.sleep(MONITOR_POLL_INTERVAL)

    logger.info("Finished monitoring reqid=%s user=%s", reqid, user_id)

def monitor_user_approval(user_id):
    """
    Monitor a single user for approval conditions (image upload + 2 people added).
    This runs in a separate thread per user for parallel processing.
    """
    logger.info("Started approval monitor for user %s", user_id)
    
    while True:
        # Get user info from open_interviews
        with open_interviews_lock:
            if user_id not in open_interviews:
                logger.info("User %s no longer in open_interviews, stopping approval monitor", user_id)
                break
            info = open_interviews.get(user_id, {})
            reqid = info.get("reqid")
            channel_id = info.get("channel_id")
            opened_at = info.get("opened_at", 0.0)
        
        if not reqid or not channel_id:
            logger.warning("Missing reqid or channel_id for user %s, stopping approval monitor", user_id)
            break
        
        # Check if 2 people have been added to the group DM
        has_two_people, added_users = check_two_people_added(channel_id, user_id)
        
        has_image = channel_has_image_from_user(channel_id, user_id, min_ts=opened_at)
        
        # Log at INFO level when conditions change or initially
        if has_two_people or has_image:
            logger.info("APPROVAL MONITOR: user=%s has_two_people=%s (added=%s) has_image=%s", 
                       user_id, has_two_people, added_users if has_two_people else "none", has_image)
        else:
            logger.debug("APPROVAL MONITOR: user=%s has_two_people=%s has_image=%s", 
                        user_id, has_two_people, has_image)

        # If image present but not 2 people added, send the "add 2 people" reminder once
        if has_image and not has_two_people:
            # Check if reminder already sent
            should_send = False
            with add_two_people_reminded_lock:
                if user_id not in add_two_people_reminded:
                    should_send = True
            
            if should_send:
                logger.info("Sending add-2-people reminder for user %s in channel %s", user_id, channel_id)
                reminder = f"<@{user_id}>\n{ADD_TWO_PEOPLE_MESSAGE}"
                sent = False
                try:
                    sent = send_interview_message(channel_id, reminder, mention_user_id=user_id)
                except Exception:
                    logger.exception("Exception while sending add-2-people reminder to %s", user_id)
                if sent:
                    with add_two_people_reminded_lock:
                        add_two_people_reminded.add(user_id)
                    logger.info("Sent add-2-people reminder to user %s in channel %s", user_id, channel_id)
                else:
                    logger.warning("Failed to send add-2-people reminder to %s in channel %s; will retry later", user_id, channel_id)

        # Approve when 2 people added AND image is uploaded
        if has_two_people and has_image:
            # Atomically check and remove user to prevent duplicate approvals
            should_approve = False
            with open_interviews_lock:
                if user_id in open_interviews:
                    del open_interviews[user_id]
                    should_approve = True
            
            if not should_approve:
                # Another thread already approved this user
                logger.info("User %s already approved by another thread, stopping monitor", user_id)
                break
            
            logger.info("✅ APPROVING reqid=%s for user=%s (has image + 2 people added)", reqid, user_id)
            
            # Step 1: Approve the application
            try:
                approve_application(reqid)
                logger.info("✅ Successfully approved application for user %s", user_id)
            except Exception:
                logger.exception("❌ Failed to approve application for user %s", user_id)
            
            # Step 2: Send notification to the 2 added users after approval
            logger.info("📧 Sending notification to added users for user %s in channel %s", user_id, channel_id)
            try:
                notify_added_users(user_id, channel_id)
                logger.info("✅ Successfully sent notification to added users for user %s", user_id)
            except Exception:
                logger.exception("❌ Exception while notifying added users for %s", user_id)
            
            # Clear reminder state
            with add_two_people_reminded_lock:
                add_two_people_reminded.discard(user_id)
            
            logger.info("✅ User %s fully processed (approved + notified), removed from monitoring", user_id)
            break
        
        # Sleep before next check
        time.sleep(APPROVAL_POLL_INTERVAL)

def recover_existing_interviews():
    """
    At startup, detect and recover any existing interview channels that may have been
    opened before the bot restarted. This handles servers with 100+ applications smoothly.
    
    Returns a tuple of (recovered_dict, unprocessed_list):
    - recovered_dict: user_id -> {reqid, channel_id, opened_at} for existing interviews
    - unprocessed_list: list of {"reqid": ..., "user_id": ...} for applications that need to be opened
    """
    logger.info("🔍 Scanning for existing interview channels at startup...")
    
    # Get all pending applications
    apps = get_pending_applications()
    if not apps:
        logger.info("No pending applications found at startup")
        return {}, []
    
    logger.info("📋 Found %d pending applications, checking for existing interviews", len(apps))
    
    # Get all user IDs from pending applications
    pending_users = {}
    for app in apps:
        reqid = app.get("id")
        user_id = app.get("user_id")
        if reqid and user_id:
            pending_users[str(user_id)] = reqid
    
    if not pending_users:
        logger.info("No valid pending applications")
        return {}, []
    
    # Find existing interview channels in batch (single API call)
    user_ids = list(pending_users.keys())
    logger.info("🔎 Checking %d users for existing interview channels...", len(user_ids))
    user_to_channel = find_channels_batch(user_ids)
    
    # For each user with an existing channel, check if our message is already there
    recovered = {}
    unprocessed = []
    
    for user_id in user_ids:
        reqid = pending_users.get(user_id)
        if not reqid:
            continue
        
        channel_id = user_to_channel.get(user_id)
        
        # If there's a channel with our message, it's recovered
        if channel_id and message_already_sent(channel_id, MESSAGE_CONTENT, mention_user_id=user_id, min_ts=0.0):
            # Find the timestamp of our message
            opened_at = find_own_message_timestamp(channel_id, MESSAGE_CONTENT, mention_user_id=user_id)
            if opened_at <= 0.0:
                opened_at = time.time()
            
            recovered[user_id] = {
                "reqid": reqid,
                "channel_id": channel_id,
                "opened_at": opened_at
            }
            logger.info("♻️  Recovered existing interview: user=%s channel=%s reqid=%s", user_id, channel_id, reqid)
        else:
            # This is an old application that was never processed
            unprocessed.append({"reqid": reqid, "user_id": user_id})
    
    if recovered:
        logger.info("✅ Recovered %d existing interviews at startup", len(recovered))
    else:
        logger.info("No existing interviews to recover")
    
    if unprocessed:
        logger.info("📝 Found %d old applications that need to be opened", len(unprocessed))
    else:
        logger.info("No old applications to process")
    
    return recovered, unprocessed

def main():
    # Validate configuration at startup
    if not SERVER_INVITE_LINK:
        logger.warning("SERVER_INVITE_LINK not configured. Notifications to added users will be skipped.")
    
    # NEW: Recover existing interviews at startup (handles 100+ applications smoothly)
    logger.info("=" * 60)
    logger.info("🚀 Starting meow.py with improved parallel processing")
    logger.info("=" * 60)
    
    recovered_interviews, unprocessed_apps = recover_existing_interviews()
    
    # Handle recovered interviews (already have channels)
    if recovered_interviews:
        # Add recovered interviews to open_interviews and start monitoring
        with open_interviews_lock:
            open_interviews.update(recovered_interviews)
        
        # Mark these as seen so we don't process them again
        with seen_reqs_lock:
            for user_id, info in recovered_interviews.items():
                seen_reqs.add(info["reqid"])
        
        # Start monitoring threads for each recovered interview
        logger.info("🔄 Starting monitoring threads for %d recovered interviews", len(recovered_interviews))
        for user_id in recovered_interviews:
            # Start approval monitoring thread
            approval_thread = threading.Thread(target=monitor_user_approval, args=(user_id,))
            approval_thread.daemon = True
            approval_thread.start()
            
            # Note: We don't start followup threads for recovered interviews since they're already past that phase
        
        logger.info("✅ Recovery complete, now monitoring %d users", len(recovered_interviews))
    
    # Handle old unprocessed applications (need to open interviews)
    if unprocessed_apps:
        # Mark them as seen first to prevent the main loop from processing them concurrently
        # Note: If bot crashes before processing completes, applications remain in Discord's SUBMITTED state
        # and will be re-fetched and re-processed on next startup (safe to mark as seen here)
        with seen_reqs_lock:
            for app in unprocessed_apps:
                seen_reqs.add(app["reqid"])
        
        # Process old applications slowly in a background thread
        logger.info("🔄 Starting background thread to process %d old applications slowly", len(unprocessed_apps))
        old_apps_thread = threading.Thread(target=process_old_applications_slowly, args=(unprocessed_apps,))
        old_apps_thread.daemon = True
        old_apps_thread.name = "old-apps-processor"
        old_apps_thread.start()
    
    # NO LONGER NEEDED: Old single approval_poller thread removed
    # Now each user gets their own approval monitoring thread
    
    logger.info("=" * 60)
    logger.info("🎯 Main poller loop starting (parallel processing enabled)")
    logger.info("=" * 60)
    
    while True:
        apps = get_pending_applications()
        
        # Collect all new applications
        new_applications = []
        for app in apps:
            reqid = app.get("id")
            user_id = app.get("user_id")
            if not reqid or not user_id:
                continue

            with seen_reqs_lock:
                if reqid in seen_reqs:
                    continue
                # mark as seen immediately (prevents duplicate workers)
                seen_reqs.add(reqid)
            
            new_applications.append({"reqid": reqid, "user_id": str(user_id)})
        
        # Process all new applications in batch for maximum speed
        if new_applications:
            logger.info("📥 Found %d new applications, processing in batch", len(new_applications))
            thread = threading.Thread(target=process_application_batch, args=(new_applications,))
            thread.daemon = True
            thread.start()
        
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()
