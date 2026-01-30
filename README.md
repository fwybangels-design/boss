# Discord Auth Application Bot

A Discord bot that automatically processes server join applications with an authentication system. Pre-authorized users are instantly accepted, while new users must complete authentication before being admitted.

## 🌟 Features

- **Auto-Accept for Authorized Users**: Users in the authorization list are automatically approved
- **Auth Request for New Users**: Non-authorized users receive an authentication link
- **Real-time Monitoring**: Automatically approves users once they complete authentication (2-3 seconds)
- **Message Forwarding**: Forward pre-existing messages from a "secret server" instead of sending new ones
- **Optional Additional Text**: Add custom text along with forwarded messages
- **Centralized Configuration**: Single `config.py` file for all settings
- **RestoreCord Integration**: Support for RestoreCord verification system
- **CLI Management Tool**: Easy command-line interface for managing authorized users
- **File-Based Storage**: Simple JSON files for managing users

## 📋 Quick Start

### 1. Install Dependencies

```bash
pip install requests>=2.25.0
```

### 2. Configure Settings

**All configuration is done in `config.py`** - a single file that contains all settings for all bots.

Edit `config.py` and set your values:

```python
# Discord credentials
TOKEN = "your_discord_user_token_here"
GUILD_ID = "your_server_id"
OWN_USER_ID = "your_user_id"

# Choose your authentication method
BOT_CLIENT_ID = "your_discord_app_client_id"  # For Discord OAuth2
# OR
RESTORECORD_URL = "https://verify.yourserver.com"  # For RestoreCord
RESTORECORD_SERVER_ID = "your_server_id"
# OR
AUTH_LINK = "https://t.me/addlist/your_telegram_group"  # For Telegram/other
```

**Alternatively, use environment variables** (more secure):
```bash
export DISCORD_TOKEN="your_token"
export DISCORD_BOT_CLIENT_ID="your_client_id"
export RESTORECORD_URL="https://verify.yourserver.com"
# etc.
```

### 3. (Optional) Configure Message Forwarding

Instead of sending new messages, you can forward pre-existing messages from a "secret server".

In `config.py`:

```python
# Enable message forwarding
FORWARD_SOURCE_CHANNEL_ID = "123456789012345678"  # Channel ID in your secret server
FORWARD_AUTH_MESSAGE_ID = "987654321098765432"    # Message ID for auth requests
FORWARD_WELCOME_MESSAGE_ID = "111222333444555666" # Message ID for welcome messages
FORWARD_SUCCESS_MESSAGE_ID = "222333444555666777" # Message ID for success messages

# Optional: Add extra text along with the forwarded message
FORWARD_AUTH_ADDITIONAL_TEXT = "Check your DMs for more info!"
FORWARD_WELCOME_ADDITIONAL_TEXT = "Welcome to our server! 🎉"
FORWARD_SUCCESS_ADDITIONAL_TEXT = ""  # Leave empty for no additional text
```

**Setting up forwarding:**
1. Create a "secret server" with a channel containing your template messages
2. Copy the channel ID and message IDs (Right-click → Copy ID with Developer Mode enabled)
3. Configure them in `config.py`
4. The bot will forward these messages instead of sending new ones
5. Optionally set additional text to send along with each forward

### 4. Start the Bot

```bash
python meow_with_auth.py
```

Expected output:
```
============================================================
Discord Application Bot Started (with Auth Handler)
============================================================
Auth Handler Enabled: True
Message Forwarding: True (if configured)
============================================================
✅ Auth monitor thread started
Polling for applications...
```

### 6. Manage Authorized Users

```bash
python auth_manager.py
```

Select options:
1. **List Authorized Users** - View all users in the whitelist
2. **View Pending Auth Requests** - See who's waiting for auth
3. **Authorize a User** - Add a user to whitelist (manual)
4. **Deauthorize a User** - Remove a user from whitelist
5. **Import Users from File** - Bulk add from text file
6. **Export Authorized Users** - Create backup

## 📖 How It Works

### For Authorized Users:
1. User applies to join server
2. Bot checks if user is in `authorized_users.json`
3. ✅ **If YES**: Opens interview channel → Sends welcome message → Auto-approves immediately

### For Non-Authorized Users:
1. User applies to join server
2. Bot checks if user is NOT in `authorized_users.json`
3. ⏳ Opens group chat → Sends auth request with link → Adds to `pending_auth.json`
4. User clicks link and completes authentication
5. Admin adds user to authorized list (manually or automatically)
6. Bot monitors and detects user is now authorized (every 2 seconds)
7. ✅ Sends success message → Auto-approves application

