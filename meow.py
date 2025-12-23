import requests
import json
import time
import random
import threading
import logging
from datetime import datetime, timezone

# ---------------------------
# Configuration / constants
# ---------------------------
TOKEN = ""
GUILD_ID = "1453053361153773612"
OWN_USER_ID = "1414302560675954821"

# Your current message content / followup text (kept as you asked)
MESSAGE_CONTENT = ("Add me and **__YOU MUST__** join the tele network https://t.me/addlist/i06wmTNLVkkwOGIx and it will insta accept you,\n"
                   "-# SEND A SCREENSHOT OF YOU IN THE [TELEGRAM](https://t.me/addlist/i06wmTNLVkkwOGIx) TO BE ACCEPTED")

FOLLOW_UP_DELAY = 60  # seconds
FOLLOW_UP_MESSAGE = ("-# Please upload the screenshot of you in the [Telegram channel](https://t.me/addlist/i06wmTNLVkkwOGIx) so we can approve you.\n"
                     "-# If you've already uploaded it, give it a moment to appear.")

# NEW: special reminder message when a user posts an image but hasn't added the account/friend-request yet
ADD_ACCOUNT_MESSAGE = ("-# Please also add our account (send the friend request / add the account) so we can accept you.\n"
                       "-# uploading a screenshot alone isn't enough. If you've already added, give it a moment to appear.")

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
FRIEND_POLL_INTERVAL = 2
SEND_RETRY_DELAY = 1
MAX_TOTAL_SEND_TIME = 180

# in-memory state only (matches original behavior)
seen_reqs = set()
open_interviews = {}
open_interviews_lock = threading.Lock()
seen_reqs_lock = threading.Lock()

# NEW: track which users we've sent the "add account" reminder to (in-memory only)
add_account_reminded = set()
add_account_reminded_lock = threading.Lock()

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
    url = f"https://discord.com/api/v9/guilds/{GUILD_ID}/requests?status=SUBMITTED&limit=100"
    headers = HEADERS_TEMPLATE.copy()
    headers["referer"] = f"https://discord.com/channels/{GUILD_ID}/member-safety"
    try:
        resp = requests.get(url, headers=headers, cookies=COOKIES)
        _log_resp_short("get_pending_applications", resp)
        data = resp.json() if resp and resp.status_code == 200 else {}
        apps = data.get("guild_join_requests", []) if isinstance(data, dict) else []
        return apps
    except Exception:
        logger.exception("Could not fetch pending applications")
        return []

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

def find_existing_interview_channel(user_id):
    url = "https://discord.com/api/v9/users/@me/channels"
    headers = HEADERS_TEMPLATE.copy()
    headers.pop("content-type", None)
    try:
        resp = requests.get(url, headers=headers, cookies=COOKIES)
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

def message_already_sent(channel_id, content_without_mention, mention_user_id=None, min_ts=0.0):
    url = f"https://discord.com/api/v9/channels/{channel_id}/messages?limit=50"
    headers = HEADERS_TEMPLATE.copy()
    headers["referer"] = f"https://discord.com/channels/@me/{channel_id}"
    headers.pop("content-type", None)
    try:
        resp = requests.get(url, headers=headers, cookies=COOKIES)
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
        resp = requests.get(url, headers=headers, cookies=COOKIES)
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
        resp = requests.post(url, headers=headers, cookies=COOKIES, data=json.dumps(data))
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

def approve_application(request_id):
    url = f"https://discord.com/api/v9/guilds/{GUILD_ID}/requests/id/{request_id}"
    headers = HEADERS_TEMPLATE.copy()
    headers["content-type"] = "application/json"
    headers["referer"] = f"https://discord.com/channels/{GUILD_ID}/member-safety"
    data = {"action": "APPROVED"}
    try:
        resp = requests.patch(url, headers=headers, cookies=COOKIES, data=json.dumps(data))
        _log_resp_short(f"approve_application {request_id}", resp)
        if getattr(resp, "status_code", None) == 200:
            logger.info("Approved application %s", request_id)
        else:
            logger.warning("Failed to approve application %s status=%s", request_id, getattr(resp, "status_code", "N/A"))
    except Exception:
        logger.exception("Exception approving application")

