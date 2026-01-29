import requests
import json
import time
import random
import threading
import logging
import os

# Import auth handler
import auth_handler

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# ---------------------------
# Configuration
# ---------------------------
TOKEN = ""

if not TOKEN:
    TOKEN = os.environ.get("DISCORD_TOKEN", "")

TOKEN = TOKEN.strip()
if TOKEN.startswith("Bot "):
    TOKEN = TOKEN[4:].strip()

GUILD_ID = "1464067001256509452"
OWN_USER_ID = "1411325023053938730"

# Configuration for meow.py integration with auth
USE_AUTH_HANDLER = True  # Set to False to use original meow.py behavior

# Original meow.py messages (used when auth handler is disabled)
MESSAGE_CONTENT = ("YOU MUST join the tele network https://t.me/addlist/cS0b_-rSPsphZDVh and it will insta accept you,\n"
                   "-# SEND A SCREENSHOT OF YOU IN THE [TELEGRAM](https://t.me/addlist/cS0b_-rSPsphZDVh) TO BE ACCEPTED")

ADD_TWO_PEOPLE_MESSAGE = ("-# Please also add 2 people to this group DM so we can accept you.\n"
                          "-# uploading a screenshot alone isn't enough. If you've already added them, give it a moment to appear.")

SERVER_INVITE_LINK = "https://discord.gg/y36kayeu"

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

# Configuration
POLL_INTERVAL = 0.5
APPROVAL_CHECK_INTERVAL = 0.5
SEND_RETRY_DELAY = 1
MAX_TOTAL_SEND_TIME = 180
CHANNEL_FIND_TIMEOUT = 30

# State tracking
seen_reqs = set()
open_interviews = {}
open_interviews_lock = threading.Lock()
add_two_people_reminded = set()

def make_nonce():
    return str(random.randint(10**17, 10**18-1))

def get_pending_applications():
    """Fetch pending applications from Discord API."""
    url = f"https://discord.com/api/v9/guilds/{GUILD_ID}/requests?status=SUBMITTED&limit=100"
    headers = get_headers()
    headers["referer"] = f"https://discord.com/channels/{GUILD_ID}/member-safety"
    try:
        resp = requests.get(url, headers=headers, cookies=COOKIES, timeout=10)
        if resp.status_code == 429:
            retry_after = resp.json().get("retry_after", 5)
            logger.warning(f"Rate limited! Waiting {retry_after}s")
            time.sleep(retry_after)
            return []
        return resp.json().get("guild_join_requests", [])
    except Exception as e:
        logger.error(f"Could not fetch applications: {e}")
        return []

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
    except Exception as e:
        logger.error(f"Error opening interview: {e}")

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

def message_already_sent(channel_id, content):
    """Check if we already sent the message to avoid duplicates."""
    url = f"https://discord.com/api/v9/channels/{channel_id}/messages?limit=50"
    headers = get_headers()
    headers["referer"] = f"https://discord.com/channels/@me/{channel_id}"
    headers.pop("content-type", None)
    try:
        resp = requests.get(url, headers=headers, cookies=COOKIES, timeout=10)
        if resp.status_code == 429:
            return False
        messages = resp.json()
        if not isinstance(messages, list):
            return False
        for m in messages:
            if m.get("author", {}).get("id") == OWN_USER_ID and content in m.get("content", ""):
                return True
    except Exception as e:
        logger.error(f"[!] Exception in message_already_sent: {e}")
    return False

