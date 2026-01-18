import discord
from discord.ext import commands
import sqlite3
import asyncio
import json
import os
from datetime import datetime

# ---------------------------
# Configuration
# ---------------------------
CONFIG_FILE = "bot_config.json"

# Default configuration structure
DEFAULT_CONFIG = {
    "bot_tokens": [],  # List of bot tokens for rotation
    "owner_id": "",  # Discord owner user ID
    "dm_message": "Welcome! Thanks for joining the server!",
    "dms_per_bot": 500,  # Number of DMs before rotating to next bot
    "current_bot_index": 0,
    "current_dm_count": 0
}

# ---------------------------
# Database Setup
# ---------------------------
def init_database():
    """Initialize SQLite database for tracking DMed users"""
    conn = sqlite3.connect('dm_tracking.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS dmed_users
                 (user_id TEXT PRIMARY KEY, 
                  username TEXT,
                  discriminator TEXT,
                  dm_timestamp TEXT,
                  bot_index INTEGER)''')
    conn.commit()
    conn.close()

def add_dmed_user(user_id, username, discriminator, bot_index):
    """Record a user that has been DMed"""
    conn = sqlite3.connect('dm_tracking.db')
    c = conn.cursor()
    c.execute('''INSERT OR REPLACE INTO dmed_users 
                 (user_id, username, discriminator, dm_timestamp, bot_index)
                 VALUES (?, ?, ?, ?, ?)''',
              (str(user_id), username, discriminator, 
               datetime.utcnow().isoformat(), bot_index))
    conn.commit()
    conn.close()

def get_all_dmed_users():
    """Retrieve all users that have been DMed"""
    conn = sqlite3.connect('dm_tracking.db')
    c = conn.cursor()
    c.execute('SELECT user_id, username, discriminator FROM dmed_users')
    users = c.fetchall()
    conn.close()
    return users

def get_dm_count():
    """Get total number of users DMed"""
    conn = sqlite3.connect('dm_tracking.db')
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM dmed_users')
    count = c.fetchone()[0]
    conn.close()
    return count

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
        save_config(self.config)
        
        if self.config["current_dm_count"] >= self.config["dms_per_bot"]:
            print(f"[!] Reached DM limit ({self.config['dms_per_bot']}), rotating bot...")
            return self.rotate_bot()
        return True
    
    async def send_dm_to_user(self, user_id, message=None):
        """Send a DM to a user by ID"""
        if not self.current_bot:
            print("[!] No bot client available")
            return False
        
        if message is None:
            message = self.config["dm_message"]
        
        try:
            user = await self.current_bot.fetch_user(int(user_id))
            await user.send(message)
            
            # Track the DM
            username = user.name
            discriminator = user.discriminator if hasattr(user, 'discriminator') else "0"
            add_dmed_user(user_id, username, discriminator, self.config["current_bot_index"])
            
            self.increment_dm_count()
            print(f"[✓] Sent DM to {username} (ID: {user_id})")
            return True
        except discord.Forbidden:
            print(f"[!] Cannot send DM to user {user_id} (DMs disabled or blocked)")
            return False
        except discord.NotFound:
            print(f"[!] User {user_id} not found")
            return False
        except Exception as e:
            print(f"[!] Error sending DM to {user_id}: {e}")
            return False
    
    async def mass_dm_all_users(self, message=None):
        """Mass DM all previously contacted users"""
        users = get_all_dmed_users()
        
        if not users:
            print("[!] No users to DM")
            return
        
        print(f"[*] Starting mass DM to {len(users)} users...")
        
        success_count = 0
        fail_count = 0
        
        for user_id, username, discriminator in users:
            result = await self.send_dm_to_user(user_id, message)
            if result:
                success_count += 1
            else:
                fail_count += 1
            
            # Small delay to avoid rate limiting
            await asyncio.sleep(1)
        
        print(f"[✓] Mass DM complete: {success_count} success, {fail_count} failed")

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
            discriminator = member.discriminator if hasattr(member, 'discriminator') else "0"
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
    """Display the main menu"""
    print("\n" + "="*50)
    print("     DISCORD DM BOT - CONTROL PANEL")
    print("="*50)
    print("1. Configure Bot Tokens")
    print("2. Configure Owner ID")
    print("3. Set DM Message")
    print("4. Set DMs per Bot (rotation threshold)")
    print("5. View Statistics")
    print("6. Start Bot")
    print("7. Mass DM All Users (Manual)")
    print("8. Exit")
    print("="*50)

def configure_tokens():
    """Configure bot tokens"""
    print("\n[*] Current tokens: ", len(bot_manager.config["bot_tokens"]))
    print("\n[*] Enter bot tokens (one per line, empty line to finish):")
    
    tokens = []
    while True:
        token = input(f"Token #{len(tokens) + 1}: ").strip()
        if not token:
            break
        tokens.append(token)
    
    if tokens:
        bot_manager.config["bot_tokens"] = tokens
        bot_manager.config["current_bot_index"] = 0
        bot_manager.config["current_dm_count"] = 0
        save_config(bot_manager.config)
        print(f"[✓] Saved {len(tokens)} bot tokens")
    else:
        print("[!] No tokens added")

def configure_owner():
    """Configure owner ID"""
    print(f"\n[*] Current owner ID: {bot_manager.config.get('owner_id', 'Not set')}")
    owner_id = input("Enter owner Discord ID: ").strip()
    
    if owner_id:
        bot_manager.config["owner_id"] = owner_id
        save_config(bot_manager.config)
        print("[✓] Owner ID saved")
    else:
        print("[!] No owner ID entered")

def set_dm_message():
    """Set the default DM message"""
    print(f"\n[*] Current message: {bot_manager.config['dm_message']}")
    message = input("Enter new DM message: ").strip()
    
    if message:
        bot_manager.config["dm_message"] = message
        save_config(bot_manager.config)
        print("[✓] DM message updated")
    else:
        print("[!] No message entered")

def set_dms_per_bot():
    """Set the DM threshold for bot rotation"""
    print(f"\n[*] Current threshold: {bot_manager.config['dms_per_bot']}")
    try:
        threshold = int(input("Enter DMs per bot before rotation: ").strip())
        if threshold > 0:
            bot_manager.config["dms_per_bot"] = threshold
            save_config(bot_manager.config)
            print("[✓] Threshold updated")
        else:
            print("[!] Must be a positive number")
    except ValueError:
        print("[!] Invalid number")

def view_statistics():
    """View bot statistics"""
    total_users = get_dm_count()
    current_count = bot_manager.config["current_dm_count"]
    current_bot_index = bot_manager.config["current_bot_index"]
    total_bots = len(bot_manager.config["bot_tokens"])
    
    print("\n" + "="*50)
    print("     STATISTICS")
    print("="*50)
    print(f"Total Users DMed: {total_users}")
    print(f"Current Bot DMs: {current_count}/{bot_manager.config['dms_per_bot']}")
    print(f"Active Bot: #{current_bot_index + 1} of {total_bots}")
    print(f"Bot Tokens Configured: {total_bots}")
    print("="*50)

async def manual_mass_dm():
    """Manually trigger mass DM from menu"""
    if not bot_manager.config["bot_tokens"]:
        print("[!] No bot tokens configured!")
        return
    
    message = input("Enter message (leave empty for default): ").strip()
    if not message:
        message = None
    
    confirm = input(f"Send DM to {get_dm_count()} users? (yes/no): ").strip().lower()
    if confirm != 'yes':
        print("[!] Cancelled")
        return
    
    # Create temporary bot for manual DM
    print("[*] Starting bot for mass DM...")
    token = bot_manager.get_current_bot_token()
    
    if not token:
        print("[!] No valid bot token")
        return
    
    temp_bot = create_bot()
    
    async def run_mass_dm():
        async with temp_bot:
            await temp_bot.login(token)
            bot_manager.current_bot = temp_bot
            await bot_manager.mass_dm_all_users(message)
            await temp_bot.close()
    
    try:
        await run_mass_dm()
    except Exception as e:
        print(f"[!] Error during mass DM: {e}")

def run_menu():
    """Run the interactive CLI menu"""
    init_database()
    
    while True:
        print_menu()
        choice = input("\nSelect option: ").strip()
        
        if choice == '1':
            configure_tokens()
        elif choice == '2':
            configure_owner()
        elif choice == '3':
            set_dm_message()
        elif choice == '4':
            set_dms_per_bot()
        elif choice == '5':
            view_statistics()
        elif choice == '6':
            if not bot_manager.config["bot_tokens"]:
                print("[!] Please configure bot tokens first!")
                continue
            
            print("[*] Starting bot...")
            token = bot_manager.get_current_bot_token()
            
            if not token:
                print("[!] No valid bot token")
                continue
            
            bot = create_bot()
            print(f"[*] Using bot #{bot_manager.config['current_bot_index'] + 1}")
            print("[*] Press Ctrl+C to stop the bot")
            
            try:
                bot.run(token)
            except KeyboardInterrupt:
                print("\n[!] Bot stopped by user")
            except Exception as e:
                print(f"[!] Error running bot: {e}")
        elif choice == '7':
            try:
                asyncio.run(manual_mass_dm())
            except Exception as e:
                print(f"[!] Error: {e}")
        elif choice == '8':
            print("[*] Exiting...")
            break
        else:
            print("[!] Invalid option")

# ---------------------------
# Main Entry Point
# ---------------------------
if __name__ == "__main__":
    print("""
    ╔═══════════════════════════════════════════════════════╗
    ║         Discord DM Bot with Token Rotation           ║
    ║                    Version 1.0                        ║
    ╚═══════════════════════════════════════════════════════╝
    """)
    
    try:
        run_menu()
    except KeyboardInterrupt:
        print("\n[*] Exiting...")
    except Exception as e:
        print(f"\n[!] Fatal error: {e}")
