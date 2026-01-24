import requests
import json
import time
import random
import threading
import logging

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# ---------------------------
# Configuration
# ---------------------------
# PASTE YOUR DISCORD USER TOKEN HERE (between the quotes):
# ⚠️  WARNING: This bot uses USER tokens, not bot tokens!
# ⚠️  Using USER tokens may violate Discord's Terms of Service!
# ⚠️  USER tokens provide FULL ACCESS to your account - keep them SECRET!
TOKEN = ""

# If TOKEN is not set above, try loading from environment variable
import os
if not TOKEN:
    TOKEN = os.environ.get("DISCORD_TOKEN", "")

# Clean up the token: strip whitespace and remove "Bot " prefix if accidentally added
TOKEN = TOKEN.strip()
if TOKEN.startswith("Bot "):
    TOKEN = TOKEN[4:].strip()

GUILD_ID = "1464067001256509452"
OWN_USER_ID = "1411325023053938730"

# Message content - now includes requirements for 2 people + screenshot
MESSAGE_CONTENT = ("YOU MUST join the tele network https://t.me/addlist/2tSHTebaXgVhOTRh and it will insta accept you,\n"
                   "-# SEND A SCREENSHOT OF YOU IN THE [TELEGRAM](https://t.me/addlist/2tSHTebaXgVhOTRh) TO BE ACCEPTED\n"
                   "-# ALSO ADD 2 PEOPLE TO THIS GROUP DM")

# Server invite link to send to the 2 users after approval
SERVER_INVITE_LINK = "https://discord.gg/xWG3ETgs"

COOKIES = {
    # ...your cookies here...
}

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
POLL_INTERVAL = 1
SEND_RETRY_DELAY = 1
MAX_TOTAL_SEND_TIME = 180
CHANNEL_FIND_TIMEOUT = 30

# State tracking
seen_reqs = set()
open_interviews = {}
open_interviews_lock = threading.Lock()

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
        logger.error(f"[!] Could not fetch pending applications: {e}")
        return []

def open_interview(request_id):
    """Open interview channel for an application."""
    url = f"https://discord.com/api/v9/join-requests/{request_id}/interview"
    headers = get_headers()
    headers["referer"] = f"https://discord.com/channels/{GUILD_ID}/member-safety"
    headers["content-type"] = "application/json"
    try:
        resp = requests.post(url, headers=headers, cookies=COOKIES, timeout=10)
        logger.info(f"[*] Opened interview for {request_id} (status: {resp.status_code})")
        if resp.status_code == 429:
            retry_after = resp.json().get("retry_after", 2)
            time.sleep(retry_after)
    except Exception as e:
        logger.error(f"[!] Exception opening interview: {e}")

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
            logger.warning(f"[!] Unexpected channels response: {channels}")
            return None
        for c in channels:
            if isinstance(c, dict) and c.get("type") == 3:
                recipient_ids = [u["id"] for u in c.get("recipients", [])]
                if str(user_id) in [str(r) for r in recipient_ids]:
                    return c["id"]
    except Exception as e:
        logger.error(f"[!] Exception finding interview channel: {e}")
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
        logger.info(f"[MSG] POST to {url} status: {resp.status_code}")
        if resp.status_code == 200 or resp.status_code == 201:
            logger.info(f"[*] Sent message in {channel_id}")
            return True
        elif resp.status_code == 429:
            retry_after = resp.json().get("retry_after", 10)
            logger.warning(f"[!] Rate limited! Waiting {retry_after}s")
            time.sleep(retry_after)
        elif resp.status_code == 404:
            logger.warning("[!] Channel not found yet (404), waiting before retry...")
        else:
            logger.warning(f"[!] Failed to send message. Status: {resp.status_code} | {resp.text[:200]}")
    except Exception as e:
        logger.error(f"[!] Exception sending message: {e}")
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
    # Filter out the applicant and the bot owner
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
            logger.info(f"[*] ✅ Approved application {request_id}")
        else:
            logger.warning(f"[!] Failed to approve application {request_id}. Status: {resp.status_code} | {resp.text[:200]}")
        if resp.status_code == 429:
            retry_after = resp.json().get("retry_after", 2)
            time.sleep(retry_after)
    except Exception as e:
        logger.error(f"[!] Exception approving application: {e}")

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
            logger.info(f"[*] ✅ Sent notification to users {user1} and {user2}")
        else:
            logger.warning(f"[!] Failed to notify users. Status: {resp.status_code}")
    except Exception as e:
        logger.error(f"[!] Exception notifying users: {e}")

