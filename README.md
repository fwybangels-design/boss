# Discord Bot Collection

This repository contains multiple Discord bots for different purposes:

1. **nox.py** - Discord DM Bot with Token Rotation for automatic member DMs
2. **meow.py** - Event-driven Discord bot for application processing and interviews
3. **gateway.py** - Gateway-based Discord bot implementation

## meow.py - Application Processing Bot

An event-driven Discord bot that automatically processes server join applications and conducts interviews via Discord.

### Features

- **Event-Driven Architecture**: Instantly responds to application submissions
- **Automated Interview System**: Opens group DM channels for applicants
- **Screenshot Verification**: Tracks when users submit required screenshots  
- **Member Addition Monitoring**: Detects when users add others to group DMs
- **Rate Limit Handling**: Robust rate limiting with exponential backoff
- **Connection Pooling**: Efficient HTTP session management

### Installation (meow.py)

1. Install required dependencies:
```bash
pip install discord.py>=2.0.0 requests>=2.25.0
```

2. Configure the bot token (choose one method):

   **Method 1: Direct configuration (RECOMMENDED - Simple copy & paste)**
   - Open `meow.py` in a text editor
   - Find the line near the top: `TOKEN = ""`
   - Paste your Discord bot token between the quotes: `TOKEN = "your_discord_bot_token_here"`
   - ⚠️ **SECURITY WARNING**: Do NOT commit your token to version control! Keep your token secret and never push it to GitHub or share it publicly.

   **Method 2: Environment variable (More secure for version control)**
   ```bash
   export DISCORD_TOKEN='your_discord_bot_token_here'
   ```

3. Run the bot:
```bash
python meow.py
```

### Getting Your Discord Bot Token

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Select your application (or create a new one)
3. Go to the 'Bot' section
4. Click 'Reset Token' or 'Copy' to get your token
5. Paste the token in the `TOKEN = ""` line at the top of `meow.py`

### Security Best Practices

⚠️ **Important Security Notes:**
- **Never commit your Discord token to version control!** If you paste your token directly in `meow.py`, be careful not to push that change to GitHub.
- If you accidentally commit your token, regenerate it immediately in the Discord Developer Portal.
- For better security when using version control, use the environment variable method instead of direct configuration.
- Keep your token secret and never share it publicly.

### Error Messages

If you see a **401 Unauthorized** error, it means:
- Your Discord token is missing, empty, or invalid
- The token has been revoked or regenerated

The bot will now provide clear error messages with instructions on how to fix the issue:

```
❌ ERROR: Discord TOKEN is not configured!
Please set your Discord bot token using one of these methods:
  1. Paste your token in the TOKEN variable at the top of meow.py (RECOMMENDED)
     Find the line: TOKEN = ""
     Replace it with: TOKEN = "your_bot_token_here"

  2. Or set the DISCORD_TOKEN environment variable:
     export DISCORD_TOKEN='your_bot_token_here'
```

## nox.py - DM Bot with Token Rotation

A Discord bot that automatically DMs users when they join a server and supports mass DM functionality with automatic token rotation to avoid rate limits and bans.

### Features (nox.py)

- **Automatic DM on Join**: Sends a customizable message to users when they join the server
- **Token Rotation**: Automatically rotates between multiple bot tokens after a configurable number of DMs (default: 500)
- **Mass DM with Bot Tracking**: Send messages to all previously contacted users using the SAME bot that originally DMed them (important for users not in server)
- **Separate Messages**: Different messages for join DM vs mass DM
- **Owner-Only Commands**: All commands are restricted to the configured owner ID
- **Simple Text File Tracking**: Uses simple .txt files to track all DMed users (no database setup needed!)
- **Colorful CLI Menu**: Eye-catching menu with colors and emojis
- **DM by User ID**: Can DM users even if they're not in the server

### Installation (nox.py)

1. Install required dependencies:
```bash
pip install discord.py
```

2. Run the bot:
```bash
python nox.py
```

## Configuration

When you first run the bot, you'll be presented with a colorful menu:

```
============================================================
          🤖 DISCORD DM BOT - CONTROL PANEL 🤖
============================================================
1. Configure Bot Tokens
2. Configure Owner ID
3. Set DM on Join Message
4. Set Mass DM Message
5. Set DMs per Bot (rotation threshold)
6. View Statistics
7. Start Bot
8. Mass DM All Users (Manual)
9. Exit
============================================================
```

### Initial Setup

1. **Configure Bot Tokens** (Option 1)
   - Add multiple Discord bot tokens (one per line)
   - The bot will rotate through these tokens automatically
   - Recommendation: Add at least 2-3 tokens for redundancy