### With Message Forwarding:
- Instead of sending new messages, the bot forwards pre-configured messages from your secret server
- Optionally adds custom text along with the forward (e.g., "Welcome! Check your DMs")
- This allows consistent formatting and keeps your templates in one place
- Messages always come from the secret server, no matter which server runs the application

## 🔧 Configuration

**All configuration is centralized in `config.py`** - edit this one file to configure everything!

### Core Settings (in `config.py`)

```python
# Discord credentials
TOKEN = ""                    # Your Discord user token
GUILD_ID = ""                 # Your server/guild ID
OWN_USER_ID = ""              # Your Discord user ID

# Auth method (choose one)
BOT_CLIENT_ID = ""            # For Discord OAuth2
RESTORECORD_URL = ""          # For RestoreCord
AUTH_LINK = ""                # Or custom auth link

# Message forwarding (optional)
FORWARD_SOURCE_CHANNEL_ID = ""  # Secret server channel
FORWARD_AUTH_MESSAGE_ID = ""    # Auth request message
FORWARD_WELCOME_MESSAGE_ID = "" # Welcome message
FORWARD_SUCCESS_MESSAGE_ID = "" # Success message

# Optional additional text with forwards
FORWARD_AUTH_ADDITIONAL_TEXT = ""     # Extra text with auth forward
FORWARD_WELCOME_ADDITIONAL_TEXT = ""  # Extra text with welcome forward
FORWARD_SUCCESS_ADDITIONAL_TEXT = ""  # Extra text with success forward

# Timing
CHANNEL_CREATION_WAIT = 2     # Wait for Discord to create channel
AUTH_CHECK_INTERVAL = 2       # How often to check for new auths (seconds)
```

### Environment Variables

For better security, use environment variables (config.py will automatically load these):

```bash
export DISCORD_TOKEN="your_token"
export DISCORD_BOT_CLIENT_ID="your_client_id"
export RESTORECORD_URL="https://verify.yourserver.com"
export RESTORECORD_SERVER_ID="your_server_id"
export RESTORECORD_API_KEY="your_api_key"
export FORWARD_SOURCE_CHANNEL_ID="channel_id"
export FORWARD_AUTH_MESSAGE_ID="message_id"
export FORWARD_WELCOME_MESSAGE_ID="message_id"
export FORWARD_SUCCESS_MESSAGE_ID="message_id"
export FORWARD_AUTH_ADDITIONAL_TEXT="Check your DMs!"
export FORWARD_WELCOME_ADDITIONAL_TEXT="Welcome! 🎉"
export FORWARD_SUCCESS_ADDITIONAL_TEXT=""
```

## 📱 Usage Examples

### Example 1: Pre-Authorized User

```
User "John" (ID: 123456789) applies
→ Bot checks authorized list
→ Found! User is authorized
→ Opens interview channel
→ Forwards/sends welcome message
→ Auto-approves application
→ ✅ John is now in the server
```

### Example 2: New User with Manual Auth

```
User "Jane" (ID: 987654321) applies
→ Bot checks authorized list
→ Not found! User needs auth
→ Opens group chat
→ Forwards/sends auth request: "🔐 Click this link: [link]"
→ Jane clicks link and joins Telegram/completes verification
→ Admin runs: python auth_manager.py → Add Jane (ID: 987654321)
→ Bot detects Jane is authorized (within 2 seconds)
→ Forwards/sends success message
→ Auto-approves application
→ ✅ Jane is now in the server
```

### Example 3: RestoreCord Auto-Detection

```
User "Bob" (ID: 111222333) applies
→ Bot checks authorized list (not found locally)
→ Bot checks RestoreCord API
→ Bob is verified on RestoreCord!
→ Bot auto-adds Bob to local authorized list
→ Opens interview channel
→ Forwards/sends welcome message
→ Auto-approves application
→ ✅ Bob is now in the server (fully automatic!)
```

## 🛠️ CLI Management Tool

The `auth_manager.py` provides an interactive interface:

```bash
$ python auth_manager.py

=================================================================
              Discord Auth Handler - Management CLI
=================================================================

1. List Authorized Users
2. View Pending Auth Requests
3. Authorize a User
4. Deauthorize a User
5. Import Users from File
6. Export Authorized Users
7. Exit

Select an option (1-7):
```

### Bulk Adding Users

Create a text file with user IDs (one per line):

```
123456789012345678
987654321098765432
111222333444555666
```

Then use option 5 to import them all at once.

## 🔒 RestoreCord Integration

RestoreCord is a verification system for Discord servers. The bot can automatically detect when users verify through RestoreCord.

### Setup:

1. Set `RESTORECORD_URL` to your RestoreCord instance
2. Set `RESTORECORD_SERVER_ID` to your server ID
3. (Optional) Set `RESTORECORD_API_KEY` for API access
4. Users who verify on RestoreCord are automatically authorized

