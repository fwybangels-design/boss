# Quick Start Guide - Auth Handler

## 🚀 Get Started in 5 Minutes

### Step 1: Configure Your Token

Open `auth_handler.py` and add your Discord token:

```python
TOKEN = "your_discord_user_token_here"
```

Or use environment variable:
```bash
export DISCORD_TOKEN="your_token"
```

### Step 2: Set Your Auth Link

In `auth_handler.py`, set the link users need to click:

```python
AUTH_LINK = "https://t.me/addlist/your_telegram_group"
# Or your RestoreCord URL
```

### Step 3: Start the Bot

```bash
python meow_with_auth.py
```

You should see:
```
============================================================
Discord Application Bot Started (with Auth Handler)
============================================================
Auth Handler Enabled: True
============================================================
✅ Auth monitor thread started
Polling for applications...
```

### Step 4: Add Authorized Users

Open a new terminal and run:

```bash
python auth_manager.py
```

Select option **3** (Authorize a User), then enter the Discord user ID.

That's it! The bot is now running with auth checking.

## 📋 Common Tasks

### Check Who's Authorized

```bash
python auth_manager.py
# Select option 1
```

### Add Multiple Users at Once

1. Create a file `users.txt`:
   ```
   123456789012345678
   987654321098765432
   111222333444555666
   ```

2. Run auth_manager:
   ```bash
   python auth_manager.py
   # Select option 5
   # Enter: users.txt
   ```

### Export Authorized Users (Backup)

```bash
python auth_manager.py
# Select option 6
# Enter filename or press Enter for default
```

### Remove a User

```bash
python auth_manager.py
# Select option 4
# Enter user ID to remove
```

## 🔄 How It Works

### For Authorized Users:
1. User applies → Bot checks list → Already authorized → ✅ **Auto-accepts immediately**

### For New Users:
1. User applies → Bot checks list → NOT authorized → Opens chat
2. Bot sends: "🔐 Click this auth link: [link]"
3. User clicks link and completes auth
4. You add them with `auth_manager.py`
5. Bot detects → ✅ **Auto-accepts automatically**

## 📱 Example Workflow

**Scenario 1: Pre-Authorized User**
```
User "John" (ID: 123456789) applies
Bot checks → Found in auth list
Bot sends: "✅ Welcome! Auto-accepted."
Application approved ✅
```

**Scenario 2: New User**
```
User "Jane" (ID: 987654321) applies
Bot checks → NOT in auth list
Bot sends: "🔐 Please authenticate: [link]"
Jane clicks link and joins Telegram
Admin runs: python auth_manager.py → Add Jane
Bot detects Jane is now authorized
Bot sends: "✅ Authentication successful!"
Application approved ✅
```

## 🛠️ Configuration Options

### Toggle Auth Handler On/Off

Edit `meow_with_auth.py`:
```python
USE_AUTH_HANDLER = True   # Use auth system
USE_AUTH_HANDLER = False  # Use original meow.py behavior
```

### Change Auth Check Interval

Edit `auth_handler.py`:
```python
AUTH_CHECK_INTERVAL = 5  # Check every 5 seconds (default)
AUTH_CHECK_INTERVAL = 10 # Check every 10 seconds (slower)
AUTH_CHECK_INTERVAL = 2  # Check every 2 seconds (faster)
```

### Customize Messages

Edit `auth_handler.py`:
```python
AUTH_REQUEST_MESSAGE = "Your custom message here..."
AUTO_ACCEPT_MESSAGE = "Your welcome message here..."
```

## 📚 Documentation

- **Full Documentation**: See `AUTH_HANDLER_README.md`
- **Technical Details**: See `IMPLEMENTATION_SUMMARY.md`
- **System Diagrams**: See `SYSTEM_FLOW_DIAGRAM.md`
- **Code Examples**: Run `python example_auth_usage.py`
- **Tests**: Run `python test_auth_handler.py`

## ❓ Troubleshooting

### Bot Not Starting
- Check that TOKEN is set correctly
- Verify token is valid (not expired/revoked)
- Run: `python meow_with_auth.py` and check error messages

### Users Not Auto-Accepting
- Check if user is in authorized list: `python auth_manager.py` → option 1
- Check logs for error messages
- Verify AUTH_CHECK_INTERVAL isn't too long

### "Invalid Token" Error
- Your Discord token is wrong or expired
- Get a new token from Discord
- Update TOKEN in `auth_handler.py`

## 💡 Tips

1. **Add test user first**: Add your own Discord ID to test the system
2. **Use environment variables**: More secure than hardcoding token
3. **Regular backups**: Use option 6 in auth_manager to export regularly
4. **Monitor logs**: Watch console output for issues
5. **Start small**: Test with a few users before scaling up

## 🔒 Security

- ✅ Never commit tokens to Git (already in .gitignore)
- ✅ Use environment variables for production
- ✅ Keep `authorized_users.json` secure
- ✅ Regular backups of authorized list
- ✅ Review auth requests before adding users

## 🆘 Getting Help

1. Check logs for error messages
2. Review documentation in `AUTH_HANDLER_README.md`
3. Run tests: `python test_auth_handler.py`
4. Check system diagrams: `SYSTEM_FLOW_DIAGRAM.md`

## 🎯 Next Steps

After getting started:

1. **Customize messages** to match your server's style
2. **Set up automation** for adding users (webhook, API, etc.)
3. **Consider RestoreCord integration** for verified users
4. **Create regular backups** of authorized users
5. **Monitor performance** and adjust check intervals

---

## Quick Command Reference

```bash
# Start bot
python meow_with_auth.py

# Manage users (interactive)
python auth_manager.py

# Test system
python test_auth_handler.py

# See examples
python example_auth_usage.py
```

## File Locations

```
auth_handler.py          - Core system
meow_with_auth.py        - Bot with auth
auth_manager.py          - CLI management tool
authorized_users.json    - User whitelist (auto-created)
pending_auth.json        - Pending users (auto-created)
```

Happy auto-accepting! 🎉
