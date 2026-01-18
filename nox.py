import discord
from discord.ext import commands
import asyncio
import json
import os
from datetime import datetime, timezone

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

# ---------------------------
# Configuration
# ---------------------------
CONFIG_FILE = "bot_config.json"
USERS_FILE = "dmed_users.txt"

# Default configuration structure
DEFAULT_CONFIG = {
    "bot_tokens": [],  # List of bot tokens for rotation
    "owner_id": "",  # Discord owner user ID
    "dm_message": "Welcome! Thanks for joining the server!",
    "mass_dm_message": "",  # Empty means use same as dm_message
    "dms_per_bot": 500,  # Number of DMs before rotating to next bot
    "current_bot_index": 0,
    "current_dm_count": 0
}

# ---------------------------
# User Tracking (Text File)
# ---------------------------
def init_user_tracking():
    """Initialize user tracking file if it doesn't exist"""
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'w') as f:
            f.write("# Format: user_id|username|discriminator|timestamp|bot_index\n")

def add_dmed_user(user_id, username, discriminator, bot_index):
    """Record a user that has been DMed"""
    init_user_tracking()
    
    # Read existing users to check if already exists
    existing_users = {}
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r') as f:
            for line in f:
                if line.startswith('#') or not line.strip():
                    continue
                parts = line.strip().split('|')
                if len(parts) >= 5:
                    existing_users[parts[0]] = line.strip()
    
    # Add or update user
    user_id_str = str(user_id)
    timestamp = datetime.now(timezone.utc).isoformat()
    user_line = f"{user_id_str}|{username}|{discriminator}|{timestamp}|{bot_index}\n"
    
    # Write back all users
    with open(USERS_FILE, 'w') as f:
        f.write("# Format: user_id|username|discriminator|timestamp|bot_index\n")
        for uid, line in existing_users.items():
            if uid != user_id_str:
                f.write(line + '\n')
        f.write(user_line)

def get_all_dmed_users():
    """Retrieve all users that have been DMed with their bot index"""
    init_user_tracking()
    users = []
    
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r') as f:
            for line in f:
                if line.startswith('#') or not line.strip():
                    continue
                parts = line.strip().split('|')
                if len(parts) >= 5:
                    user_id = parts[0]
                    username = parts[1]
                    discriminator = parts[2]
                    bot_index = int(parts[4])
                    users.append((user_id, username, discriminator, bot_index))
    
    return users

def get_dm_count():
    """Get total number of users DMed"""
    users = get_all_dmed_users()
    return len(users)

# ---------------------------
# Configuration Management
# ---------------------------
def load_config():
    """Load configuration from file or create default"""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    else:
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()

def save_config(config):
    """Save configuration to file"""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)

# ---------------------------
# Helper Functions
# ---------------------------
def get_user_discriminator(user):
    """Helper to get user discriminator with fallback"""
    return user.discriminator if hasattr(user, 'discriminator') else "0"

