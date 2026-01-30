# Discord Auth Application Bot

A Discord bot that automatically processes server join applications with RestoreCord authentication. Users are verified in real-time via RestoreCord API - no local storage needed.

## 📚 Quick Summary - How It Works

**In 30 seconds:**

1. Someone applies to join your Discord server
2. Bot checks RestoreCord API: "Are they verified?"
   - ✅ **YES** → Auto-approves immediately (NO interview channel opened, NO messages sent)
   - ❌ **NO** → Opens interview → Forwards auth request → They authenticate → Auto-approves → Sends success message

**Message Forwarding:**

The bot forwards a pre-made auth request message from your "secret server":
- **FORWARD_AUTH_MESSAGE_ID** = Template asking users to verify (contains RestoreCord link)
- **FORWARD_AUTH_ADDITIONAL_TEXT** = Optional extra text to add with the forward

**Post-Acceptance Message:**

After a user completes auth and is approved, bot sends a simple success message (NOT forwarded):
- Example: "✅ Authentication successful! Make sure to join VC https://discord.gg/example"

📖 **For detailed explanation, see [HOW_IT_WORKS.md](HOW_IT_WORKS.md)**

---

## 🌟 Features

- **RestoreCord API Integration**: Real-time verification via RestoreCord API polling
- **No Local Storage**: No authorized_users.json file - all checks via API
- **Silent Auto-Accept**: Already verified users are auto-approved WITHOUT opening interview channels
- **Auth Request Forwarding**: Forward pre-existing auth request messages from a "secret server"
- **Optional Additional Text**: Add custom text along with forwarded messages
- **Post-Acceptance Message**: Simple success message with server invite link (not forwarded)
- **Centralized Configuration**: Single `config.py` file for all settings
- **CLI Management Tool**: View pending auth requests and check user verification status
- **Real-time Monitoring**: Automatically approves users within 2-3 seconds of verification

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

# RestoreCord configuration (REQUIRED)
RESTORECORD_URL = "https://verify.yourserver.com"
RESTORECORD_SERVER_ID = "your_server_id"
RESTORECORD_API_KEY = "your_api_key"  # Optional but recommended

# Server invite link (sent after approval)
SERVER_INVITE_LINK = "https://discord.gg/example"
```

**Alternatively, use environment variables** (more secure):
```bash
export DISCORD_TOKEN="your_token"
export RESTORECORD_URL="https://verify.yourserver.com"
export RESTORECORD_SERVER_ID="your_server_id"
export RESTORECORD_API_KEY="your_api_key"
export SERVER_INVITE_LINK="https://discord.gg/example"
# etc.
```

### 3. (Optional) Configure Message Forwarding

Instead of sending new messages, you can forward pre-existing auth request messages from a "secret server".

In `config.py`:

```python
# Enable message forwarding for auth requests
FORWARD_SOURCE_CHANNEL_ID = "123456789012345678"  # Channel ID in your secret server
FORWARD_AUTH_MESSAGE_ID = "987654321098765432"    # Message ID for auth requests

# Optional: Add extra text along with the forwarded message
FORWARD_AUTH_ADDITIONAL_TEXT = "Please complete verification to join!"
```

**Setting up forwarding:**
1. Create a "secret server" with a channel containing your auth request template message
2. The message should contain the RestoreCord verification link
3. Copy the channel ID and message ID (Right-click → Copy ID with Developer Mode enabled)
4. Configure them in `config.py`
5. The bot will forward this message instead of sending new ones
6. Optionally set additional text to send along with each forward

**Note:** Only auth request messages are forwarded. Success messages are simple text (not forwarded).

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
RestoreCord Enabled: True
Message Forwarding: True (if configured)
============================================================
✅ Auth monitor thread started
Polling for applications...
```

### 5. Manage Pending Auth Requests

```bash
python auth_manager.py
```

Select options:
1. **List Pending Auth Users** - See who's waiting for auth completion
2. **Check User Verification Status** - Check if a user is verified on RestoreCord
3. **View RestoreCord Configuration** - See current RestoreCord settings
4. **Exit**

