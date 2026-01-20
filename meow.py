import requests
import json
import time
import random
import threading
import logging
import tempfile
import os
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

# Timeout for all API requests (prevents hanging)
REQUEST_TIMEOUT = 10  # seconds

# Retry configuration for network requests
MAX_REQUEST_RETRIES = 3  # Maximum number of retries for network requests
RETRY_DELAY = 2  # Initial delay between retries (seconds), uses exponential backoff

# ---------------------------
# Configuration / constants
# ---------------------------
TOKEN = ""
GUILD_ID = "1460863243990859851"
OWN_USER_ID = "1425093130813968395"
OWN_USER_ID_STR = str(OWN_USER_ID)  # Pre-convert for efficient string comparisons

# Server invite link to send to the 2 users after approval
# For security, consider using environment variables instead: os.environ.get("SERVER_INVITE_LINK", "")
SERVER_INVITE_LINK = ""  # Set this to your Discord server invite link (e.g., "https://discord.gg/example")

# Your current message content / followup text (kept as you asked)
MESSAGE_CONTENT = ("Add me and **__YOU MUST__** join the tele network https://t.me/addlist/kb2V8807oMg1NGYx and it will insta accept you,\n"
                   "-# SEND A SCREENSHOT OF YOU IN THE [TELEGRAM](https://t.me/addlist/kb2V8807oMg1NGYx) TO BE ACCEPTED")

FOLLOW_UP_DELAY = 60  # seconds
FOLLOW_UP_MESSAGE = ("-# Please upload the screenshot of you in the [Telegram channel](https://t.me/addlist/kb2V8807oMg1NGYx) so we can approve you.\n"
                     "-# If you've already uploaded it, give it a moment to appear.")

# NEW: special reminder message when a user posts an image but hasn't added 2 people to the group DM yet
ADD_TWO_PEOPLE_MESSAGE = ("-# Please also add 2 people to this group DM so we can accept you.\n"
                          "-# uploading a screenshot alone isn't enough. If you've already added them, give it a moment to appear.")

# NEW: special reminder message when a user adds 2 people but hasn't uploaded a screenshot yet
UPLOAD_SCREENSHOT_MESSAGE = ("-# Great! We see you've added 2 people. Now please upload the screenshot of you in the [Telegram channel](https://t.me/addlist/kb2V8807oMg1NGYx) so we can approve you.\n"
                             "-# If you've already uploaded it, give it a moment to appear.")

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

POLL_INTERVAL = 1
APPROVAL_POLL_INTERVAL = 2.0  # Reduced API load - check every 2 seconds instead of 0.2s
SEND_RETRY_DELAY = 1
MAX_TOTAL_SEND_TIME = 180

# Optimized polling configuration for faster application opening
# Start with fast polling (0.1s) for immediate response in typical cases
# Use 2.0x backoff multiplier to quickly reduce API load while still being responsive
# Cap at 2.0s to balance responsiveness with API efficiency
INITIAL_POLL_DELAY = 0.1  # Initial delay provides near-instant response (100ms)
MAX_POLL_DELAY = 2.0  # Maximum delay balances API load with reasonable retry speed
BACKOFF_MULTIPLIER = 2.0  # Aggressive backoff for efficient API usage (0.1→0.2→0.4→0.8→1.6→2.0s)

# Monitoring loop configuration  
MONITOR_POLL_INTERVAL = 1.0  # 1 second provides responsive image detection without excessive API calls
CHANNEL_REFRESH_INTERVAL = 10.0  # Check for new channels infrequently since it's a rare edge case

# Concurrent processing configuration
MAX_WORKERS = 50  # Maximum number of concurrent threads for processing applications

# Batch processing timing constants
CHANNEL_CREATION_DELAY = 0.5  # Delay after opening interviews to allow Discord to create channels
MAX_CHANNEL_FIND_RETRIES = 5  # Maximum retries for finding newly created channels
CHANNEL_FIND_RETRY_DELAY = 0.5  # Delay between channel finding retries

# Staggered opening configuration (NEW)
STAGGER_OPEN_DELAY = 0.7  # Delay between opening each new interview (0.5-1 seconds)
initial_startup = True  # Flag to track if this is the first batch (for staggered opening)
initial_startup_lock = threading.Lock()

# Persistent state file
STATE_FILE = "meow_state.json"

# Auto-save interval (save state every N seconds to handle restarts better)
AUTO_SAVE_INTERVAL = 30  # seconds
MAX_APPLICATION_PAGES = 10  # Maximum pages to fetch (10 pages * 100 = 1000 max applications)

# Cleanup interval for tracking sets (prevent memory leaks)
TRACKING_SET_CLEANUP_INTERVAL = 300  # seconds (5 minutes)
MAX_TRACKING_SET_SIZE = 10000  # Maximum entries in tracking sets before cleanup

# Empty GC cleanup configuration
EMPTY_GC_CLEANUP_INTERVAL = 600  # seconds (10 minutes) - check for empty GCs to leave after first scan
EMPTY_GC_CLEANUP_ENABLED = True  # Set to False to disable empty GC cleanup

last_save_time = time.time()  # Initialize to current time to prevent immediate save
last_save_time_lock = threading.Lock()
last_cleanup_time = time.time()
last_cleanup_time_lock = threading.Lock()
last_empty_gc_cleanup_time = 0  # Set to 0 to trigger immediate cleanup on startup
last_empty_gc_cleanup_time_lock = threading.Lock()

# in-memory state
seen_reqs = set()
open_interviews = {}
open_interviews_lock = threading.Lock()
seen_reqs_lock = threading.Lock()

# NEW: track which users we've sent the "add 2 people" reminder to (in-memory only)
add_two_people_reminded = set()
add_two_people_reminded_lock = threading.Lock()

# NEW: track which users we've sent the "upload screenshot" reminder to (in-memory only)
upload_screenshot_reminded = set()
upload_screenshot_reminded_lock = threading.Lock()

# NEW: track timestamps when reminders were first sent for 30-minute follow-ups
# Format: {user_id: timestamp}
add_two_people_reminder_times = {}
add_two_people_reminder_times_lock = threading.Lock()

upload_screenshot_reminder_times = {}
upload_screenshot_reminder_times_lock = threading.Lock()

# 30-minute follow-up reminder delay (in seconds)
SECOND_REMINDER_DELAY = 30 * 60  # 30 minutes

