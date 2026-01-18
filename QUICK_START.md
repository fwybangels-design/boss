# Quick Start Guide

## Step 1: Install Dependencies

```bash
pip install discord.py
```

Or use the requirements file:
```bash
pip install -r requirements.txt
```

## Step 2: Create Discord Bot(s)

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application" and give it a name
3. Go to "Bot" section and click "Add Bot"
4. Under "Privileged Gateway Intents", enable:
   - ✅ PRESENCE INTENT
   - ✅ SERVER MEMBERS INTENT
   - ✅ MESSAGE CONTENT INTENT
5. Click "Reset Token" to get your bot token (save this!)
6. Repeat for each bot you want to use (recommended: 2-3 bots)

## Step 3: Invite Bot(s) to Your Server

1. In Developer Portal, go to "OAuth2" → "URL Generator"
2. Select scopes:
   - ✅ bot
3. Select bot permissions:
   - ✅ Send Messages
   - ✅ Read Message History
4. Copy the generated URL and open it in your browser
5. Select your server and authorize the bot
6. Repeat for each bot

## Step 4: Get Your Discord User ID

1. Open Discord and go to Settings → Advanced
2. Enable "Developer Mode"
3. Right-click your username and select "Copy ID"
4. Save this ID

## Step 5: Run the Bot

```bash
python nox.py
```

You'll see the control panel:

```
==================================================
     DISCORD DM BOT - CONTROL PANEL
==================================================
1. Configure Bot Tokens
2. Configure Owner ID
3. Set DM Message
4. Set DMs per Bot (rotation threshold)
5. View Statistics
6. Start Bot
7. Mass DM All Users (Manual)
8. Exit
==================================================
```

## Step 6: Configure the Bot

### 6.1 Add Bot Tokens (Option 1)
```
Select option: 1
Token #1: [paste your first bot token]
Token #2: [paste your second bot token]
Token #3: [press Enter to finish]
```

### 6.2 Set Owner ID (Option 2)
```
Select option: 2
Enter owner Discord ID: [paste your user ID]
```

### 6.3 Customize DM Message (Option 3)
```
Select option: 3
Enter new DM message: Welcome to our server! Check out #rules
```

### 6.4 Set Rotation Threshold (Option 4)
```
Select option: 4
Enter DMs per bot before rotation: 500
```

## Step 7: Start the Bot (Option 6)

```
Select option: 6
[*] Starting bot...
[*] Using bot #1
[✓] Logged in as MyBot (ID: 123456789...)
[*] Bot is ready!
```

Keep this terminal open. The bot is now running!

## Using Bot Commands

### In Discord Server

#### Send DM to specific user:
```
!dm 123456789012345678 Hey there! Check out our new updates.
```

#### Mass DM all tracked users:
```
!massdm Important announcement for everyone!
```

#### Check statistics:
```
!stats
```

Output:
```
📊 **Bot Statistics**
━━━━━━━━━━━━━━━━━━━━
👥 Total Users DMed: 1,234
📨 Current Bot DMs: 345/500
🤖 Active Bot: #2 of 3
━━━━━━━━━━━━━━━━━━━━
```

#### Change default message:
```
!setmessage New welcome message here!
```

## How It Works

### Auto-DM on Join
When a user joins your server:
1. Bot automatically sends them the configured DM message
2. User is added to the database
3. DM counter increments
4. If counter reaches 500 (or your threshold), bot automatically rotates to next token

### Mass DM
You can mass DM all users who have been DMed before:
- Works even if users left the server
- Works even if the server is deleted
- Uses the database of tracked users

### Token Rotation
When a bot sends 500 DMs (default):
```
[!] Reached DM limit (500), rotating bot...
[✓] Rotated to bot #2
```
The next DM will use bot #2, and so on.

## Tips

1. **Start with 2-3 bot tokens** for safety
2. **Set threshold to 400-500 DMs** - safer range
3. **Test with a small server first** before using on large servers
4. **Keep the terminal open** while bot is running
5. **Backup your database** (`dm_tracking.db`) periodically

## Troubleshooting

### "Cannot send DM to user"
- User has DMs disabled from server members
- User blocked the bot
- This is normal - not everyone accepts DMs

### "Bot not responding to commands"
- Make sure you're the owner (check owner ID)
- Verify bot has "Send Messages" permission
- Check that bot is online

### "No bot tokens configured"
- You must add at least 1 bot token (Option 1)
- Tokens should be from Discord Developer Portal

## Safety Notes

⚠️ **Important:**
- Mass DMing can violate Discord ToS
- Bots can get banned for excessive DM activity
- This is for educational purposes only
- Use at your own risk
- The author is not responsible for any bans

## Files Generated

After running the bot, you'll see these files:
- `bot_config.json` - Your configuration (tokens, owner ID, etc.)
- `dm_tracking.db` - SQLite database of all DMed users

**Never share these files!** They contain sensitive data.

## Stopping the Bot

Press `Ctrl+C` in the terminal to stop the bot.

```
^C
[!] Bot stopped by user
```

Then you'll be back at the menu. Select option 8 to exit.