**Note:** This tool no longer manages authorized users because authorization is checked via RestoreCord API in real-time.

## 📖 How It Works

### For Already Verified Users:
1. User applies to join server
2. Bot checks RestoreCord API: "Is user verified?"
3. ✅ **If YES**: Bot immediately auto-approves WITHOUT opening interview channel or sending messages
   - This is silent and instant - user just gets accepted

### For Non-Verified Users:
1. User applies to join server
2. Bot checks RestoreCord API: "Is user verified?"
3. ⏳ **If NO**: Opens interview channel → Forwards/sends auth request with RestoreCord link → Adds to pending list
4. User clicks RestoreCord link and completes verification
5. Bot monitors RestoreCord API (checks every 2 seconds)
6. Bot detects user is now verified
7. ✅ Bot approves application → Sends success message with server invite link

### With Message Forwarding:
- Instead of sending new auth request messages, the bot forwards a pre-configured message from your secret server
- The forwarded message should contain the RestoreCord verification link
- Optionally adds custom text along with the forward (e.g., "Complete verification to join!")
- Success messages are simple text (NOT forwarded)

## 🔧 Configuration

**All configuration is centralized in `config.py`** - edit this one file to configure everything!

### Core Settings (in `config.py`)

```python
# Discord credentials
TOKEN = ""                    # Your Discord user token
GUILD_ID = ""                 # Your server/guild ID
OWN_USER_ID = ""              # Your Discord user ID

# RestoreCord configuration (REQUIRED)
RESTORECORD_URL = ""          # Your RestoreCord instance URL
RESTORECORD_SERVER_ID = ""    # Your server ID on RestoreCord
RESTORECORD_API_KEY = ""      # Optional API key

# Server invite link (sent after approval)
SERVER_INVITE_LINK = ""       # e.g., "https://discord.gg/example"

# Message forwarding (optional)
FORWARD_SOURCE_CHANNEL_ID = ""  # Secret server channel
FORWARD_AUTH_MESSAGE_ID = ""    # Auth request message
FORWARD_AUTH_ADDITIONAL_TEXT = ""  # Extra text with auth forward

# Timing
CHANNEL_CREATION_WAIT = 2     # Wait for Discord to create channel
AUTH_CHECK_INTERVAL = 2       # How often to check for new verifications (seconds)
```

### Environment Variables

For better security, use environment variables (config.py will automatically load these):

```bash
export DISCORD_TOKEN="your_token"
export RESTORECORD_URL="https://verify.yourserver.com"
export RESTORECORD_SERVER_ID="your_server_id"
export RESTORECORD_API_KEY="your_api_key"
export SERVER_INVITE_LINK="https://discord.gg/example"
export FORWARD_SOURCE_CHANNEL_ID="channel_id"
export FORWARD_AUTH_MESSAGE_ID="message_id"
export FORWARD_AUTH_ADDITIONAL_TEXT="Complete verification!"
```

## 📱 Usage Examples

### Example 1: Already Verified User

```
User "John" (ID: 123456789) applies
→ Bot checks RestoreCord API
→ John IS verified on RestoreCord
→ Bot immediately approves (NO interview channel, NO messages)
→ ✅ John is now in the server (silent approval)
```

### Example 2: New User Needs Verification

```
User "Jane" (ID: 987654321) applies
→ Bot checks RestoreCord API
→ Jane is NOT verified
→ Bot opens interview channel
→ Bot forwards/sends auth request: "🔐 Verify on RestoreCord: [link]"
→ Jane clicks link and completes RestoreCord verification
→ Bot detects Jane is verified (within 2 seconds)
→ Bot approves application
→ Bot sends: "✅ Authentication successful! Make sure to join VC https://discord.gg/example"
→ ✅ Jane is now in the server
```

## 🛠️ CLI Management Tool

The `auth_manager.py` provides an interface for viewing pending auth requests:

```bash
$ python auth_manager.py

=================================================================
               Auth Manager CLI
=================================================================

1. List Pending Auth Users
2. Check User Verification Status (RestoreCord)
3. View RestoreCord Configuration
4. Exit

Select an option (1-4):
```

### Key Functions

