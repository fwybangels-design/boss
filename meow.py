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

POLL_INTERVAL = 1.0  # Check for new applications every second
APPROVAL_POLL_INTERVAL = 0.2  # Fast polling for approval checking in single poller thread (was 2s in old version, 0.2s for responsiveness)
SEND_RETRY_DELAY = 1  # Retry delay for message sending
MAX_TOTAL_SEND_TIME = 180

# Channel finding configuration (simpler than old batch approach)
CHANNEL_FIND_POLL_DELAY = 0.5  # Poll every 0.5s when waiting for channel to be created
CHANNEL_FIND_TIMEOUT = 60  # Give up after 60s if channel not found

# Follow-up message timing
FOLLOW_UP_DELAY = 60  # Send follow-up reminder after 60 seconds if no screenshot uploaded

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
def process_application(reqid, user_id):
    """Process a single application - open interview, find channel, send message, start monitoring."""
    logger.info("Starting processing for reqid=%s user=%s", reqid, user_id)

    # open interview (simple behavior)
    open_interview(reqid)

    # Wait for channel to be created
    start_time = time.time()
    channel_id = None
    while time.time() - start_time < CHANNEL_FIND_TIMEOUT:
        channel_id = find_existing_interview_channel(user_id)
        if channel_id:
            break
        time.sleep(CHANNEL_FIND_POLL_DELAY)

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
        # clear prior reminder state so the user can be reminded again on re-apply
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
        # clear prior reminder state so the user can be reminded again on re-apply
        with add_two_people_reminded_lock:
            add_two_people_reminded.discard(str(user_id))
        logger.info("Sent message to %s for reqid=%s; using opened_at=%s", channel_id, reqid, opened_at)

    logger.info("Registered reqid=%s for user=%s (channel=%s opened_at=%s)", reqid, user_id, channel_id, opened_at)

    # monitor for image and follow-up
    follow_up_sent = False
    monitor_start = time.time()
    while time.time() - monitor_start < MAX_TOTAL_SEND_TIME:
        # refresh channel if user creates a new DM
        new_channel = find_existing_interview_channel(user_id)
        if new_channel and new_channel != channel_id:
            logger.info("Switching to newer channel %s for user %s", new_channel, user_id)
            channel_id = new_channel
            opened_at = time.time()
            with open_interviews_lock:
                if str(user_id) in open_interviews:
                    open_interviews[str(user_id)]["channel_id"] = channel_id
                    open_interviews[str(user_id)]["opened_at"] = opened_at

        if channel_has_image_from_user(channel_id, user_id, min_ts=opened_at):
            logger.info("Image detected for user %s in channel %s; stopping monitor.", user_id, channel_id)
            break

        elapsed = time.time() - monitor_start
        if not follow_up_sent and elapsed >= FOLLOW_UP_DELAY:
            # re-check immediately before sending follow-up to reduce races
            if not channel_has_image_from_user(channel_id, user_id, min_ts=opened_at):
                followup_composed = f"<@{user_id}>\n{FOLLOW_UP_MESSAGE}"
                send_interview_message(channel_id, followup_composed, mention_user_id=user_id)
                follow_up_sent = True
        time.sleep(2)

    logger.info("Finished monitoring reqid=%s user=%s", reqid, user_id)

def approval_poller():
    """
    Single poller thread that checks all users for approval conditions.
    This replaces the per-user approval threads for better efficiency.
    Similar to the old friend_request_poller architecture but checks for 2 people + image.
    """
    logger.info("Started approval poller thread.")
    while True:
        with open_interviews_lock:
            keys = list(open_interviews.keys())
        if not keys:
            time.sleep(APPROVAL_POLL_INTERVAL)
            continue

        with open_interviews_lock:
            to_remove = []
            for user_id in keys:
                info = open_interviews.get(user_id, {})
                reqid = info.get("reqid")
                channel_id = info.get("channel_id")
                opened_at = info.get("opened_at", 0.0)
                if not reqid or not channel_id:
                    continue
                
                has_two_people, added_users = check_two_people_added(channel_id, user_id)
                has_image = channel_has_image_from_user(channel_id, user_id, min_ts=opened_at)
                logger.info("APPROVAL POLLER: user=%s has_two_people=%s has_image=%s", user_id, has_two_people, has_image)

                # If image present but not 2 people added, send the "add 2 people" reminder once
                if has_image and not has_two_people:
                    with add_two_people_reminded_lock:
                        if user_id not in add_two_people_reminded:
                            logger.info("Attempting add-2-people reminder for user %s in channel %s", user_id, channel_id)
                            reminder = f"<@{user_id}>\n{ADD_TWO_PEOPLE_MESSAGE}"
                            sent = False
                            try:
                                sent = send_interview_message(channel_id, reminder, mention_user_id=user_id)
                            except Exception:
                                logger.exception("Exception while sending add-2-people reminder to %s", user_id)
                            if sent:
                                add_two_people_reminded.add(user_id)
                                logger.info("Sent add-2-people reminder to user %s in channel %s", user_id, channel_id)
                            else:
                                logger.warning("Failed to send add-2-people reminder to %s in channel %s; will retry later", user_id, channel_id)

                if has_two_people and has_image:
                    logger.info("Approving reqid=%s for user=%s", reqid, user_id)
                    approve_application(reqid)
                    
                    # Send notification to the 2 added users
                    logger.info("📧 Sending notification to added users for user %s in channel %s", user_id, channel_id)
                    try:
                        notify_added_users(user_id, channel_id)
                        logger.info("✅ Successfully sent notification to added users for user %s", user_id)
                    except Exception:
                        logger.exception("❌ Exception while notifying added users for %s", user_id)
                    
                    to_remove.append(user_id)

            for user_id in to_remove:
                if user_id in open_interviews:
                    del open_interviews[user_id]
                # also clear reminder state if present
                with add_two_people_reminded_lock:
                    add_two_people_reminded.discard(user_id)
        time.sleep(APPROVAL_POLL_INTERVAL)

def main():
    # Start single approval poller thread (like old friend_request_poller)
    poller_thread = threading.Thread(target=approval_poller, daemon=True)
    poller_thread.start()
    logger.info("Starting main poller loop.")
    
    while True:
        apps = get_pending_applications()
        for app in apps:
            # simple extraction like old version
            reqid = app.get("id")
            user_id = app.get("user_id")
            if not reqid or not user_id:
                continue

            with seen_reqs_lock:
                if reqid in seen_reqs:
                    continue
                # mark as seen immediately (prevents duplicate workers)
                seen_reqs.add(reqid)

            thread = threading.Thread(target=process_application, args=(reqid, str(user_id)))
            thread.daemon = True
            thread.start()
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()