# ---------------------------
# Bot Setup
# ---------------------------
class DMBot:
    def __init__(self):
        self.config = load_config()
        self.current_bot = None
        self.bot_clients = []
        
    def get_current_bot_token(self):
        """Get the current bot token to use"""
        if not self.config["bot_tokens"]:
            return None
        
        index = self.config["current_bot_index"]
        if index >= len(self.config["bot_tokens"]):
            index = 0
            self.config["current_bot_index"] = 0
            save_config(self.config)
        
        return self.config["bot_tokens"][index]
    
    def rotate_bot(self):
        """Rotate to the next bot token"""
        if len(self.config["bot_tokens"]) <= 1:
            print("[!] No other bot tokens available to rotate to.")
            return False
        
        # Move to next bot
        self.config["current_bot_index"] = (self.config["current_bot_index"] + 1) % len(self.config["bot_tokens"])
        self.config["current_dm_count"] = 0
        save_config(self.config)
        
        print(f"[✓] Rotated to bot #{self.config['current_bot_index'] + 1}")
        return True
    
    def increment_dm_count(self):
        """Increment DM counter and rotate if needed"""
        self.config["current_dm_count"] += 1
        
        if self.config["current_dm_count"] >= self.config["dms_per_bot"]:
            print(f"[!] Reached DM limit ({self.config['dms_per_bot']}), rotating bot...")
            save_config(self.config)
            return self.rotate_bot()
        
        save_config(self.config)
        return True
    
    async def send_dm_to_user(self, user_id, message=None, bot_client=None):
        """Send a DM to a user by ID using specified bot client or current bot"""
        bot_to_use = bot_client if bot_client else self.current_bot
        
        if not bot_to_use:
            print(f"{Colors.RED}[!] No bot client available{Colors.ENDC}")
            return False
        
        if message is None:
            message = self.config["dm_message"]
        
        try:
            user = await bot_to_use.fetch_user(int(user_id))
            await user.send(message)
            
            # Track the DM (use the bot index from the bot_client or current)
            username = user.name
            discriminator = get_user_discriminator(user)
            add_dmed_user(user_id, username, discriminator, self.config["current_bot_index"])
            
            self.increment_dm_count()
            print(f"{Colors.GREEN}[✓] Sent DM to {username} (ID: {user_id}){Colors.ENDC}")
            return True
        except discord.Forbidden:
            print(f"{Colors.YELLOW}[!] Cannot send DM to user {user_id} (DMs disabled or blocked){Colors.ENDC}")
            return False
        except discord.NotFound:
            print(f"{Colors.YELLOW}[!] User {user_id} not found{Colors.ENDC}")
            return False
        except Exception as e:
            print(f"{Colors.RED}[!] Error sending DM to {user_id}: {e}{Colors.ENDC}")
            return False
    
    async def mass_dm_all_users(self, message=None, bot_clients_dict=None):
        """Mass DM all previously contacted users using the SAME bot that originally DMed them"""
        users = get_all_dmed_users()
        
        if not users:
            print(f"{Colors.YELLOW}[!] No users to DM{Colors.ENDC}")
            return
        
        # Use mass_dm_message if set, otherwise use dm_message
        if message is None:
            message = self.config.get("mass_dm_message", "") or self.config["dm_message"]
        
        print(f"{Colors.CYAN}[*] Starting mass DM to {len(users)} users...{Colors.ENDC}")
        print(f"{Colors.CYAN}[*] Each user will be DMed by the same bot that originally contacted them{Colors.ENDC}")
        
        success_count = 0
        fail_count = 0
        
        # Group users by bot index
        users_by_bot = {}
        for user_id, username, discriminator, bot_index in users:
            if bot_index not in users_by_bot:
                users_by_bot[bot_index] = []
            users_by_bot[bot_index].append((user_id, username, discriminator))
        
        # DM users grouped by their original bot
        for bot_index, user_list in users_by_bot.items():
            print(f"{Colors.CYAN}[*] Processing {len(user_list)} users with bot #{bot_index + 1}...{Colors.ENDC}")
            
            # Get the bot client for this index
            bot_client = bot_clients_dict.get(bot_index) if bot_clients_dict else self.current_bot
            
            if not bot_client:
                print(f"{Colors.RED}[!] Bot #{bot_index + 1} not available, skipping {len(user_list)} users{Colors.ENDC}")
                fail_count += len(user_list)
                continue
            
            for user_id, username, discriminator in user_list:
                try:
                    user = await bot_client.fetch_user(int(user_id))
                    await user.send(message)
                    success_count += 1
                    print(f"{Colors.GREEN}[✓] Sent DM to {username} (ID: {user_id}) via bot #{bot_index + 1}{Colors.ENDC}")
                except discord.Forbidden:
                    print(f"{Colors.YELLOW}[!] Cannot DM {username} (DMs disabled){Colors.ENDC}")
                    fail_count += 1
                except discord.NotFound:
                    print(f"{Colors.YELLOW}[!] User {username} not found{Colors.ENDC}")
                    fail_count += 1
                except Exception as e:
                    print(f"{Colors.RED}[!] Error DMing {username}: {e}{Colors.ENDC}")
                    fail_count += 1
                
                # Small delay to avoid rate limiting
                await asyncio.sleep(1)
        
        print(f"{Colors.GREEN}[✓] Mass DM complete: {success_count} success, {fail_count} failed{Colors.ENDC}")

