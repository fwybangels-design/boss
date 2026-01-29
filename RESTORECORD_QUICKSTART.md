# 🎯 RestoreCord Quick Setup - Copy & Paste Guide

## Where to Put Your Settings

Open the file: `/home/runner/work/boss/boss/auth_handler.py`

Look for this section (around line 60-70):

```python
# ---------------------------
# RestoreCord Configuration
# ---------------------------
```

## ✏️ What to Change

### Find These Lines:

```python
RESTORECORD_URL = ""  # e.g., "https://verify.yourserver.com"
RESTORECORD_API_KEY = ""  # Your RestoreCord API key (if required)
RESTORECORD_SERVER_ID = ""  # Your RestoreCord server/guild ID
```

### Replace With Your Info:

```python
RESTORECORD_URL = "https://your-restorecord-instance.com"  # ← Your RestoreCord URL here
RESTORECORD_API_KEY = "rc_your_api_key_here"  # ← Your API key here (members permission)
RESTORECORD_SERVER_ID = "1464067001256509452"  # ← Your Discord server ID here
```

## 📋 Getting Your Values

### 1. RestoreCord URL

This is where your RestoreCord is hosted:
- **Self-hosted**: `https://verify.yourserver.com`
- **Shared service**: `https://restorecord.com` or whatever URL you use

### 2. RestoreCord API Key

1. Go to RestoreCord dashboard
2. Navigate to **Settings** → **API**
3. Click **Create New Key**
4. Select **members** permission ✅
5. (Optional) Select **servers** permission ✅
6. Copy the generated key

**Example:** `rc_1a2b3c4d5e6f7g8h9i0j`

### 3. Discord Server ID

1. Open Discord
2. Enable Developer Mode: **Settings** → **Advanced** → **Developer Mode ON**
3. Right-click your server icon (in server list)
4. Click **Copy ID**

**Example:** `1464067001256509452`

## ✅ Complete Example

Here's what it should look like when done:

```python
# ---------------------------
# RestoreCord Configuration
# ---------------------------
RESTORECORD_URL = "https://verify.myserver.com"
RESTORECORD_API_KEY = "rc_9x8y7z6w5v4u3t2s1r0q"
RESTORECORD_SERVER_ID = "1464067001256509452"
```

## 🧪 Test It

After setting these values, run:

```bash
python3 test_restorecord.py
```

You should see:
```
✅ RestoreCord is configured!
✅ RestoreCord Verification
```

## 🚀 Start the Bot

Once configured and tested:

```bash
python3 meow_with_auth.py
```

The bot will now:
- Check RestoreCord for verified users
- Auto-accept verified users immediately
- Send RestoreCord link to unverified users
- Auto-accept once they verify

## 🎬 Full Example Start to Finish

### Before (auth_handler.py):
```python
RESTORECORD_URL = ""
RESTORECORD_API_KEY = ""
RESTORECORD_SERVER_ID = ""
```

### After (auth_handler.py):
```python
RESTORECORD_URL = "https://verify.mycommunity.com"
RESTORECORD_API_KEY = "rc_abc123xyz789"
RESTORECORD_SERVER_ID = "987654321012345678"
```

### Then run:
```bash
# Test configuration
python3 test_restorecord.py

# If OK, start bot
python3 meow_with_auth.py
```

## 💡 Pro Tips

1. **Use environment variables** for better security:
   ```bash
   export RESTORECORD_URL="https://verify.mycommunity.com"
   export RESTORECORD_API_KEY="rc_abc123xyz789"
   export RESTORECORD_SERVER_ID="987654321012345678"
   python3 meow_with_auth.py
   ```

2. **Test with your own user ID** first to make sure it works

3. **Keep API key secret** - don't share or commit to git

## ❓ Common Issues

### "RestoreCord is not configured"
→ Make sure all 3 values are set (URL, API Key, Server ID)

### "403 Forbidden"
→ API key doesn't have **members** permission - regenerate with correct permission

### "404 Not Found"
→ Check your RestoreCord URL is correct

### "User not verified"
→ Make sure the user has actually verified on RestoreCord first

## 📚 More Help

- **Detailed guide**: See `RESTORECORD_API_SETUP.md`
- **Full config guide**: See `RESTORECORD_CONFIG.md`
- **Test your setup**: Run `python3 test_restorecord.py`

---

**That's it!** Just 3 lines to change and you're ready to go! 🎉