# Thread pool for approval checking to avoid creating new pools on each iteration
approval_executor = ThreadPoolExecutor(max_workers=MAX_WORKERS, thread_name_prefix="approval-")

# Logging
VERBOSE = False
logger = logging.getLogger("discord_auto_accept")
logger.setLevel(logging.DEBUG if VERBOSE else logging.INFO)
ch = logging.StreamHandler()
ch.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logger.addHandler(ch)

# Helpers
def save_state():
    """Save the current state to disk for persistence across restarts."""
    global last_save_time
    try:
        # Acquire locks to prevent race conditions
        with seen_reqs_lock:
            seen_reqs_copy = list(seen_reqs)
        
        with open_interviews_lock:
            open_interviews_copy = {k: v for k, v in open_interviews.items()}
        
        state = {
            "seen_reqs": seen_reqs_copy,
            "open_interviews": open_interviews_copy
        }
        
        # Atomic write: write to temp file then rename (prevents corruption on crash)
        temp_fd, temp_path = tempfile.mkstemp(dir=os.path.dirname(STATE_FILE) or '.', prefix='.meow_state_', suffix='.tmp')
        try:
            with os.fdopen(temp_fd, 'w') as f:
                json.dump(state, f, indent=2)
            os.replace(temp_path, STATE_FILE)  # Atomic rename
        except Exception:
            # Clean up temp file on failure
            try:
                os.unlink(temp_path)
            except Exception:
                pass
            raise
        
        # Update timestamp only after successful write
        with last_save_time_lock:
            last_save_time = time.time()
        
        logger.debug("State saved to %s (%d seen_reqs, %d open_interviews)", 
                    STATE_FILE, len(seen_reqs_copy), len(open_interviews_copy))
    except Exception:
        logger.exception("Failed to save state")

def auto_save_state_if_needed():
    """Auto-save state if enough time has passed since last save."""
    global last_save_time
    with last_save_time_lock:
        current_time = time.time()
        time_since_last_save = current_time - last_save_time
    
    if time_since_last_save >= AUTO_SAVE_INTERVAL:
        logger.debug("Auto-saving state (%.1fs since last save)", time_since_last_save)
        save_state()

def cleanup_tracking_sets():
    """Clean up old entries from tracking sets to prevent memory leaks."""
    global last_cleanup_time
    
    with last_cleanup_time_lock:
        current_time = time.time()
        time_since_last_cleanup = current_time - last_cleanup_time
    
    if time_since_last_cleanup < TRACKING_SET_CLEANUP_INTERVAL:
        return  # Not time to cleanup yet
    
    try:
        # Clean up seen_reqs by removing entries not in open_interviews
        with open_interviews_lock:
            active_user_ids = set(open_interviews.keys())
        
        # Note: seen_reqs stores request IDs not user IDs, so we use FIFO with cap
        # Warning: Python sets are unordered in Python < 3.7, but insertion-ordered in 3.7+
        # We rely on Python 3.7+ insertion order for FIFO cleanup
        with seen_reqs_lock:
            if len(seen_reqs) > MAX_TRACKING_SET_SIZE:
                # Convert to list to maintain order (Python 3.7+ preserves insertion order in sets)
                seen_reqs_list = list(seen_reqs)
                keep_size = MAX_TRACKING_SET_SIZE // 2
                seen_reqs.clear()
                # Keep the most recent entries (last 50% of max size)
                seen_reqs.update(seen_reqs_list[-keep_size:])
                logger.info("Cleaned up seen_reqs: kept %d of %d entries", keep_size, len(seen_reqs_list))
        
        # Clean up reminder sets by removing inactive users
        with add_two_people_reminded_lock:
            add_two_people_reminded.intersection_update(active_user_ids)
        
        with upload_screenshot_reminded_lock:
            upload_screenshot_reminded.intersection_update(active_user_ids)
        
        with last_cleanup_time_lock:
            last_cleanup_time = time.time()
        
        logger.debug("Cleaned up tracking sets")
    except Exception:
        logger.exception("Failed to cleanup tracking sets")

def leave_channel(channel_id):
    """Leave a Discord channel/group DM."""
    url = f"https://discord.com/api/v9/channels/{channel_id}"
    headers = HEADERS_TEMPLATE.copy()
    headers["content-type"] = "application/json"
    try:
        resp = requests.delete(url, headers=headers, cookies=COOKIES, timeout=REQUEST_TIMEOUT)
        _log_resp_short(f"leave_channel {channel_id}", resp)
        if resp and resp.status_code in (200, 204):
            logger.info("Successfully left channel %s", channel_id)
            return True
        else:
            logger.warning("Failed to leave channel %s status=%s", channel_id, getattr(resp, "status_code", "N/A"))
            return False
    except Exception:
        logger.exception("Exception leaving channel %s", channel_id)
        return False