1. **List Pending Auth Users** - View all users waiting for verification completion
2. **Check User Verification Status** - Check if a specific user is verified on RestoreCord
3. **View RestoreCord Configuration** - See current RestoreCord settings

**Note:** Authorization is now handled entirely via RestoreCord API. There is no local authorized users list to manage.

## 🔒 RestoreCord Integration

RestoreCord is a verification system for Discord servers. The bot automatically checks user verification via RestoreCord API in real-time.

### Setup:

1. Set `RESTORECORD_URL` to your RestoreCord instance URL
2. Set `RESTORECORD_SERVER_ID` to your server ID
3. (Optional) Set `RESTORECORD_API_KEY` for API access
4. Users who verify on RestoreCord are automatically authorized

### How it works:

- When a user applies, bot checks RestoreCord API in real-time
- If verified, user is auto-approved immediately (no interview channel)
- If not verified, user gets auth request with RestoreCord link
- Bot polls API every 2 seconds to detect when verification completes
- No local storage - always checks the authoritative RestoreCord API

## 📁 File Structure

```
.
├── config.py                # 🔧 Central configuration file (EDIT THIS!)
├── auth_handler.py          # Core authentication system (RestoreCord API)
├── meow_with_auth.py        # Bot with auth integration
├── auth_manager.py          # CLI tool for viewing pending auth
├── requirements.txt         # Python dependencies
├── README.md                # This file
├── HOW_IT_WORKS.md          # Detailed explanation
├── .gitignore               # Git ignore rules
│
└── pending_auth.json        # Pending auth requests (auto-created)
```

**Important:** 
- All configuration is done in `config.py` - this one file controls everything!
- No `authorized_users.json` file - authorization is via RestoreCord API
- Only `pending_auth.json` is used to track users waiting for verification

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
- Verify `FORWARD_AUTH_MESSAGE_ID` exists in that channel
- Make sure the bot/user has access to the source channel

**Test manually:**
- Try sending a message to the channel first
- Verify the channel is accessible
- Check Discord API errors in logs

**Note:** Only auth request messages are forwarded. Success messages are simple text.

## 🔐 Security Best Practices

1. **Never commit tokens**: Already configured in `.gitignore`
2. **Use environment variables**: More secure than hardcoding
3. **Protect auth files**: Keep `authorized_users.json` secure
4. **Regular backups**: Export authorized users regularly
5. **Review auth requests**: Don't blindly approve everyone
6. **Secure your secret server**: Only trusted users should access it

## 📊 Performance

- **Auth check interval**: 2 seconds (configurable)
- **Auto-approve time**: 2-3 seconds after RestoreCord verification
- **RestoreCord check**: Real-time via API on each application
- **Message forwarding**: Same speed as regular sending
- **Already verified users**: Instant approval (no interview channel)

## 🎯 Advanced Usage

### Custom Messages

Edit messages in `config.py`:

```python
# Post-acceptance message with server invite
if SERVER_INVITE_LINK:
    AUTH_SUCCESS_MESSAGE = (
        f"✅ **Authentication successful!** Make sure to join VC {SERVER_INVITE_LINK}"
    )
```

Or edit `auth_handler.py` for full customization:

```python
AUTH_REQUEST_MESSAGE = """
🔐 **Custom Auth Message**

Your custom instructions here...

**Link:** {AUTH_LINK}
"""
```

### Toggle Auth On/Off

In `meow_with_auth.py`:

```python
USE_AUTH_HANDLER = True   # Auth enabled
USE_AUTH_HANDLER = False  # Auth disabled (regular meow.py behavior)
```

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
- [ ] Configure RestoreCord in `config.py` (REQUIRED: URL and SERVER_ID)
- [ ] Set SERVER_INVITE_LINK in `config.py` (optional but recommended)
- [ ] (Optional) Configure message forwarding in `config.py`
- [ ] (Optional) Set additional text for forwards in `config.py`
- [ ] Start the bot (`python meow_with_auth.py`)
- [ ] Test with your own user ID
- [ ] Monitor logs and adjust settings in `config.py`

---

**Happy auto-accepting! 🚀**