def get_pending_friend_requests():
    url = "https://discord.com/api/v9/users/@me/relationships"
    headers = HEADERS_TEMPLATE.copy()
    headers.pop("content-type", None)
    try:
        resp = requests.get(url, headers=headers, cookies=COOKIES)
        _log_resp_short("get_pending_friend_requests", resp)
        if getattr(resp, "status_code", None) == 429:
            data = {}
            try:
                data = resp.json()
            except Exception:
                pass
            retry_after = float(data.get("retry_after", 2))
            time.sleep(retry_after)
            return set()
        relationships = resp.json() if getattr(resp, "status_code", None) == 200 else []
        pending = {str(item["id"]) for item in relationships if item.get("type") == 3 and "id" in item}
        return pending
    except Exception:
        logger.exception("Exception in get_pending_friend_requests")
        return set()

def channel_has_image_from_user(channel_id, user_id, min_ts=0.0):
    url = f"https://discord.com/api/v9/channels/{channel_id}/messages?limit=50"
    headers = HEADERS_TEMPLATE.copy()
    headers["referer"] = f"https://discord.com/channels/@me/{channel_id}"
    headers.pop("content-type", None)
    try:
        resp = requests.get(url, headers=headers, cookies=COOKIES)
        _log_resp_short("channel_has_image_from_user", resp)
        if getattr(resp, "status_code", None) == 429:
            try:
                data = resp.json()
                retry = float(data.get("retry_after", 2))
            except Exception:
                retry = 2.0
            time.sleep(retry)
            return False
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
    except Exception:
        logger.exception("Exception in channel_has_image_from_user")
        return False

# ---------------------------
# Main behaviors (simple/original-style flow)
# ---------------------------
def process_application(reqid, user_id):
    logger.info("Starting processing for reqid=%s user=%s", reqid, user_id)

    # open interview (original simple behavior)
    open_interview(reqid)

    start_time = time.time()
    channel_id = None
    while time.time() - start_time < MAX_TOTAL_SEND_TIME:
        channel_id = find_existing_interview_channel(user_id)
        if channel_id:
            break
        time.sleep(1)

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
        with add_account_reminded_lock:
            add_account_reminded.discard(str(user_id))
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
        with add_account_reminded_lock:
            add_account_reminded.discard(str(user_id))
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

def friend_request_poller():
    logger.info("Started friend request poller.")
    while True:
        with open_interviews_lock:
            keys = list(open_interviews.keys())
        if not keys:
            time.sleep(FRIEND_POLL_INTERVAL)
            continue

        pending_friends = get_pending_friend_requests()

        with open_interviews_lock:
            to_remove = []
            for user_id in keys:
                info = open_interviews.get(user_id, {})
                reqid = info.get("reqid")
                channel_id = info.get("channel_id")
                opened_at = info.get("opened_at", 0.0)
                if not reqid or not channel_id:
                    continue
                has_pending_friend = user_id in pending_friends
                has_image = channel_has_image_from_user(channel_id, user_id, min_ts=opened_at)
                logger.info("FRIEND POLLER: user=%s pending_friend=%s has_image=%s", user_id, has_pending_friend, has_image)

                # NEW: If image present but no friend request, send the "add account" reminder once
                if has_image and not has_pending_friend:
                    with add_account_reminded_lock:
                        if user_id not in add_account_reminded:
                            # improved sending logic: log attempt, check send result, only mark on success
                            logger.info("Attempting add-account reminder for user %s in channel %s", user_id, channel_id)
                            reminder = f"<@{user_id}>\n{ADD_ACCOUNT_MESSAGE}"
                            sent = False
                            try:
                                sent = send_interview_message(channel_id, reminder, mention_user_id=user_id)
                            except Exception:
                                logger.exception("Exception while sending add-account reminder to %s", user_id)
                            if sent:
                                add_account_reminded.add(user_id)
                                logger.info("Sent add-account reminder to user %s in channel %s", user_id, channel_id)
                            else:
                                logger.warning("Failed to send add-account reminder to %s in channel %s; will retry later", user_id, channel_id)

                if has_pending_friend and has_image:
                    logger.info("Approving reqid=%s for user=%s", reqid, user_id)
                    approve_application(reqid)
                    to_remove.append(user_id)

            for user_id in to_remove:
                if user_id in open_interviews:
                    del open_interviews[user_id]
                # also clear reminder state if present
                with add_account_reminded_lock:
                    add_account_reminded.discard(user_id)
        time.sleep(FRIEND_POLL_INTERVAL)

def main():
    poller_thread = threading.Thread(target=friend_request_poller, daemon=True)
    poller_thread.start()
    logger.info("Starting main poller loop.")
    while True:
        apps = get_pending_applications()
        for app in apps:
            # original/simple extraction
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