def cleanup_empty_group_chats():
    """
    Clean up empty group chats where only the bot remains.
    Safely identifies and leaves GCs with only 1 recipient (the bot itself).
    Also removes these users from open_interviews to prevent re-messaging.
    """
    global last_empty_gc_cleanup_time
    
    if not EMPTY_GC_CLEANUP_ENABLED:
        return  # Feature disabled
    
    with last_empty_gc_cleanup_time_lock:
        current_time = time.time()
        time_since_last_cleanup = current_time - last_empty_gc_cleanup_time
    
    if time_since_last_cleanup < EMPTY_GC_CLEANUP_INTERVAL:
        return  # Not time to cleanup yet
    
    try:
        logger.info("Checking for empty group chats to leave...")
        
        # Get all channels
        url = "https://discord.com/api/v9/users/@me/channels"
        headers = HEADERS_TEMPLATE.copy()
        headers.pop("content-type", None)
        
        resp = requests.get(url, headers=headers, cookies=COOKIES, timeout=REQUEST_TIMEOUT)
        _log_resp_short("cleanup_empty_group_chats", resp)
        
        if not resp or resp.status_code != 200:
            logger.warning("Failed to fetch channels for empty GC cleanup")
            return
        
        channels = resp.json() if isinstance(resp.text, str) else []
        if not isinstance(channels, list):
            logger.warning("Invalid channels response for empty GC cleanup")
            return
        
        # Get currently active interview channels
        with open_interviews_lock:
            active_channel_to_user = {info.get("channel_id"): user_id 
                                      for user_id, info in open_interviews.items() 
                                      if info.get("channel_id")}
        
        empty_gcs_to_leave = []
        users_to_remove = []
        
        # Find group DMs (type 3) with only 1 recipient (the bot itself)
        for channel in channels:
            if not isinstance(channel, dict):
                continue
            
            channel_id = channel.get("id")
            channel_type = channel.get("type")
            
            # Only process group DMs (type 3)
            if channel_type != 3:
                continue
            
            # Get recipients for this channel
            recipients = channel.get("recipients", [])
            
            # Count recipients (should only have the bot if everyone left)
            # Note: The bot itself is NOT included in the recipients list
            # So if recipients is empty, it means only the bot is in the GC
            if len(recipients) == 0:
                logger.info("Found empty GC %s with 0 recipients (only bot remaining)", channel_id)
                empty_gcs_to_leave.append(channel_id)
                
                # If this is an active interview channel, mark user for removal
                if channel_id in active_channel_to_user:
                    user_id = active_channel_to_user[channel_id]
                    users_to_remove.append(user_id)
                    logger.info("Will remove user %s from open_interviews (empty GC)", user_id)
            else:
                logger.debug("Channel %s has %d recipients, keeping", channel_id, len(recipients))
        
        # Remove users from open_interviews first (before leaving channels)
        if users_to_remove:
            with open_interviews_lock:
                for user_id in users_to_remove:
                    if user_id in open_interviews:
                        del open_interviews[user_id]
                        logger.info("Removed user %s from open_interviews (empty GC)", user_id)
            
            # Also remove from reminder tracking
            with add_two_people_reminded_lock:
                for user_id in users_to_remove:
                    add_two_people_reminded.discard(user_id)
            
            with upload_screenshot_reminded_lock:
                for user_id in users_to_remove:
                    upload_screenshot_reminded.discard(user_id)
            
            with add_two_people_reminder_times_lock:
                for user_id in users_to_remove:
                    add_two_people_reminder_times.pop(user_id, None)
            
            with upload_screenshot_reminder_times_lock:
                for user_id in users_to_remove:
                    upload_screenshot_reminder_times.pop(user_id, None)
        
        # Leave empty GCs
        if empty_gcs_to_leave:
            logger.info("Leaving %d empty group chat(s)", len(empty_gcs_to_leave))
            for channel_id in empty_gcs_to_leave:
                leave_channel(channel_id)
                time.sleep(0.5)  # Rate limit protection
        else:
            logger.info("No empty group chats found to leave")
        
        # Update last cleanup time
        with last_empty_gc_cleanup_time_lock:
            last_empty_gc_cleanup_time = time.time()
        
        logger.debug("Empty GC cleanup completed")
    except Exception:
        logger.exception("Failed to cleanup empty group chats")

def load_state():
    """Load state from disk on startup to resume incomplete applications."""
    global seen_reqs, open_interviews
    try:
        with open(STATE_FILE, 'r') as f:
            state = json.load(f)
        
        with seen_reqs_lock:
            seen_reqs = set(state.get("seen_reqs", []))
        
        with open_interviews_lock:
            open_interviews = state.get("open_interviews", {})
            # Get a copy of keys for safe iteration
            user_ids_to_resume = list(open_interviews.keys())
        
        logger.info("State loaded from %s: %d seen_reqs, %d open_interviews", 
                   STATE_FILE, len(seen_reqs), len(user_ids_to_resume))
        
        # Resume monitoring for all incomplete interviews
        for user_id in user_ids_to_resume:
            logger.info("Resuming monitoring for user %s", user_id)
            thread = threading.Thread(target=monitor_user_followup, args=(user_id,))
            thread.daemon = True
            thread.start()
            
    except FileNotFoundError:
        logger.info("No existing state file found, starting fresh")
    except Exception:
        logger.exception("Failed to load state, starting fresh")

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
    """Fetch all pending applications with pagination to handle 250+ applications."""
    all_apps = []
    after = None
    
    headers = HEADERS_TEMPLATE.copy()
    headers["referer"] = f"https://discord.com/channels/{GUILD_ID}/member-safety"
    
    for page in range(MAX_APPLICATION_PAGES):
        try:
            url = f"https://discord.com/api/v9/guilds/{GUILD_ID}/requests?status=SUBMITTED&limit=100"
            if after:
                url += f"&after={after}"
            
            resp = requests.get(url, headers=headers, cookies=COOKIES, timeout=REQUEST_TIMEOUT)
            _log_resp_short(f"get_pending_applications (page {page + 1})", resp)
            
            if not resp or resp.status_code != 200:
                break
            
            try:
                data = resp.json()
            except Exception:
                logger.warning("Failed to parse JSON response on page %d", page + 1)
                break
                
            apps = data.get("guild_join_requests", []) if isinstance(data, dict) else []
            
            if not apps:
                break  # No more applications
            
            # Filter to only include applications with status SUBMITTED
            # This prevents processing already approved/rejected applications
            # Note: Discord API returns None for status field when application is SUBMITTED (default state)
            filtered_apps = []
            for app in apps:
                status = app.get("application_status")
                if status == "SUBMITTED" or status is None:  # None means default SUBMITTED state
                    filtered_apps.append(app)
                else:
                    logger.debug("Skipping application %s with status %s", app.get("id"), status)
            
            all_apps.extend(filtered_apps)
            logger.info("Fetched %d applications on page %d (total so far: %d)", len(filtered_apps), page + 1, len(all_apps))
            
            # Check if there are more pages
            if len(apps) < 100:
                break  # Last page (fewer than 100 results)
            
            # Use the last application's ID as the cursor for next page
            after = apps[-1].get("id")
            if not after:
                break
            
        except Exception:
            logger.exception("Error fetching pending applications page %d", page + 1)
            break
    
    logger.info("Fetched total of %d pending applications", len(all_apps))
    return all_apps