# Global bot manager instance
bot_manager = DMBot()

# ---------------------------
# Discord Bot Setup
# ---------------------------
def create_bot():
    """Create a Discord bot instance"""
    intents = discord.Intents.default()
    intents.members = True
    intents.guilds = True
    intents.message_content = True
    
    bot = commands.Bot(command_prefix='!', intents=intents)
    
    @bot.event
    async def on_ready():
        print(f'[✓] Logged in as {bot.user.name} (ID: {bot.user.id})')
        print(f'[*] Bot is ready!')
        bot_manager.current_bot = bot
    
    @bot.event
    async def on_member_join(member):
        """Automatically DM users when they join the server"""
        print(f'[*] New member joined: {member.name} (ID: {member.id})')
        
        # Send DM
        message = bot_manager.config["dm_message"]
        try:
            await member.send(message)
            
            # Track the DM
            username = member.name
            discriminator = get_user_discriminator(member)
            add_dmed_user(member.id, username, discriminator, bot_manager.config["current_bot_index"])
            
            bot_manager.increment_dm_count()
            print(f"[✓] Sent welcome DM to {member.name}")
        except discord.Forbidden:
            print(f"[!] Cannot send DM to {member.name} (DMs disabled)")
        except Exception as e:
            print(f"[!] Error sending welcome DM: {e}")
    
    @bot.command(name='dm')
    async def dm_user(ctx, user_id: str, *, message: str):
        """DM a specific user by ID (Owner only)"""
        if str(ctx.author.id) != bot_manager.config["owner_id"]:
            await ctx.send("❌ You don't have permission to use this command.")
            return
        
        await ctx.send(f"📤 Sending DM to user {user_id}...")
        result = await bot_manager.send_dm_to_user(user_id, message)
        
        if result:
            await ctx.send(f"✅ DM sent successfully!")
        else:
            await ctx.send(f"❌ Failed to send DM.")
    
    @bot.command(name='massdm')
    async def mass_dm(ctx, *, message: str = None):
        """Mass DM all previously contacted users (Owner only)"""
        if str(ctx.author.id) != bot_manager.config["owner_id"]:
            await ctx.send("❌ You don't have permission to use this command.")
            return
        
        users_count = get_dm_count()
        await ctx.send(f"📤 Starting mass DM to {users_count} users...")
        
        await bot_manager.mass_dm_all_users(message)
        await ctx.send(f"✅ Mass DM completed!")
    
    @bot.command(name='stats')
    async def stats(ctx):
        """Show bot statistics (Owner only)"""
        if str(ctx.author.id) != bot_manager.config["owner_id"]:
            await ctx.send("❌ You don't have permission to use this command.")
            return
        
        total_users = get_dm_count()
        current_count = bot_manager.config["current_dm_count"]
        current_bot_index = bot_manager.config["current_bot_index"]
        total_bots = len(bot_manager.config["bot_tokens"])
        
        stats_msg = f"""
📊 **Bot Statistics**
━━━━━━━━━━━━━━━━━━━━
👥 Total Users DMed: {total_users}
📨 Current Bot DMs: {current_count}/{bot_manager.config['dms_per_bot']}
🤖 Active Bot: #{current_bot_index + 1} of {total_bots}
━━━━━━━━━━━━━━━━━━━━
        """
        await ctx.send(stats_msg)
    
    @bot.command(name='setmessage')
    async def set_message(ctx, *, message: str):
        """Set the default DM message (Owner only)"""
        if str(ctx.author.id) != bot_manager.config["owner_id"]:
            await ctx.send("❌ You don't have permission to use this command.")
            return
        
        bot_manager.config["dm_message"] = message
        save_config(bot_manager.config)
        await ctx.send(f"✅ Default DM message updated!")
    
    return bot

