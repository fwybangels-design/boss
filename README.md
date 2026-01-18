# Discord DM Bot with Token Rotation

A Discord bot that automatically DMs users when they join a server and supports mass DM functionality with automatic token rotation to avoid rate limits and bans.

## Features

- **Automatic DM on Join**: Sends a customizable message to users when they join the server
- **Token Rotation**: Automatically rotates between multiple bot tokens after a configurable number of DMs (default: 500)
- **Mass DM**: Send messages to all previously contacted users, even if the server is deleted
- **Owner-Only Commands**: All commands are restricted to the configured owner ID
- **Persistent Tracking**: Uses SQLite database to track all DMed users
- **CLI Menu Interface**: Easy-to-use command-line interface for configuration and control
- **DM by User ID**: Can DM users even if they're not in the server

## Installation

1. Install required dependencies:
```bash
pip install discord.py
```

2. Run the bot:
```bash
python nox.py
```

## Configuration

When you first run the bot, you'll be presented with a menu:

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

### Initial Setup

1. **Configure Bot Tokens** (Option 1)
   - Add multiple Discord bot tokens (one per line)
   - The bot will rotate through these tokens automatically
   - Recommendation: Add at least 2-3 tokens for redundancy

2. **Configure Owner ID** (Option 2)
   - Enter your Discord user ID
   - Only this user can use bot commands

3. **Set DM Message** (Option 3)
   - Customize the message sent to users when they join

4. **Set DMs per Bot** (Option 4)
   - Configure how many DMs to send before rotating to next token
   - Default: 500 (adjust based on your risk tolerance)

5. **Start Bot** (Option 6)
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
Send a mass DM to all users that have been previously DMed by the bot.

**Example:**
```
!massdm Important announcement for all members!
```

If no message is provided, it uses the default DM message.

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

All DMed users are stored in `dm_tracking.db` (SQLite database) with:
- User ID
- Username
- Discriminator
- Timestamp of DM
- Which bot token was used

This allows you to:
- Mass DM users even after they leave the server
- Track all interactions
- Maintain a persistent list of contacted users

### Automatic DM on Join

When a user joins the server:
1. Bot detects the `on_member_join` event
2. Sends the configured DM message
3. Records the user in the database
4. Increments the DM counter
5. Rotates to next token if threshold is reached

## Files Created

- `bot_config.json` - Stores bot tokens, owner ID, and configuration
- `dm_tracking.db` - SQLite database tracking all DMed users

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