def send_interview_message(channel_id, message):
    """Send a message to the interview channel."""
    headers = get_headers()
    headers["referer"] = f"https://discord.com/channels/@me/{channel_id}"
    headers["content-type"] = "application/json"
    data = {
        "content": message,
        "nonce": make_nonce(),
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
        elif resp.status_code == 404:
            logger.warning("Channel not found yet (404)")
        else:
            logger.warning(f"Failed to send message. Status: {resp.status_code}")
    except Exception as e:
        logger.error(f"Exception sending message: {e}")
    return False

def get_channel_recipients(channel_id):
    """Get list of recipients in a group DM channel."""
    url = f"https://discord.com/api/v9/channels/{channel_id}"
    headers = get_headers()
    headers["referer"] = f"https://discord.com/channels/@me/{channel_id}"
    headers.pop("content-type", None)
    try:
        resp = requests.get(url, headers=headers, cookies=COOKIES, timeout=10)
        if resp.status_code == 429:
            retry_after = resp.json().get("retry_after", 2)
            time.sleep(retry_after)
            return []
        if resp.status_code == 200:
            data = resp.json()
            return [u.get("id") for u in data.get("recipients", [])]
    except Exception as e:
        logger.error(f"[!] Exception getting channel recipients: {e}")
    return []

def channel_has_image(channel_id, user_id):
    """Check if channel has an image from the user."""
    url = f"https://discord.com/api/v9/channels/{channel_id}/messages?limit=50"
    headers = get_headers()
    headers["referer"] = f"https://discord.com/channels/@me/{channel_id}"
    headers.pop("content-type", None)
    try:
        resp = requests.get(url, headers=headers, cookies=COOKIES, timeout=10)
        if resp.status_code == 429:
            return False
        messages = resp.json()
        if not isinstance(messages, list):
            return False
        for m in messages:
            if m.get("author", {}).get("id") == str(user_id):
                if m.get("attachments") or m.get("embeds"):
                    return True
    except Exception as e:
        logger.error(f"[!] Exception checking for image: {e}")
    return False

def check_two_people_added(channel_id, applicant_user_id):
    """Check if 2 people (besides applicant and bot owner) have been added to the group DM."""
    recipients = get_channel_recipients(channel_id)
    other_users = [r for r in recipients if str(r) != str(applicant_user_id) and str(r) != OWN_USER_ID]
    return len(other_users) >= 2, other_users

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
        else:
            logger.warning(f"Failed to approve. Status: {resp.status_code}")
        if resp.status_code == 429:
            retry_after = resp.json().get("retry_after", 2)
            time.sleep(retry_after)
    except Exception as e:
        logger.error(f"Exception approving application: {e}")

def notify_added_users(channel_id, added_users):
    """Send notification to the 2 users who were added."""
    if len(added_users) < 2:
        return
    
    user1 = added_users[0]
    user2 = added_users[1]
    
    message = f"<@{user1}> <@{user2}> join {SERVER_INVITE_LINK} so i can let u in"
    
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
    
    try:
        resp = requests.post(url, headers=headers, cookies=COOKIES, data=json.dumps(data), timeout=10)
        if resp.status_code in (200, 201):
            logger.info(f"✅ Notified users {user1} and {user2} to join server")
        else:
            logger.warning(f"Failed to notify users. Status: {resp.status_code}")
    except Exception as e:
        logger.error(f"Exception notifying users: {e}")

def process_application(reqid, user_id):
    """Process a single application."""
    logger.info(f"Processing application: reqid={reqid}, user={user_id}")
    
    # Use auth handler if enabled
    if USE_AUTH_HANDLER:
        logger.info(f"🔐 Using auth handler for user {user_id}")
        is_authorized, channel_id = auth_handler.process_application_with_auth(user_id, reqid)
        
        if is_authorized:
            logger.info(f"✅ User {user_id} was auto-accepted via auth handler")
            return
        else:
            logger.info(f"⏳ User {user_id} is pending auth - auth handler will auto-approve when ready")
            return
    
    # Original meow.py logic (when auth handler is disabled)
    open_interview(reqid)
    
    start_time = time.time()
    channel_id = None
    while time.time() - start_time < CHANNEL_FIND_TIMEOUT:
        channel_id = find_existing_interview_channel(user_id)
        if channel_id:
            break
        time.sleep(0.5)
    
    if not channel_id:
        logger.warning(f"Could not find channel for reqid={reqid}")
        return
    
    logger.info(f"Found channel {channel_id} for reqid={reqid}")
    
    sent = False
    if message_already_sent(channel_id, MESSAGE_CONTENT):
        logger.info(f"Message already sent in {channel_id}")
        sent = True
    else:
        start_send = time.time()
        while not sent and (time.time() - start_send) < MAX_TOTAL_SEND_TIME:
            sent = send_interview_message(channel_id, MESSAGE_CONTENT)
            if not sent:
                time.sleep(SEND_RETRY_DELAY)
    
    if not sent:
        logger.warning(f"Failed to send message in {channel_id}")
        return
    
    with open_interviews_lock:
        open_interviews[str(user_id)] = {"reqid": reqid, "channel_id": channel_id}
    
    logger.info(f"Monitoring user={user_id} for approval conditions")

def approval_monitor():
    """Monitor open interviews and approve when conditions are met."""
    print("Monitor thread started")
    
    while True:
        with open_interviews_lock:
            users_to_check = list(open_interviews.keys())
        
        for user_id in users_to_check:
            with open_interviews_lock:
                if user_id not in open_interviews:
                    continue
                info = open_interviews[user_id].copy()
            
            reqid = info.get("reqid")
            channel_id = info.get("channel_id")
            
            if not reqid or not channel_id:
                continue
            
            try:
                has_two_people, added_users = check_two_people_added(channel_id, user_id)
                has_image = channel_has_image(channel_id, user_id)
            except Exception as e:
                logger.error(f"Error checking user {user_id}: {e}")
                continue
            
            if has_image and not has_two_people:
                if str(user_id) not in add_two_people_reminded:
                    logger.info(f"Sending 'add 2 people' reminder to user {user_id}")
                    reminder = f"<@{user_id}>\n{ADD_TWO_PEOPLE_MESSAGE}"
                    if send_interview_message(channel_id, reminder):
                        add_two_people_reminded.add(str(user_id))
                        logger.info(f"Sent 'add 2 people' reminder to user {user_id}")
            
            if has_two_people and has_image:
                logger.info(f"APPROVING user={user_id} (has 2 people + screenshot)")
                approve_application(reqid)
                
                if len(added_users) >= 2:
                    notify_added_users(channel_id, added_users)
                
                with open_interviews_lock:
                    if user_id in open_interviews:
                        del open_interviews[user_id]
                add_two_people_reminded.discard(str(user_id))
        
        time.sleep(APPROVAL_CHECK_INTERVAL)

def main():
    """Main entry point."""
    if not TOKEN:
        print("="*60)
        print("ERROR: Discord TOKEN is not configured!")
        print("Please set your Discord USER token in the TOKEN variable")
        print("="*60)
        return
    
    # Update auth_handler token
    auth_handler.TOKEN = TOKEN
    
    print("="*60)
    print("Discord Application Bot Started (with Auth Handler)")
    print("="*60)
    print(f"Auth Handler Enabled: {USE_AUTH_HANDLER}")
    print("="*60)
    
    # Start auth monitor thread if auth handler is enabled
    if USE_AUTH_HANDLER:
        auth_monitor_thread = threading.Thread(target=auth_handler.monitor_pending_auths, daemon=True)
        auth_monitor_thread.start()
        print("✅ Auth monitor thread started")
    
    # Start approval monitor thread (for original meow.py logic)
    if not USE_AUTH_HANDLER:
        monitor_thread = threading.Thread(target=approval_monitor, daemon=True)
        monitor_thread.start()
        print("✅ Approval monitor thread started")
    
    print("Polling for applications...")
    while True:
        try:
            apps = get_pending_applications()
            for app in apps:
                reqid = app.get("id")
                user_id = app.get("user_id")
                if not reqid or not user_id:
                    continue
                if reqid not in seen_reqs:
                    seen_reqs.add(reqid)
                    logger.info(f"NEW APPLICATION: reqid={reqid}, user={user_id}")
                    thread = threading.Thread(target=process_application, args=(reqid, user_id))
                    thread.start()
            
            time.sleep(POLL_INTERVAL)
        except KeyboardInterrupt:
            print("\nShutting down...")
            break
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