# ---------------------------
# CLI Menu Interface
# ---------------------------
def print_menu():
    """Display the main menu with colors"""
    print(f"\n{Colors.CYAN}{'='*60}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}          🤖 DISCORD DM BOT - CONTROL PANEL 🤖{Colors.ENDC}")
    print(f"{Colors.CYAN}{'='*60}{Colors.ENDC}")
    print(f"{Colors.GREEN}1.{Colors.ENDC} {Colors.BOLD}Configure Bot Tokens{Colors.ENDC}")
    print(f"{Colors.GREEN}2.{Colors.ENDC} {Colors.BOLD}Configure Owner ID{Colors.ENDC}")
    print(f"{Colors.GREEN}3.{Colors.ENDC} {Colors.BOLD}Set DM on Join Message{Colors.ENDC}")
    print(f"{Colors.GREEN}4.{Colors.ENDC} {Colors.BOLD}Set Mass DM Message{Colors.ENDC}")
    print(f"{Colors.GREEN}5.{Colors.ENDC} {Colors.BOLD}Set DMs per Bot (rotation threshold){Colors.ENDC}")
    print(f"{Colors.GREEN}6.{Colors.ENDC} {Colors.BOLD}View Statistics{Colors.ENDC}")
    print(f"{Colors.GREEN}7.{Colors.ENDC} {Colors.BOLD}Start Bot{Colors.ENDC}")
    print(f"{Colors.GREEN}8.{Colors.ENDC} {Colors.BOLD}Mass DM All Users (Manual){Colors.ENDC}")
    print(f"{Colors.GREEN}9.{Colors.ENDC} {Colors.BOLD}Exit{Colors.ENDC}")
    print(f"{Colors.CYAN}{'='*60}{Colors.ENDC}")

def configure_tokens():
    """Configure bot tokens"""
    print(f"\n{Colors.CYAN}[*] Current tokens: {len(bot_manager.config['bot_tokens'])}{Colors.ENDC}")
    print(f"\n{Colors.YELLOW}[*] Enter bot tokens (one per line, empty line to finish):{Colors.ENDC}")
    
    tokens = []
    while True:
        token = input(f"{Colors.BLUE}Token #{len(tokens) + 1}: {Colors.ENDC}").strip()
        if not token:
            break
        tokens.append(token)
    
    if tokens:
        bot_manager.config["bot_tokens"] = tokens
        bot_manager.config["current_bot_index"] = 0
        bot_manager.config["current_dm_count"] = 0
        save_config(bot_manager.config)
        print(f"{Colors.GREEN}[✓] Saved {len(tokens)} bot tokens{Colors.ENDC}")
    else:
        print(f"{Colors.RED}[!] No tokens added{Colors.ENDC}")

def configure_owner():
    """Configure owner ID"""
    print(f"\n{Colors.CYAN}[*] Current owner ID: {bot_manager.config.get('owner_id', 'Not set')}{Colors.ENDC}")
    owner_id = input(f"{Colors.BLUE}Enter owner Discord ID: {Colors.ENDC}").strip()
    
    if owner_id:
        bot_manager.config["owner_id"] = owner_id
        save_config(bot_manager.config)
        print(f"{Colors.GREEN}[✓] Owner ID saved{Colors.ENDC}")
    else:
        print(f"{Colors.RED}[!] No owner ID entered{Colors.ENDC}")