2. **Configure Owner ID** (Option 2)
   - Enter your Discord user ID
   - Only this user can use bot commands

3. **Set DM on Join Message** (Option 3)
   - Customize the message sent to users when they join the server

4. **Set Mass DM Message** (Option 4)
   - Set a separate message for mass DMs (optional)
   - Leave empty to use the same as the join message

5. **Set DMs per Bot** (Option 5)
   - Configure how many DMs to send before rotating to next token
   - Default: 500 (adjust based on your risk tolerance)

6. **Start Bot** (Option 7)
   - Once configured, start the bot to begin monitoring

## Bot Commands

All commands require the user to be the configured owner.

### `!dm <user_id> <message>`
Send a DM to a specific user by their Discord ID.

**Example:**
```
!dm 123456789012345678 Hello! This is a test message.
```

### `!massdm [message]`
Send a mass DM to all users that have been previously DMed by the bot. **Each user will be contacted by the same bot that originally DMed them** - this is crucial because a bot can only DM users it shares a server with OR has previously DMed.

**Example:**
```
!massdm Important announcement for all members!
```

If no message is provided, it uses the mass DM message (or DM on join message if not set separately).

### `!stats`
Display bot statistics including:
- Total users DMed
- Current bot DM count
- Active bot number
- Total configured bots

**Example output:**
```
📊 **Bot Statistics**
━━━━━━━━━━━━━━━━━━━━
👥 Total Users DMed: 1,234
📨 Current Bot DMs: 345/500
🤖 Active Bot: #2 of 3
━━━━━━━━━━━━━━━━━━━━
```

### `!setmessage <message>`
Change the default DM message that is sent when users join.

**Example:**
```
!setmessage Welcome to our server! Please read the rules.
```

## How It Works

### Token Rotation System

1. Bot tracks the number of DMs sent with the current token
2. When the threshold is reached (default: 500), it automatically rotates to the next token
3. The rotation state is saved to `bot_config.json`
4. If all tokens have been used, it cycles back to the first one

### DM Tracking

All DMed users are stored in `dmed_users.txt` (simple text file) with:
- User ID
- Username
- Discriminator
- Timestamp of DM
- Which bot token was used (bot index)

**Format:** `user_id|username|discriminator|timestamp|bot_index`

This allows you to:
- Mass DM users even after they leave the server
- Each user gets DMed by the SAME bot that originally contacted them
- Track all interactions in a simple, readable text file
- No database setup required!

### Automatic DM on Join

When a user joins the server:
1. Bot detects the `on_member_join` event
2. Sends the configured DM on join message
3. Records the user in the text file with the bot index
4. Increments the DM counter
5. Rotates to next token if threshold is reached

### Mass DM with Bot Tracking

When you mass DM all users:
1. Bot reads all users from `dmed_users.txt`
2. Groups users by which bot originally DMed them
3. Logs in all bot tokens that are needed
4. Each user is DMed by their original bot
5. This ensures the bot can DM users even if they left the server

**Why this matters:** A Discord bot can only DM users that either:
- Share a server with the bot, OR
- Have been previously DMed by that specific bot

By tracking which bot DMed which user, we ensure mass DMs work correctly!

## Files Created

- `bot_config.json` - Stores bot tokens, owner ID, messages, and configuration
- `dmed_users.txt` - Simple text file tracking all DMed users

**Note:** These files are automatically added to `.gitignore` to prevent accidentally committing sensitive data.

## Important Notes

### Discord Terms of Service

⚠️ **Warning**: Mass DMing users may violate Discord's Terms of Service. This bot is provided for educational purposes only. Use at your own risk. The author is not responsible for any account bans or terminations.

### Rate Limiting

- Bot includes 1-second delays between mass DMs to avoid rate limits
- Token rotation helps distribute the load
- Adjust `dms_per_bot` based on your needs and risk tolerance

### Required Intents

The bot requires the following Discord intents:
- `members` - To detect when users join
- `guilds` - To access guild information
- `message_content` - To process commands

Make sure these are enabled in your Discord Developer Portal for each bot.

## Troubleshooting

### Bot won't start
- Check that bot tokens are valid
- Ensure owner ID is correctly set
- Verify the bot has the required intents enabled

### DMs not sending
- Check that users have DMs enabled
- Verify the bot is not rate limited
- Check that the bot is in the same server as the user (for on_member_join)

### Token rotation not working
- Ensure you have multiple tokens configured
- Check that `dms_per_bot` threshold is set
- Review the console logs for rotation messages

## Security

- Never share your `bot_config.json` file
- Keep your bot tokens secret
- Use a `.gitignore` to prevent committing sensitive files
- Regularly rotate your bot tokens if compromised

## License

This project is provided as-is for educational purposes.