def open_interview(request_id):
    url = f"https://discord.com/api/v9/join-requests/{request_id}/interview"
    headers = HEADERS_TEMPLATE.copy()
    headers["referer"] = f"https://discord.com/channels/{GUILD_ID}/member-safety"
    headers["content-type"] = "application/json"
    try:
        resp = requests.post(url, headers=headers, cookies=COOKIES)
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
        resp = requests.get(url, headers=headers, cookies=COOKIES, timeout=REQUEST_TIMEOUT)
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
        resp = requests.get(url, headers=headers, cookies=COOKIES, timeout=REQUEST_TIMEOUT)
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
    """Get the list of recipient user IDs in a group DM channel."""
    url = f"https://discord.com/api/v9/channels/{channel_id}"
    headers = HEADERS_TEMPLATE.copy()
    headers["referer"] = f"https://discord.com/channels/@me/{channel_id}"
    # Remove content-type header for GET requests (not needed and may cause issues)
    headers.pop("content-type", None)
    
    max_retries = 2
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, headers=headers, cookies=COOKIES, timeout=10)
            _log_resp_short("get_channel_recipients", resp)
            
            if resp and resp.status_code == 200:
                channel_data = resp.json()
                recipients = channel_data.get("recipients", [])
                recipient_ids = [u.get("id") for u in recipients if isinstance(u, dict) and "id" in u]
                logger.debug("Channel %s has %d recipients", channel_id, len(recipient_ids))
                return recipient_ids
            elif resp and resp.status_code == 429:
                # Rate limited
                try:
                    retry_after = float(resp.json().get("retry_after", 1))
                except Exception:
                    retry_after = 1
                logger.warning("Rate limited in get_channel_recipients, waiting %s seconds", retry_after)
                time.sleep(retry_after)
            else:
                logger.warning("Failed to get channel recipients status=%s", getattr(resp, "status_code", "N/A"))
                if attempt < max_retries - 1:
                    time.sleep(0.5)
        except Exception as e:
            logger.exception("Exception getting channel recipients: %s", str(e))
            if attempt < max_retries - 1:
                time.sleep(0.5)
    
    return []

def get_channel_recipients_batch(channel_ids):
    """Get recipients for multiple channels concurrently using thread pool."""
    if not channel_ids:
        return {}
    
    logger.debug("Getting recipients for %d channels concurrently", len(channel_ids))
    channel_to_recipients = {}
    
    with ThreadPoolExecutor(max_workers=min(len(channel_ids), MAX_WORKERS)) as executor:
        future_to_channel = {executor.submit(get_channel_recipients, cid): cid for cid in channel_ids}
        for future in as_completed(future_to_channel):
            channel_id = future_to_channel[future]
            try:
                recipients = future.result()
                channel_to_recipients[channel_id] = recipients
            except Exception:
                logger.exception("Exception in batch channel recipients fetching for %s", channel_id)
                channel_to_recipients[channel_id] = []
    
    return channel_to_recipients

def filter_added_users(recipients, applicant_user_id):
    """
    Filter recipients to get only added users (excluding bot and applicant).
    Returns list of added user IDs.
    """
    applicant_id_str = str(applicant_user_id)
    return [
        uid for uid in recipients 
        if str(uid) != OWN_USER_ID_STR and str(uid) != applicant_id_str
    ]

def check_two_people_added(channel_id, applicant_user_id):
    """
    Check if the applicant has added 2 people to the group DM.
    Returns (bool, list of added user IDs excluding bot and applicant).
    """
    recipients = get_channel_recipients(channel_id)
    if not recipients:
        return False, []
    
    added_users = filter_added_users(recipients, applicant_user_id)
    
    # Need at least 2 people added
    has_two_people = len(added_users) >= 2
    return has_two_people, added_users