def set_dm_message():
    """Set the DM on join message"""
    print(f"\n{Colors.CYAN}[*] Current DM on Join message:{Colors.ENDC}")
    print(f"{Colors.YELLOW}{bot_manager.config['dm_message']}{Colors.ENDC}")
    message = input(f"{Colors.BLUE}Enter new DM on join message: {Colors.ENDC}").strip()
    
    if message:
        bot_manager.config["dm_message"] = message
        save_config(bot_manager.config)
        print(f"{Colors.GREEN}[✓] DM on join message updated{Colors.ENDC}")
    else:
        print(f"{Colors.RED}[!] No message entered{Colors.ENDC}")

def set_mass_dm_message():
    """Set the mass DM message (separate from on-join message)"""
    current = bot_manager.config.get("mass_dm_message", "")
    if not current:
        print(f"\n{Colors.CYAN}[*] Current Mass DM message: {Colors.YELLOW}(using same as DM on join){Colors.ENDC}")
    else:
        print(f"\n{Colors.CYAN}[*] Current Mass DM message:{Colors.ENDC}")
        print(f"{Colors.YELLOW}{current}{Colors.ENDC}")
    
    print(f"{Colors.CYAN}[*] Leave empty to use same as DM on join message{Colors.ENDC}")
    message = input(f"{Colors.BLUE}Enter mass DM message: {Colors.ENDC}").strip()
    
    bot_manager.config["mass_dm_message"] = message
    save_config(bot_manager.config)
    if message:
        print(f"{Colors.GREEN}[✓] Mass DM message set to custom message{Colors.ENDC}")
    else:
        print(f"{Colors.GREEN}[✓] Mass DM will use same message as DM on join{Colors.ENDC}")

def set_dms_per_bot():
    """Set the DM threshold for bot rotation"""
    print(f"\n{Colors.CYAN}[*] Current threshold: {bot_manager.config['dms_per_bot']}{Colors.ENDC}")
    try:
        threshold = int(input(f"{Colors.BLUE}Enter DMs per bot before rotation: {Colors.ENDC}").strip())
        if threshold > 0:
            bot_manager.config["dms_per_bot"] = threshold
            save_config(bot_manager.config)
            print(f"{Colors.GREEN}[✓] Threshold updated{Colors.ENDC}")
        else:
            print(f"{Colors.RED}[!] Must be a positive number{Colors.ENDC}")
    except ValueError:
        print(f"{Colors.RED}[!] Invalid number{Colors.ENDC}")

def view_statistics():
    """View bot statistics"""
    total_users = get_dm_count()
    current_count = bot_manager.config["current_dm_count"]
    current_bot_index = bot_manager.config["current_bot_index"]
    total_bots = len(bot_manager.config["bot_tokens"])
    
    print(f"\n{Colors.CYAN}{'='*60}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}               📊 STATISTICS 📊{Colors.ENDC}")
    print(f"{Colors.CYAN}{'='*60}{Colors.ENDC}")
    print(f"{Colors.YELLOW}👥 Total Users DMed:{Colors.ENDC} {Colors.BOLD}{total_users}{Colors.ENDC}")
    print(f"{Colors.YELLOW}📨 Current Bot DMs:{Colors.ENDC} {Colors.BOLD}{current_count}/{bot_manager.config['dms_per_bot']}{Colors.ENDC}")
    print(f"{Colors.YELLOW}🤖 Active Bot:{Colors.ENDC} {Colors.BOLD}#{current_bot_index + 1} of {total_bots}{Colors.ENDC}")
    print(f"{Colors.YELLOW}🔧 Bot Tokens Configured:{Colors.ENDC} {Colors.BOLD}{total_bots}{Colors.ENDC}")
    print(f"{Colors.CYAN}{'='*60}{Colors.ENDC}")

