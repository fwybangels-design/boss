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
class GatewayConfig:
    def __init__(self):
        self.TOKEN = ""
        self.GUILD_ID = ""
        self.OWN_USER_ID = ""
        self.GATEWAY_MESSAGE = ("The real server is here: discord.gg/example\n"
                               "Join telegram to never lose us: https://t.me/example")
        self.AUTO_DENY_DELAY = 30  # seconds before auto-denying
        self.COOKIES = {}
        self.config_lock = threading.Lock()
    
    def update_token(self, token):
        with self.config_lock:
            self.TOKEN = token
    
    def update_guild_id(self, guild_id):
        with self.config_lock:
            self.GUILD_ID = guild_id
    
    def update_own_user_id(self, user_id):
        with self.config_lock:
            self.OWN_USER_ID = user_id
    
    def update_gateway_message(self, message):
        with self.config_lock:
            self.GATEWAY_MESSAGE = message
    
    def update_auto_deny_delay(self, delay):
        with self.config_lock:
            self.AUTO_DENY_DELAY = delay
    
    def get_token(self):
        with self.config_lock:
            return self.TOKEN
    
    def get_guild_id(self):
        with self.config_lock:
            return self.GUILD_ID
    
    def get_own_user_id(self):
        with self.config_lock:
            return self.OWN_USER_ID
    
    def get_gateway_message(self):
        with self.config_lock:
            return self.GATEWAY_MESSAGE
    
    def get_auto_deny_delay(self):
        with self.config_lock:
            return self.AUTO_DENY_DELAY

# Global configuration instance
config = GatewayConfig()