def message_already_sent(channel_id, content_without_mention, mention_user_id=None, min_ts=0.0):
    url = f"https://discord.com/api/v9/channels/{channel_id}/messages?limit=50"
    headers = HEADERS_TEMPLATE.copy()
    headers["referer"] = f"https://discord.com/channels/@me/{channel_id}"
    headers.pop("content-type", None)
    
    # Retry with exponential backoff for SSL and transient errors
    for attempt in range(MAX_REQUEST_RETRIES):
        try:
            resp = requests.get(url, headers=headers, cookies=COOKIES, timeout=REQUEST_TIMEOUT)
            _log_resp_short("message_already_sent", resp)
            
            if resp and resp.status_code == 429:
                try:
                    data = resp.json()
                    retry_after = float(data.get("retry_after", 2))
                except Exception:
                    retry_after = 2.0
                logger.warning("Rate limited in message_already_sent, waiting %s seconds", retry_after)
                time.sleep(retry_after)
                continue  # Retry after rate limit
            
            messages = resp.json() if resp and resp.status_code == 200 else []
            if not isinstance(messages, list):
                if attempt < MAX_REQUEST_RETRIES - 1:
                    time.sleep(RETRY_DELAY * (2 ** attempt))
                    continue
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
        except (requests.exceptions.SSLError, requests.exceptions.ConnectionError) as e:
            logger.warning("Network error in message_already_sent (attempt %d/%d): %s", 
                          attempt + 1, MAX_REQUEST_RETRIES, str(e))
            if attempt < MAX_REQUEST_RETRIES - 1:
                time.sleep(RETRY_DELAY * (2 ** attempt))  # Exponential backoff
        except Exception:
            logger.exception("Exception in message_already_sent")
            # When in doubt after exception, assume message was sent to avoid duplicates
            logger.warning("Exception in message_already_sent - returning True to avoid duplicate messages")
            return True
    
    logger.warning("Failed to check if message was sent after %d retries, assuming it was sent to avoid duplicates", MAX_REQUEST_RETRIES)
    return True  # Assume message was sent to avoid duplicates

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
    
    # Retry with exponential backoff for SSL and transient errors
    for attempt in range(MAX_REQUEST_RETRIES):
        try:
            resp = requests.get(url, headers=headers, cookies=COOKIES, timeout=REQUEST_TIMEOUT)
            _log_resp_short("find_own_message_timestamp", resp)
            
            if resp and resp.status_code == 429:
                try:
                    data = resp.json()
                    retry_after = float(data.get("retry_after", 2))
                except Exception:
                    retry_after = 2.0
                logger.warning("Rate limited in find_own_message_timestamp, waiting %s seconds", retry_after)
                time.sleep(retry_after)
                continue  # Retry after rate limit
            
            messages = resp.json() if resp and getattr(resp, "status_code", None) == 200 else []
            if not isinstance(messages, list):
                if attempt < MAX_REQUEST_RETRIES - 1:
                    time.sleep(RETRY_DELAY * (2 ** attempt))
                    continue
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
        except (requests.exceptions.SSLError, requests.exceptions.ConnectionError) as e:
            logger.warning("Network error in find_own_message_timestamp (attempt %d/%d): %s", 
                          attempt + 1, MAX_REQUEST_RETRIES, str(e))
            if attempt < MAX_REQUEST_RETRIES - 1:
                time.sleep(RETRY_DELAY * (2 ** attempt))  # Exponential backoff
        except Exception:
            logger.exception("[!] Exception in find_own_message_timestamp")
            return 0.0
    
    logger.warning("Failed to find own message timestamp after %d retries", MAX_REQUEST_RETRIES)
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
    
    # Retry with exponential backoff for SSL and transient errors
    for attempt in range(MAX_REQUEST_RETRIES):
        try:
            resp = requests.post(url, headers=headers, cookies=COOKIES, data=json.dumps(data), timeout=REQUEST_TIMEOUT)
            _log_resp_short(f"send_interview_message to {channel_id}", resp)
            
            if getattr(resp, "status_code", None) == 429:
                try:
                    retry_data = resp.json()
                    retry_after = float(retry_data.get("retry_after", 2))
                except Exception:
                    retry_after = 2.0
                logger.warning("Rate limited in send_interview_message, waiting %s seconds", retry_after)
                time.sleep(retry_after)
                continue  # Retry after rate limit
            
            if getattr(resp, "status_code", None) in (200, 201):
                logger.info("Sent message to channel %s", channel_id)
                return True
            else:
                logger.warning("Failed to send message to %s status=%s", channel_id, getattr(resp, "status_code", "N/A"))
                if attempt < MAX_REQUEST_RETRIES - 1:
                    time.sleep(RETRY_DELAY * (2 ** attempt))
                    continue
                return False
        except (requests.exceptions.SSLError, requests.exceptions.ConnectionError) as e:
            logger.warning("Network error in send_interview_message (attempt %d/%d): %s", 
                          attempt + 1, MAX_REQUEST_RETRIES, str(e))
            if attempt < MAX_REQUEST_RETRIES - 1:
                time.sleep(RETRY_DELAY * (2 ** attempt))  # Exponential backoff
        except Exception:
            logger.exception("Exception sending message")
            return False
    
    logger.error("Failed to send message after %d retries", MAX_REQUEST_RETRIES)
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
    Implements retry logic with exponential backoff for reliability.
    """
    if not SERVER_INVITE_LINK:
        logger.warning("SERVER_INVITE_LINK not configured. Skipping notification to added users.")
        return
    
    # Small delay to ensure Discord state is consistent after approval
    time.sleep(0.2)
    
    # Get the list of users who were added to the group DM
    _, added_users = check_two_people_added(channel_id, applicant_user_id)
    if len(added_users) < 2:
        logger.warning("Less than 2 people added to group DM for applicant %s, skipping notification", applicant_user_id)
        return
    
    # Take the first 2 users who were added
    user1 = added_users[0]
    user2 = added_users[1]
    
    # Send message mentioning the 2 users with the server invite
    message = f"<@{user1}> <@{user2}> join {SERVER_INVITE_LINK} so i can let u in"
    
    # Retry logic with exponential backoff (3 attempts max)
    max_retries = 3
    retry_delay = 1.0
    for attempt in range(max_retries):
        try:
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
            
            resp = requests.post(url, headers=headers, cookies=COOKIES, data=json.dumps(data), timeout=10)
            _log_resp_short(f"notify_added_users to {channel_id}", resp)
            
            if getattr(resp, "status_code", None) in (200, 201):
                logger.info("Sent notification to users %s and %s in channel %s", user1, user2, channel_id)
                return  # Success, exit function
            elif getattr(resp, "status_code", None) == 429:
                # Rate limited - get retry_after from response
                try:
                    retry_after = float(resp.json().get("retry_after", retry_delay))
                except Exception:
                    retry_after = retry_delay
                logger.warning("Rate limited on notification attempt %d, waiting %s seconds", attempt + 1, retry_after)
                time.sleep(retry_after)
            else:
                logger.warning("Failed to send notification attempt %d status=%s", attempt + 1, getattr(resp, "status_code", "N/A"))
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
        except Exception as e:
            logger.exception("Exception sending notification attempt %d: %s", attempt + 1, str(e))
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
    
    logger.error("Failed to send notification to users %s and %s after %d attempts", user1, user2, max_retries)


def approve_application(request_id):
    url = f"https://discord.com/api/v9/guilds/{GUILD_ID}/requests/id/{request_id}"
    headers = HEADERS_TEMPLATE.copy()
    headers["content-type"] = "application/json"
    headers["referer"] = f"https://discord.com/channels/{GUILD_ID}/member-safety"
    data = {"action": "APPROVED"}
    try:
        resp = requests.patch(url, headers=headers, cookies=COOKIES, data=json.dumps(data), timeout=REQUEST_TIMEOUT)
        _log_resp_short(f"approve_application {request_id}", resp)
        if getattr(resp, "status_code", None) == 200:
            logger.info("Approved application %s", request_id)
        else:
            logger.warning("Failed to approve application %s status=%s", request_id, getattr(resp, "status_code", "N/A"))
    except Exception:
        logger.exception("Exception approving application")



def channel_has_image_from_user(channel_id, user_id, min_ts=0.0):
    url = f"https://discord.com/api/v9/channels/{channel_id}/messages?limit=50"
    headers = HEADERS_TEMPLATE.copy()
    headers["referer"] = f"https://discord.com/channels/@me/{channel_id}"
    headers.pop("content-type", None)
    
    # Retry with exponential backoff for SSL and transient errors
    for attempt in range(MAX_REQUEST_RETRIES):
        try:
            resp = requests.get(url, headers=headers, cookies=COOKIES, timeout=REQUEST_TIMEOUT)
            _log_resp_short("channel_has_image_from_user", resp)
            
            if getattr(resp, "status_code", None) == 429:
                try:
                    data = resp.json()
                    retry = float(data.get("retry_after", 2))
                except Exception:
                    retry = 2.0
                logger.warning("Rate limited in channel_has_image_from_user, waiting %s seconds", retry)
                time.sleep(retry)
                continue  # Retry after rate limit
            
            messages = resp.json() if getattr(resp, "status_code", None) == 200 else []
            if not isinstance(messages, list):
                return False
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
                        logger.info("Found image attachment in channel %s from user %s: %s", channel_id, user_id, filename)
                        return True
            return False
        except (requests.exceptions.SSLError, requests.exceptions.ConnectionError) as e:
            logger.warning("Network error in channel_has_image_from_user (attempt %d/%d): %s", 
                          attempt + 1, MAX_REQUEST_RETRIES, str(e))
            if attempt < MAX_REQUEST_RETRIES - 1:
                time.sleep(RETRY_DELAY * (2 ** attempt))  # Exponential backoff
        except Exception:
            logger.exception("Exception in channel_has_image_from_user")
            return False
    
    logger.error("Failed to check for image after %d retries, returning False to avoid duplicate messages", MAX_REQUEST_RETRIES)
    return False

def check_images_batch(channel_user_pairs):
    """Check for images in multiple channels concurrently."""
    if not channel_user_pairs:
        return {}
    
    logger.debug("Checking images for %d channels concurrently", len(channel_user_pairs))
    results = {}
    
    def check_image_for_pair(pair):
        channel_id, user_id, min_ts = pair
        has_image = channel_has_image_from_user(channel_id, user_id, min_ts)
        return (channel_id, has_image)
    
    with ThreadPoolExecutor(max_workers=min(len(channel_user_pairs), MAX_WORKERS)) as executor:
        futures = {executor.submit(check_image_for_pair, pair): pair for pair in channel_user_pairs}
        for future in as_completed(futures):
            try:
                channel_id, has_image = future.result()
                results[channel_id] = has_image
            except Exception:
                pair = futures[future]
                logger.exception("Exception in batch image checking for channel %s", pair[0])
                results[pair[0]] = False
    
    return results

# ---------------------------
# Main behaviors (staggered processing for stability on startup, instant for runtime)
# ---------------------------
def process_applications(applications, use_stagger=False):
    """
    Process multiple applications.
    - use_stagger=True: Staggered opening for startup backlog (to prevent bugs)
    - use_stagger=False: Instant batch processing for new applications during runtime
    """
    if not applications:
        return
    
    if use_stagger:
        logger.info("Processing %d applications with staggered opening (%.1fs delay between each)", 
                    len(applications), STAGGER_OPEN_DELAY)
        
        for i, app in enumerate(applications):
            reqid = app['reqid']
            user_id = str(app['user_id'])
            
            logger.info("Processing application %d/%d: reqid=%s user=%s", 
                       i + 1, len(applications), reqid, user_id)
            
            # Open interview
            open_interview(reqid)
            
            # Wait for channel to be created
            time.sleep(CHANNEL_CREATION_DELAY)
            
            # Find channel with retries
            channel_id = None
            for retry in range(MAX_CHANNEL_FIND_RETRIES):
                channel_id = find_existing_interview_channel(user_id)
                if channel_id:
                    break
                time.sleep(CHANNEL_FIND_RETRY_DELAY)
            
            if not channel_id:
                logger.warning("Could not find channel for user %s after retries", user_id)
                continue
            
            # Check if message already sent (on restart scenario)
            if message_already_sent(channel_id, MESSAGE_CONTENT, mention_user_id=user_id, min_ts=0.0):
                prior_ts = find_own_message_timestamp(channel_id, MESSAGE_CONTENT, mention_user_id=user_id)
                opened_at = prior_ts if prior_ts > 0.0 else time.time()
                logger.info("Message already present in %s (restart scenario). Will not re-send.", channel_id)
                with open_interviews_lock:
                    open_interviews[user_id] = {"reqid": reqid, "channel_id": channel_id, "opened_at": opened_at}
                with add_two_people_reminded_lock:
                    add_two_people_reminded.discard(user_id)
                with upload_screenshot_reminded_lock:
                    upload_screenshot_reminded.discard(user_id)
            else:
                # Send initial message
                composed_message = f"<@{user_id}>\n{MESSAGE_CONTENT}"
                sent_ok = send_interview_message(channel_id, composed_message, mention_user_id=user_id)
                
                if sent_ok:
                    sent_ts = find_own_message_timestamp(channel_id, MESSAGE_CONTENT, mention_user_id=user_id)
                    opened_at = sent_ts if sent_ts > 0.0 else time.time()
                    
                    with open_interviews_lock:
                        open_interviews[user_id] = {"reqid": reqid, "channel_id": channel_id, "opened_at": opened_at}
                    with add_two_people_reminded_lock:
                        add_two_people_reminded.discard(user_id)
                    with upload_screenshot_reminded_lock:
                        upload_screenshot_reminded.discard(user_id)
                    logger.info("Registered user %s (channel=%s, reqid=%s)", user_id, channel_id, reqid)
                else:
                    logger.warning("Failed to send message for user %s", user_id)
                    continue
            
            # Start monitoring thread for this user
            thread = threading.Thread(target=monitor_user_followup, args=(user_id,))
            thread.daemon = True
            thread.start()
            
            # Stagger the opening of interviews to avoid bugs
            if i < len(applications) - 1:  # Don't delay after the last one
                time.sleep(STAGGER_OPEN_DELAY)
        
        # Save state once after processing entire batch (more efficient than per-application saves)
        save_state()
        logger.info("Completed staggered processing of %d applications", len(applications))
    
    else:
        # Instant batch processing for new applications during runtime
        logger.info("Processing %d applications instantly (batch mode)", len(applications))
        
        # Step 1: Open all interviews concurrently
        request_ids = [app['reqid'] for app in applications]
        open_interviews_batch(request_ids)
        
        # Step 2: Wait a bit for channels to be created, then find all channels in one API call
        time.sleep(CHANNEL_CREATION_DELAY)
        user_ids = [app['user_id'] for app in applications]
        user_to_channel = find_channels_batch(user_ids)
        
        # Step 3: For users without channels yet, retry a few times
        missing_users = [uid for uid in user_ids if str(uid) not in user_to_channel]
        retry_count = 0
        while missing_users and retry_count < MAX_CHANNEL_FIND_RETRIES:
            time.sleep(CHANNEL_FIND_RETRY_DELAY)
            new_channels = find_channels_batch(missing_users)
            user_to_channel.update(new_channels)
            missing_users = [uid for uid in missing_users if str(uid) not in user_to_channel]
            retry_count += 1
        
        # Step 4: Prepare messages to send
        messages_to_send = []
        for app in applications:
            user_id = str(app['user_id'])
            channel_id = user_to_channel.get(user_id)
            if not channel_id:
                logger.warning("Could not find channel for user %s after retries", user_id)
                continue
            
            # Check if message already sent
            if message_already_sent(channel_id, MESSAGE_CONTENT, mention_user_id=user_id, min_ts=0.0):
                prior_ts = find_own_message_timestamp(channel_id, MESSAGE_CONTENT, mention_user_id=user_id)
                opened_at = prior_ts if prior_ts > 0.0 else time.time()
                logger.info("Message already present in %s. Will not re-send.", channel_id)
                with open_interviews_lock:
                    open_interviews[user_id] = {"reqid": app['reqid'], "channel_id": channel_id, "opened_at": opened_at}
                with add_two_people_reminded_lock:
                    add_two_people_reminded.discard(user_id)
                with upload_screenshot_reminded_lock:
                    upload_screenshot_reminded.discard(user_id)
            else:
                composed_message = f"<@{user_id}>\n{MESSAGE_CONTENT}"
                messages_to_send.append((channel_id, composed_message, user_id))
        
        # Step 5: Send all messages concurrently
        if messages_to_send:
            send_results = send_messages_batch(messages_to_send)
            
            # Step 6: Register successful sends in open_interviews
            for channel_id, message, user_id in messages_to_send:
                if send_results.get(channel_id, False):
                    sent_ts = find_own_message_timestamp(channel_id, MESSAGE_CONTENT, mention_user_id=user_id)
                    opened_at = sent_ts if sent_ts > 0.0 else time.time()
                    
                    # Find the reqid for this user
                    reqid = None
                    for app in applications:
                        if str(app['user_id']) == str(user_id):
                            reqid = app['reqid']
                            break
                    
                    if reqid:
                        with open_interviews_lock:
                            open_interviews[user_id] = {"reqid": reqid, "channel_id": channel_id, "opened_at": opened_at}
                        with add_two_people_reminded_lock:
                            add_two_people_reminded.discard(user_id)
                        with upload_screenshot_reminded_lock:
                            upload_screenshot_reminded.discard(user_id)
                        logger.info("Registered user %s (channel=%s, reqid=%s)", user_id, channel_id, reqid)
        
        # Save state after batch processing
        save_state()
        
        # Step 7: Start monitoring threads for each application
        for app in applications:
            user_id = str(app['user_id'])
            if user_id in open_interviews:
                thread = threading.Thread(target=monitor_user_followup, args=(user_id,))
                thread.daemon = True
                thread.start()
        
        logger.info("Completed instant batch processing of %d applications", len(applications))

def monitor_user_followup(user_id):
    """Monitor a user for image upload and send follow-up if needed."""
    try:
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
    except Exception:
        logger.exception("Exception in monitor_user_followup for user %s", user_id)

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

def approval_poller():
    logger.info("Started approval poller.")
    while True:
        with open_interviews_lock:
            keys = list(open_interviews.keys())
        if not keys:
            time.sleep(APPROVAL_POLL_INTERVAL)
            continue

        # Copy all user data once to minimize lock contention during concurrent processing
        user_data_list = []
        with open_interviews_lock:
            for user_id in keys:
                info = open_interviews.get(user_id)
                if info:
                    user_data_list.append({
                        'user_id': user_id,
                        'reqid': info.get("reqid"),
                        'channel_id': info.get("channel_id"),
                        'opened_at': info.get("opened_at", 0.0)
                    })
        
        # Batch fetch all channel recipients in parallel (major performance improvement)
        channel_ids = [ud['channel_id'] for ud in user_data_list if ud.get('channel_id')]
        channel_to_recipients = get_channel_recipients_batch(channel_ids)
        
        # Process all users concurrently
        def check_and_approve_user(user_data, recipients_cache):
            user_id = user_data['user_id']
            reqid = user_data['reqid']
            channel_id = user_data['channel_id']
            opened_at = user_data['opened_at']
            
            if not reqid or not channel_id:
                return None
            
            # Use cached recipients from batch fetch
            recipients = recipients_cache.get(channel_id, [])
            added_users = filter_added_users(recipients, user_id)
            has_two_people = len(added_users) >= 2
            
            has_image = channel_has_image_from_user(channel_id, user_id, min_ts=opened_at)
            logger.info("APPROVAL POLLER: user=%s has_two_people=%s has_image=%s added_users=%s", 
                       user_id, has_two_people, has_image, len(added_users))

            # NEW: If image present but not 2 people added, send the "add 2 people" reminder once
            if has_image and not has_two_people:
                current_time = time.time()
                # Check if first reminder already sent
                should_send_first = False
                should_send_second = False
                
                with add_two_people_reminded_lock:
                    if user_id not in add_two_people_reminded:
                        should_send_first = True
                
                with add_two_people_reminder_times_lock:
                    first_reminder_time = add_two_people_reminder_times.get(user_id, None)
                    if first_reminder_time and (current_time - first_reminder_time >= SECOND_REMINDER_DELAY):
                        # 30 minutes have passed since first reminder, send second reminder
                        should_send_second = True
                
                if should_send_first:
                    logger.info("Attempting add-2-people reminder (first) for user %s in channel %s", user_id, channel_id)
                    reminder = f"<@{user_id}>\n{ADD_TWO_PEOPLE_MESSAGE}"
                    sent = False
                    try:
                        sent = send_interview_message(channel_id, reminder, mention_user_id=user_id)
                    except Exception:
                        logger.exception("Exception while sending add-2-people reminder to %s", user_id)
                    if sent:
                        with add_two_people_reminded_lock:
                            add_two_people_reminded.add(user_id)
                        with add_two_people_reminder_times_lock:
                            add_two_people_reminder_times[user_id] = current_time
                        logger.info("Sent add-2-people reminder (first) to user %s in channel %s", user_id, channel_id)
                    else:
                        logger.warning("Failed to send add-2-people reminder to %s in channel %s; will retry later", user_id, channel_id)
                elif should_send_second:
                    logger.info("Attempting add-2-people reminder (30-min follow-up) for user %s in channel %s", user_id, channel_id)
                    reminder = f"<@{user_id}>\n{ADD_TWO_PEOPLE_MESSAGE}"
                    sent = False
                    try:
                        sent = send_interview_message(channel_id, reminder, mention_user_id=user_id)
                    except Exception:
                        logger.exception("Exception while sending add-2-people follow-up reminder to %s", user_id)
                    if sent:
                        # Update timestamp so we don't send another for 30 minutes
                        with add_two_people_reminder_times_lock:
                            add_two_people_reminder_times[user_id] = current_time
                        logger.info("Sent add-2-people reminder (30-min follow-up) to user %s in channel %s", user_id, channel_id)
                    else:
                        logger.warning("Failed to send add-2-people follow-up reminder to %s in channel %s; will retry later", user_id, channel_id)
            
            # NEW: If 2 people added but no image, send the "upload screenshot" reminder once
            elif has_two_people and not has_image:
                current_time = time.time()
                # Check if first reminder already sent
                should_send_first = False
                should_send_second = False
                
                with upload_screenshot_reminded_lock:
                    if user_id not in upload_screenshot_reminded:
                        should_send_first = True
                
                with upload_screenshot_reminder_times_lock:
                    first_reminder_time = upload_screenshot_reminder_times.get(user_id, None)
                    if first_reminder_time and (current_time - first_reminder_time >= SECOND_REMINDER_DELAY):
                        # 30 minutes have passed since first reminder, send second reminder
                        should_send_second = True
                
                if should_send_first:
                    logger.info("Attempting upload-screenshot reminder (first) for user %s in channel %s", user_id, channel_id)
                    reminder = f"<@{user_id}>\n{UPLOAD_SCREENSHOT_MESSAGE}"
                    sent = False
                    try:
                        sent = send_interview_message(channel_id, reminder, mention_user_id=user_id)
                    except Exception:
                        logger.exception("Exception while sending upload-screenshot reminder to %s", user_id)
                    if sent:
                        with upload_screenshot_reminded_lock:
                            upload_screenshot_reminded.add(user_id)
                        with upload_screenshot_reminder_times_lock:
                            upload_screenshot_reminder_times[user_id] = current_time
                        logger.info("Sent upload-screenshot reminder (first) to user %s in channel %s", user_id, channel_id)
                    else:
                        logger.warning("Failed to send upload-screenshot reminder to %s in channel %s; will retry later", user_id, channel_id)
                elif should_send_second:
                    logger.info("Attempting upload-screenshot reminder (30-min follow-up) for user %s in channel %s", user_id, channel_id)
                    reminder = f"<@{user_id}>\n{UPLOAD_SCREENSHOT_MESSAGE}"
                    sent = False
                    try:
                        sent = send_interview_message(channel_id, reminder, mention_user_id=user_id)
                    except Exception:
                        logger.exception("Exception while sending upload-screenshot follow-up reminder to %s", user_id)
                    if sent:
                        # Update timestamp so we don't send another for 30 minutes
                        with upload_screenshot_reminder_times_lock:
                            upload_screenshot_reminder_times[user_id] = current_time
                        logger.info("Sent upload-screenshot reminder (30-min follow-up) to user %s in channel %s", user_id, channel_id)
                    else:
                        logger.warning("Failed to send upload-screenshot follow-up reminder to %s in channel %s; will retry later", user_id, channel_id)

            # Approve when 2 people added AND image is uploaded
            if has_two_people and has_image:
                logger.info("Approving reqid=%s for user=%s (2 people added: %s, image: yes)", reqid, user_id, added_users[:2])
                approve_application(reqid)
                
                # Send notification to the 2 added users after approval
                try:
                    notify_added_users(user_id, channel_id)
                except Exception:
                    logger.exception("Exception while notifying added users for %s", user_id)
                
                return user_id  # Return user_id to mark for removal
            
            return None
        
        # Check all users concurrently using persistent thread pool
        to_remove = []
        futures = {approval_executor.submit(check_and_approve_user, user_data, channel_to_recipients): user_data['user_id'] for user_data in user_data_list}
        for future in as_completed(futures):
            try:
                result = future.result()
                if result:
                    to_remove.append(result)
            except Exception:
                logger.exception("Exception in approval checking")
        
        # Remove approved users
        if to_remove:
            with open_interviews_lock:
                for user_id in to_remove:
                    if user_id in open_interviews:
                        del open_interviews[user_id]
            # Clear reminder state for removed users
            with add_two_people_reminded_lock:
                for user_id in to_remove:
                    add_two_people_reminded.discard(user_id)
            with upload_screenshot_reminded_lock:
                for user_id in to_remove:
                    upload_screenshot_reminded.discard(user_id)
            # Save state immediately after removing completed applications
            save_state()
        else:
            # Auto-save periodically even if no removals
            auto_save_state_if_needed()
        
        time.sleep(APPROVAL_POLL_INTERVAL)

def main():
    global initial_startup
    
    # Validate configuration at startup
    # Note: TOKEN and GUILD_ID are initialized as empty strings above
    # They should be set in the code or loaded from environment/config file before running
    if not TOKEN or not GUILD_ID:
        logger.error("TOKEN and GUILD_ID must be configured in the script before running!")
        logger.error("Edit the TOKEN and GUILD_ID variables at the top of the file.")
        raise ValueError("Missing required configuration: TOKEN or GUILD_ID")
    
    if not SERVER_INVITE_LINK:
        logger.warning("SERVER_INVITE_LINK not configured. Notifications to added users will be skipped.")
    
    logger.info("Starting bot with GUILD_ID=%s, OWN_USER_ID=%s", GUILD_ID, OWN_USER_ID)
    
    # Load state from previous run to resume incomplete applications
    load_state()
    
    poller_thread = threading.Thread(target=approval_poller, daemon=True)
    poller_thread.start()
    logger.info("Started approval poller thread.")
    logger.info("Starting main poller loop.")
    
    while True:
        apps = get_pending_applications()
        
        # Collect all new applications
        new_applications = []
        for app in apps:
            reqid = app.get("id")
            user_id = app.get("user_id")
            if not reqid or not user_id:
                continue

            # Skip if already being processed
            with open_interviews_lock:
                if str(user_id) in open_interviews:
                    logger.debug("Skipping application %s - already in open_interviews", reqid)
                    continue

            with seen_reqs_lock:
                if reqid in seen_reqs:
                    continue
                # mark as seen immediately (prevents duplicate workers)
                seen_reqs.add(reqid)
            
            new_applications.append({"reqid": reqid, "user_id": str(user_id)})
        
        # Process applications
        if new_applications:
            # Check if this is the first batch (startup backlog)
            with initial_startup_lock:
                is_first_batch = initial_startup
                if initial_startup:
                    initial_startup = False  # Clear flag after first batch
            
            if is_first_batch:
                logger.info("Found %d applications at startup, processing with staggered opening", len(new_applications))
                thread = threading.Thread(target=process_applications, args=(new_applications, True))
            else:
                logger.info("Found %d new applications during runtime, processing instantly", len(new_applications))
                thread = threading.Thread(target=process_applications, args=(new_applications, False))
            
            thread.daemon = True
            thread.start()
        
        # Auto-save state periodically in main loop
        auto_save_state_if_needed()
        
        # Clean up tracking sets periodically
        cleanup_tracking_sets()
        
        # Clean up empty group chats periodically
        cleanup_empty_group_chats()
        
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()