async def manual_mass_dm():
    """Manually trigger mass DM from menu - uses correct bot for each user"""
    if not bot_manager.config["bot_tokens"]:
        print(f"{Colors.RED}[!] No bot tokens configured!{Colors.ENDC}")
        return
    
    # Use mass_dm_message if set, otherwise ask
    default_msg = bot_manager.config.get("mass_dm_message", "") or bot_manager.config["dm_message"]
    print(f"\n{Colors.CYAN}[*] Default message:{Colors.ENDC} {Colors.YELLOW}{default_msg}{Colors.ENDC}")
    message = input(f"{Colors.BLUE}Enter message (leave empty for default): {Colors.ENDC}").strip()
    if not message:
        message = None
    
    user_count = get_dm_count()
    confirm = input(f"{Colors.YELLOW}Send DM to {user_count} users using their original bots? (yes/no): {Colors.ENDC}").strip().lower()
    if confirm != 'yes':
        print(f"{Colors.RED}[!] Cancelled{Colors.ENDC}")
        return
    
    # Create bot clients for all tokens
    print(f"{Colors.CYAN}[*] Starting bots for mass DM...{Colors.ENDC}")
    
    # Create multiple bot instances
    bot_clients = {}
    
    async def run_mass_dm():
        # Login all bots
        tasks = []
        for idx, token in enumerate(bot_manager.config["bot_tokens"]):
            bot = create_bot()
            bot_clients[idx] = bot
            tasks.append(bot.login(token))
        
        try:
            await asyncio.gather(*tasks)
            print(f"{Colors.GREEN}[✓] All bots logged in{Colors.ENDC}")
            
            # Now run mass DM with all bot clients
            await bot_manager.mass_dm_all_users(message, bot_clients)
            
        finally:
            # Close all bots
            for bot in bot_clients.values():
                await bot.close()
    
    try:
        await run_mass_dm()
    except Exception as e:
        print(f"{Colors.RED}[!] Error during mass DM: {e}{Colors.ENDC}")

def run_menu():
    """Run the interactive CLI menu"""
    init_user_tracking()
    
    while True:
        print_menu()
        choice = input(f"\n{Colors.BOLD}Select option: {Colors.ENDC}").strip()
        
        if choice == '1':
            configure_tokens()
        elif choice == '2':
            configure_owner()
        elif choice == '3':
            set_dm_message()
        elif choice == '4':
            set_mass_dm_message()
        elif choice == '5':
            set_dms_per_bot()
        elif choice == '6':
            view_statistics()
        elif choice == '7':
            if not bot_manager.config["bot_tokens"]:
                print(f"{Colors.RED}[!] Please configure bot tokens first!{Colors.ENDC}")
                continue
            
            print(f"{Colors.CYAN}[*] Starting bot...{Colors.ENDC}")
            token = bot_manager.get_current_bot_token()
            
            if not token:
                print(f"{Colors.RED}[!] No valid bot token{Colors.ENDC}")
                continue
            
            bot = create_bot()
            print(f"{Colors.GREEN}[*] Using bot #{bot_manager.config['current_bot_index'] + 1}{Colors.ENDC}")
            print(f"{Colors.YELLOW}[*] Press Ctrl+C to stop the bot{Colors.ENDC}")
            
            try:
                bot.run(token)
            except KeyboardInterrupt:
                print(f"\n{Colors.YELLOW}[!] Bot stopped by user{Colors.ENDC}")
            except Exception as e:
                print(f"{Colors.RED}[!] Error running bot: {e}{Colors.ENDC}")
        elif choice == '8':
            try:
                asyncio.run(manual_mass_dm())
            except Exception as e:
                print(f"{Colors.RED}[!] Error: {e}{Colors.ENDC}")
        elif choice == '9':
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
{Colors.HEADER}{Colors.BOLD}    ║       🤖 Discord DM Bot with Token Rotation 🤖          ║{Colors.ENDC}
{Colors.GREEN}    ║                    Version 2.0                            ║{Colors.ENDC}
{Colors.CYAN}    ╚═══════════════════════════════════════════════════════════╝{Colors.ENDC}
    """)
    
    try:
        run_menu()
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}[*] Exiting...{Colors.ENDC}")
    except Exception as e:
        print(f"\n{Colors.RED}[!] Fatal error: {e}{Colors.ENDC}")