HEADERS_TEMPLATE = {
    "accept": "*/*",
    "accept-language": "en-US,en;q=0.9",
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
INITIAL_POLL_DELAY = 0.1
MAX_POLL_DELAY = 2.0
BACKOFF_MULTIPLIER = 2.0
MAX_TOTAL_SEND_TIME = 180

# in-memory state
seen_reqs = set()
seen_reqs_lock = threading.Lock()

# Logging
VERBOSE = False
logger = logging.getLogger("gateway_bot")
logger.setLevel(logging.DEBUG if VERBOSE else logging.INFO)
ch = logging.StreamHandler()
ch.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logger.addHandler(ch)

# ANSI color codes for terminal
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

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
    guild_id = config.get_guild_id()
    token = config.get_token()
    
    if not guild_id or not token:
        return []
    
    url = f"https://discord.com/api/v9/guilds/{guild_id}/requests?status=SUBMITTED&limit=100"
    headers = HEADERS_TEMPLATE.copy()
    headers["authorization"] = token
    headers["referer"] = f"https://discord.com/channels/{guild_id}/member-safety"
    try:
        resp = requests.get(url, headers=headers, cookies=config.COOKIES)
        _log_resp_short("get_pending_applications", resp)
        data = resp.json() if resp and resp.status_code == 200 else {}
        apps = data.get("guild_join_requests", []) if isinstance(data, dict) else []
        return apps
    except Exception:
        logger.exception("Could not fetch pending applications")
        return []

def open_interview(request_id):
    token = config.get_token()
    guild_id = config.get_guild_id()
    
    if not token or not guild_id:
        return
    
    url = f"https://discord.com/api/v9/join-requests/{request_id}/interview"
    headers = HEADERS_TEMPLATE.copy()
    headers["authorization"] = token
    headers["referer"] = f"https://discord.com/channels/{guild_id}/member-safety"
    headers["content-type"] = "application/json"
    try:
        resp = requests.post(url, headers=headers, cookies=config.COOKIES)
        _log_resp_short(f"open_interview {request_id}", resp)
        logger.info("Opened interview for request %s (status=%s)", request_id, getattr(resp, "status_code", "N/A"))
    except Exception:
        logger.exception("Exception opening interview")

def find_existing_interview_channel(user_id):
    token = config.get_token()
    
    if not token:
        return None
    
    url = "https://discord.com/api/v9/users/@me/channels"
    headers = HEADERS_TEMPLATE.copy()
    headers["authorization"] = token
    headers.pop("content-type", None)
    try:
        resp = requests.get(url, headers=headers, cookies=config.COOKIES)
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

def send_interview_message(channel_id, message, mention_user_id=None):
    token = config.get_token()
    
    if not token:
        return False
    
    headers = HEADERS_TEMPLATE.copy()
    headers["authorization"] = token
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
        resp = requests.post(url, headers=headers, cookies=config.COOKIES, data=json.dumps(data))
        _log_resp_short(f"send_interview_message to {channel_id}", resp)
        if getattr(resp, "status_code", None) in (200, 201):
            logger.info("Sent gateway message to channel %s", channel_id)
            return True
        else:
            logger.warning("Failed to send message to %s status=%s", channel_id, getattr(resp, "status_code", "N/A"))
            return False
    except Exception:
        logger.exception("Exception sending message")
        return False

def deny_application(request_id):
    guild_id = config.get_guild_id()
    token = config.get_token()
    
    if not guild_id or not token:
        return
    
    url = f"https://discord.com/api/v9/guilds/{guild_id}/requests/id/{request_id}"
    headers = HEADERS_TEMPLATE.copy()
    headers["authorization"] = token
    headers["content-type"] = "application/json"
    headers["referer"] = f"https://discord.com/channels/{guild_id}/member-safety"
    data = {"action": "REJECTED"}
    try:
        resp = requests.patch(url, headers=headers, cookies=config.COOKIES, data=json.dumps(data))
        _log_resp_short(f"deny_application {request_id}", resp)
        if getattr(resp, "status_code", None) == 200:
            logger.info("Denied application %s", request_id)
        else:
            logger.warning("Failed to deny application %s status=%s", request_id, getattr(resp, "status_code", "N/A"))
    except Exception:
        logger.exception("Exception denying application")

# ---------------------------
# Main behaviors
# ---------------------------
def process_application(reqid, user_id):
    logger.info("Starting gateway processing for reqid=%s user=%s", reqid, user_id)
    
    # Open interview
    open_interview(reqid)
    
    start_time = time.time()
    channel_id = None
    poll_delay = INITIAL_POLL_DELAY
    while time.time() - start_time < MAX_TOTAL_SEND_TIME:
        channel_id = find_existing_interview_channel(user_id)
        if channel_id:
            break
        time.sleep(poll_delay)
        poll_delay = min(poll_delay * BACKOFF_MULTIPLIER, MAX_POLL_DELAY)
    
    if not channel_id:
        logger.warning("Could not find group DM for reqid=%s", reqid)
        return
    
    # Send gateway message
    gateway_message = config.get_gateway_message()
    composed_message = f"<@{user_id}>\n{gateway_message}"
    sent_ok = send_interview_message(channel_id, composed_message, mention_user_id=user_id)
    if not sent_ok:
        logger.warning("Failed to send gateway message to %s for reqid=%s", channel_id, reqid)
        return
    
    logger.info("Sent gateway message to %s for reqid=%s", channel_id, reqid)
    
    # Wait for auto-deny delay
    auto_deny_delay = config.get_auto_deny_delay()
    logger.info("Waiting %s seconds before auto-denying reqid=%s", auto_deny_delay, reqid)
    time.sleep(auto_deny_delay)
    
    # Auto-deny the application
    deny_application(reqid)
    logger.info("Auto-denied reqid=%s after %s seconds", reqid, auto_deny_delay)
    
    # Remove from seen requests to allow reapplication
    with seen_reqs_lock:
        seen_reqs.discard(reqid)
    
    logger.info("Finished processing reqid=%s user=%s (ready for reapplication)", reqid, user_id)

def main_polling_loop():
    logger.info("Starting main polling loop.")
    while True:
        apps = get_pending_applications()
        for app in apps:
            reqid = app.get("id")
            user_id = app.get("user_id")
            if not reqid or not user_id:
                continue
            
            with seen_reqs_lock:
                if reqid in seen_reqs:
                    continue
                seen_reqs.add(reqid)
            
            thread = threading.Thread(target=process_application, args=(reqid, str(user_id)))
            thread.daemon = True
            thread.start()
        time.sleep(POLL_INTERVAL)

# ---------------------------
# CLI Menu Interface
# ---------------------------
def print_menu():
    """Display the main menu with colors"""
    print(f"\n{Colors.CYAN}{'='*60}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}          🚪 GATEWAY APPLICATION BOT - CONTROL PANEL 🚪{Colors.ENDC}")
    print(f"{Colors.CYAN}{'='*60}{Colors.ENDC}")
    print(f"{Colors.GREEN}1.{Colors.ENDC} {Colors.BOLD}Set Application Token{Colors.ENDC}")
    print(f"{Colors.GREEN}2.{Colors.ENDC} {Colors.BOLD}Set Guild ID{Colors.ENDC}")
    print(f"{Colors.GREEN}3.{Colors.ENDC} {Colors.BOLD}Set Own User ID{Colors.ENDC}")
    print(f"{Colors.GREEN}4.{Colors.ENDC} {Colors.BOLD}Set Gateway Message{Colors.ENDC}")
    print(f"{Colors.GREEN}5.{Colors.ENDC} {Colors.BOLD}Set Auto-Deny Delay (seconds){Colors.ENDC}")
    print(f"{Colors.GREEN}6.{Colors.ENDC} {Colors.BOLD}View Current Configuration{Colors.ENDC}")
    print(f"{Colors.GREEN}7.{Colors.ENDC} {Colors.BOLD}Start Gateway Bot{Colors.ENDC}")
    print(f"{Colors.GREEN}8.{Colors.ENDC} {Colors.BOLD}Exit{Colors.ENDC}")
    print(f"{Colors.CYAN}{'='*60}{Colors.ENDC}")

def set_token():
    """Set the application token"""
    print(f"\n{Colors.CYAN}[*] Current token: {'***set***' if config.get_token() else 'Not set'}{Colors.ENDC}")
    token = input(f"{Colors.BLUE}Enter application token: {Colors.ENDC}").strip()
    
    if token:
        config.update_token(token)
        print(f"{Colors.GREEN}[✓] Token updated (changes take effect immediately){Colors.ENDC}")
    else:
        print(f"{Colors.RED}[!] No token entered{Colors.ENDC}")

def set_guild_id():
    """Set the guild ID"""
    print(f"\n{Colors.CYAN}[*] Current guild ID: {config.get_guild_id() or 'Not set'}{Colors.ENDC}")
    guild_id = input(f"{Colors.BLUE}Enter guild ID: {Colors.ENDC}").strip()
    
    if guild_id:
        config.update_guild_id(guild_id)
        print(f"{Colors.GREEN}[✓] Guild ID updated (changes take effect immediately){Colors.ENDC}")
    else:
        print(f"{Colors.RED}[!] No guild ID entered{Colors.ENDC}")

def set_own_user_id():
    """Set own user ID"""
    print(f"\n{Colors.CYAN}[*] Current user ID: {config.get_own_user_id() or 'Not set'}{Colors.ENDC}")
    user_id = input(f"{Colors.BLUE}Enter your user ID: {Colors.ENDC}").strip()
    
    if user_id:
        config.update_own_user_id(user_id)
        print(f"{Colors.GREEN}[✓] User ID updated (changes take effect immediately){Colors.ENDC}")
    else:
        print(f"{Colors.RED}[!] No user ID entered{Colors.ENDC}")

def set_gateway_message():
    """Set the gateway message"""
    print(f"\n{Colors.CYAN}[*] Current gateway message:{Colors.ENDC}")
    print(f"{Colors.YELLOW}{config.get_gateway_message()}{Colors.ENDC}")
    print(f"\n{Colors.CYAN}[*] Enter your gateway message (multiple lines supported, type 'END' on a new line when done):{Colors.ENDC}")
    
    lines = []
    while True:
        line = input()
        if line.strip() == "END":
            break
        lines.append(line)
    
    message = "\n".join(lines).strip()
    if message:
        config.update_gateway_message(message)
        print(f"{Colors.GREEN}[✓] Gateway message updated (changes take effect immediately){Colors.ENDC}")
    else:
        print(f"{Colors.RED}[!] No message entered{Colors.ENDC}")

def set_auto_deny_delay():
    """Set the auto-deny delay"""
    print(f"\n{Colors.CYAN}[*] Current auto-deny delay: {config.get_auto_deny_delay()} seconds{Colors.ENDC}")
    try:
        delay = int(input(f"{Colors.BLUE}Enter delay in seconds (e.g., 30): {Colors.ENDC}").strip())
        if delay > 0:
            config.update_auto_deny_delay(delay)
            print(f"{Colors.GREEN}[✓] Auto-deny delay updated to {delay} seconds (changes take effect immediately){Colors.ENDC}")
        else:
            print(f"{Colors.RED}[!] Delay must be a positive number{Colors.ENDC}")
    except ValueError:
        print(f"{Colors.RED}[!] Invalid number{Colors.ENDC}")

def view_config():
    """View current configuration"""
    print(f"\n{Colors.CYAN}{'='*60}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}          📋 CURRENT CONFIGURATION 📋{Colors.ENDC}")
    print(f"{Colors.CYAN}{'='*60}{Colors.ENDC}")
    print(f"{Colors.YELLOW}Token:{Colors.ENDC} {'***set***' if config.get_token() else 'Not set'}")
    print(f"{Colors.YELLOW}Guild ID:{Colors.ENDC} {config.get_guild_id() or 'Not set'}")
    print(f"{Colors.YELLOW}User ID:{Colors.ENDC} {config.get_own_user_id() or 'Not set'}")
    print(f"{Colors.YELLOW}Auto-Deny Delay:{Colors.ENDC} {config.get_auto_deny_delay()} seconds")
    print(f"{Colors.YELLOW}Gateway Message:{Colors.ENDC}")
    print(f"{Colors.GREEN}{config.get_gateway_message()}{Colors.ENDC}")
    print(f"{Colors.CYAN}{'='*60}{Colors.ENDC}")

def run_menu():
    """Run the interactive CLI menu"""
    while True:
        print_menu()
        choice = input(f"\n{Colors.BOLD}Select option: {Colors.ENDC}").strip()
        
        if choice == '1':
            set_token()
        elif choice == '2':
            set_guild_id()
        elif choice == '3':
            set_own_user_id()
        elif choice == '4':
            set_gateway_message()
        elif choice == '5':
            set_auto_deny_delay()
        elif choice == '6':
            view_config()
        elif choice == '7':
            if not config.get_token():
                print(f"{Colors.RED}[!] Please set application token first!{Colors.ENDC}")
                continue
            if not config.get_guild_id():
                print(f"{Colors.RED}[!] Please set guild ID first!{Colors.ENDC}")
                continue
            
            print(f"{Colors.CYAN}[*] Starting gateway bot...{Colors.ENDC}")
            print(f"{Colors.YELLOW}[*] Bot will gateway applications and auto-deny after {config.get_auto_deny_delay()} seconds{Colors.ENDC}")
            print(f"{Colors.YELLOW}[*] Press Ctrl+C to return to menu{Colors.ENDC}")
            print(f"{Colors.GREEN}[*] You can change settings in real-time by stopping and going back to menu{Colors.ENDC}")
            
            try:
                main_polling_loop()
            except KeyboardInterrupt:
                print(f"\n{Colors.YELLOW}[!] Stopped gateway bot{Colors.ENDC}")
        elif choice == '8':
            print(f"{Colors.GREEN}[*] Exiting...{Colors.ENDC}")
            break
        else:
            print(f"{Colors.RED}[!] Invalid option{Colors.ENDC}")

# ---------------------------
# Main Entry Point
# ---------------------------
if __name__ == "__main__":
    print(f"""
{Colors.CYAN}    ╔═══════════════════════════════════════════════════════════╗{Colors.ENDC}
{Colors.HEADER}{Colors.BOLD}    ║           🚪 Gateway Application Bot 🚪                  ║{Colors.ENDC}
{Colors.GREEN}    ║                                                           ║{Colors.ENDC}
{Colors.GREEN}    ║  Redirects applicants to real server and auto-denies     ║{Colors.ENDC}
{Colors.GREEN}    ║  Allows reapplication for repeated gateway messages      ║{Colors.ENDC}
{Colors.CYAN}    ╚═══════════════════════════════════════════════════════════╝{Colors.ENDC}
    """)
    
    try:
        run_menu()
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}[*] Exiting...{Colors.ENDC}")
    except Exception as e:
        print(f"\n{Colors.RED}[!] Fatal error: {e}{Colors.ENDC}")