### How it works:

- When a user applies, bot checks local list first
- If not found locally, bot checks RestoreCord API
- If verified on RestoreCord, user is auto-authorized
- This happens in real-time with no manual intervention

## 📁 File Structure

```
.
├── config.py                # 🔧 Central configuration file (EDIT THIS!)
├── auth_handler.py          # Core authentication system
├── meow_with_auth.py        # Bot with auth integration
├── auth_manager.py          # CLI management tool
├── requirements.txt         # Python dependencies
├── README.md                # This file
├── .gitignore               # Git ignore rules
│
├── authorized_users.json    # Authorized users list (auto-created)
└── pending_auth.json        # Pending auth requests (auto-created)
```

**Important:** All configuration is done in `config.py` - this one file controls all bots!
├── .gitignore              # Git ignore rules
│
├── authorized_users.json   # Authorized users list (auto-created)
└── pending_auth.json       # Pending auth requests (auto-created)
```

## 🐛 Troubleshooting

### Bot Not Starting

**Error: "Invalid Token"**
- Your Discord token is invalid or expired
- Get a new token from Discord Developer Portal
- Update `TOKEN` in `auth_handler.py`

**Error: "Module not found"**
- Install dependencies: `pip install requests`

### Users Not Auto-Accepting

**Check if user is in authorized list:**
```bash
python auth_manager.py
# Select option 1
```

**Check logs for errors:**
- Look at console output when bot is running
- Check for rate limit warnings
- Verify `AUTH_CHECK_INTERVAL` is set correctly

**Verify RestoreCord (if using):**
- Test RestoreCord URL manually
- Check API key permissions
- Verify server ID is correct

### Message Forwarding Not Working

**Check configuration:**
- Verify `FORWARD_SOURCE_CHANNEL_ID` is correct
- Verify message IDs exist in that channel
- Make sure the bot/user has access to the source channel

**Test manually:**
- Try sending a message to the channel first
- Verify the channel is accessible
- Check Discord API errors in logs

## 🔐 Security Best Practices

1. **Never commit tokens**: Already configured in `.gitignore`
2. **Use environment variables**: More secure than hardcoding
3. **Protect auth files**: Keep `authorized_users.json` secure
4. **Regular backups**: Export authorized users regularly
5. **Review auth requests**: Don't blindly approve everyone
6. **Secure your secret server**: Only trusted users should access it

## 📊 Performance

- **Auth check interval**: 2 seconds (configurable)
- **Auto-approve time**: 2-3 seconds after authorization
- **RestoreCord check**: Real-time on application
- **Message forwarding**: Same speed as regular sending

## 🎯 Advanced Usage

### Custom Messages

Edit messages in `auth_handler.py`:

```python
AUTH_REQUEST_MESSAGE = """
🔐 **Custom Auth Message**

Your custom instructions here...

**Link:** {AUTH_LINK}
"""

AUTO_ACCEPT_MESSAGE = """
✅ **Custom Welcome**

Welcome to our server!
"""
```

### Toggle Auth On/Off

In `meow_with_auth.py`:

```python
USE_AUTH_HANDLER = True   # Auth enabled
USE_AUTH_HANDLER = False  # Auth disabled (regular meow.py behavior)
```

### Multiple Auth Methods

You can use multiple auth methods simultaneously:
- Set both `AUTH_LINK` and `RESTORECORD_URL`
- Users verified via either method will be authorized
- The bot checks both local list and RestoreCord

## 🆘 Support

If you encounter issues:

1. Check console logs for error messages
2. Verify all configuration values are correct
3. Test with a single user first
4. Check Discord API status
5. Review troubleshooting section above

## 📝 License

This is a private tool for Discord server management. Use responsibly and in accordance with Discord's Terms of Service.

## 🎉 Getting Started Checklist

- [ ] Install dependencies (`pip install requests`)
- [ ] Edit `config.py` with your Discord token and server IDs
- [ ] Set up authentication method in `config.py` (OAuth2/RestoreCord/Custom)
- [ ] (Optional) Configure message forwarding in `config.py`
- [ ] (Optional) Set additional text for forwards in `config.py`
- [ ] Start the bot (`python meow_with_auth.py`)
- [ ] Test with your own user ID
- [ ] Add authorized users as needed (`python auth_manager.py`)
- [ ] Monitor logs and adjust settings in `config.py`
- [ ] Start the bot (`python meow_with_auth.py`)
- [ ] Test with your own user ID
- [ ] Add authorized users as needed
- [ ] Monitor logs and adjust settings

---

**Happy auto-accepting! 🚀**