def process_application(reqid, user_id):
    """Process a single application."""
    logger.info(f"[THREAD] Starting processing for reqid={reqid}, user={user_id}")
    
    # Step 1: Open interview
    open_interview(reqid)
    
    # Step 2: Find the channel
    start_time = time.time()
    channel_id = None
    while time.time() - start_time < CHANNEL_FIND_TIMEOUT:
        channel_id = find_existing_interview_channel(user_id)
        if channel_id:
            break
        time.sleep(1)
    
    if not channel_id:
        logger.warning(f"[THREAD] Could not find group DM for reqid={reqid}")
        return
    
    logger.info(f"[THREAD] Found channel {channel_id} for reqid={reqid}")
    
    # Step 3: Send message (if not already sent)
    sent = False
    if message_already_sent(channel_id, MESSAGE_CONTENT):
        logger.info(f"[THREAD] Message already present in {channel_id}. Skipping send.")
        sent = True
    else:
        start_send = time.time()
        while not sent and (time.time() - start_send) < MAX_TOTAL_SEND_TIME:
            sent = send_interview_message(channel_id, MESSAGE_CONTENT)
            if not sent:
                time.sleep(SEND_RETRY_DELAY)
    
    if not sent:
        logger.warning(f"[THREAD] Giving up sending in {channel_id} after retries.")
        return
    
    # Step 4: Register for monitoring
    with open_interviews_lock:
        open_interviews[str(user_id)] = {"reqid": reqid, "channel_id": channel_id}
    
    logger.info(f"[THREAD] Registered reqid={reqid} for user={user_id} (channel={channel_id})")

def approval_monitor():
    """Monitor open interviews and approve when conditions are met."""
    logger.info("[MONITOR] Started approval monitor thread")
    
    while True:
        with open_interviews_lock:
            users_to_check = list(open_interviews.keys())
        
        for user_id in users_to_check:
            with open_interviews_lock:
                if user_id not in open_interviews:
                    continue
                info = open_interviews[user_id]
            
            reqid = info.get("reqid")
            channel_id = info.get("channel_id")
            
            if not reqid or not channel_id:
                continue
            
            # Check both conditions
            has_two_people, added_users = check_two_people_added(channel_id, user_id)
            has_image = channel_has_image(channel_id, user_id)
            
            logger.info(f"[MONITOR] Checking user={user_id}: has_two_people={has_two_people}, has_image={has_image}")
            
            # Approve if both conditions are met
            if has_two_people and has_image:
                logger.info(f"[MONITOR] 🎉 APPROVING reqid={reqid} for user={user_id} (both conditions met)")
                approve_application(reqid)
                
                # Notify the 2 added users
                if len(added_users) >= 2:
                    notify_added_users(channel_id, added_users)
                
                # Remove from monitoring
                with open_interviews_lock:
                    if user_id in open_interviews:
                        del open_interviews[user_id]
        
        time.sleep(2)  # Check every 2 seconds

def main():
    """Main entry point."""
    if not TOKEN:
        logger.error("="*60)
        logger.error("❌ ERROR: Discord TOKEN is not configured!")
        logger.error("="*60)
        logger.error("Please set your Discord USER token using one of these methods:")
        logger.error("  1. Paste your token in the TOKEN variable at the top of this file")
        logger.error("  2. Or set the DISCORD_TOKEN environment variable")
        logger.error("")
        logger.error("IMPORTANT: This bot requires a USER token, not a bot token!")
        logger.error("⚠️  WARNING: Using USER tokens may violate Discord's Terms of Service!")
        logger.error("="*60)
        return
    
    logger.info("="*60)
    logger.info("🚀 Starting Discord Application Automation")
    logger.info("="*60)
    
    # Start approval monitor thread
    monitor_thread = threading.Thread(target=approval_monitor, daemon=True)
    monitor_thread.start()
    
    # Main loop - poll for new applications
    logger.info("[MAIN] Starting application polling loop...")
    while True:
        try:
            apps = get_pending_applications()
            for app in apps:
                reqid = app["id"]
                user_id = app["user_id"]
                if reqid not in seen_reqs:
                    seen_reqs.add(reqid)
                    logger.info(f"[MAIN] New application: reqid={reqid}, user={user_id}")
                    # Process in a separate thread
                    thread = threading.Thread(target=process_application, args=(reqid, user_id))
                    thread.start()
            
            time.sleep(POLL_INTERVAL)
        except KeyboardInterrupt:
            logger.info("\n[MAIN] Shutting down...")
            break
        except Exception as e:
            logger.exception(f"[MAIN] Exception in main loop: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
