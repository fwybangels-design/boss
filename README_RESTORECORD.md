# RestoreCord Integration - Complete Guide

## 🎯 Quick Answer

**Q:** What RestoreCord API permissions do I need?

**A:** Just ONE:
- ✅ **Read everything (data access)** - To see who's verified

**Don't need:**
- ❌ Pull members (bot handles adding users)
- ❌ Server operations, bots, analytics, account

---

## 📝 Setup (3 Steps)

### Step 1: Get API Key

1. Go to RestoreCord dashboard
2. Settings → API → Create New Key
3. Enable: **Read everything (data access)**
4. Copy the key: `rc_xxxxxxxxxxxxx`

### Step 2: Configure

Open `/home/runner/work/boss/boss/auth_handler.py`

Find line 67 and change:

```python
RESTORECORD_URL = "https://your-restorecord.com"
RESTORECORD_API_KEY = "rc_your_key_here"
RESTORECORD_SERVER_ID = "your_discord_server_id"
```

### Step 3: Test & Run

```bash
python3 test_restorecord.py  # Test configuration
python3 meow_with_auth.py     # Start the bot
```

---

## 🔄 How It Works

### For Verified Users

```
User applies
    ↓
Bot checks RestoreCord
    ↓
User IS verified
    ↓
Bot auto-accepts ✅
```

### For Unverified Users

```
User applies
    ↓
Bot checks RestoreCord
    ↓
User NOT verified
    ↓
Bot opens group chat
    ↓
Bot sends verification link
    ↓
User verifies on RestoreCord
    ↓
Bot checks again
    ↓
User now verified
    ↓
Bot auto-accepts ✅
```

---

## 👥 Division of Responsibilities

### 🤖 The Bot Handles:
- Opening group chat with applicant
- Sending verification link message
- Checking RestoreCord API for verification status
- Approving Discord applications
- Adding users to Discord server
- All Discord operations

### 🔐 RestoreCord Provides:
- Verification system/website
- Read-only API to check who's verified
- Verification link for users
- User verification data

**Simple:** Bot does all Discord work, RestoreCord just tells who's verified!

---

## 📚 Documentation

- **SETUP_SUMMARY.txt** - Quick reference
- **RESTORECORD_QUICKSTART.md** - Step-by-step setup
- **RESTORECORD_API_SETUP.md** - Detailed API info
- **RESTORECORD_CONFIG.md** - Complete configuration
- **test_restorecord.py** - Configuration tester

---

## 🧪 Testing

Run the test script:

```bash
python3 test_restorecord.py
```

Expected output:
```
✅ RestoreCord is configured!
✅ RestoreCord Verification
```

---

## 🔧 Configuration Example

```python
# In auth_handler.py (lines 67-69)

RESTORECORD_URL = "https://verify.myserver.com"
RESTORECORD_API_KEY = "rc_abc123xyz789"
RESTORECORD_SERVER_ID = "1464067001256509452"
```

---

## 💡 What Happens in Practice

### Scenario 1: Verified User Applies

```
[User123 applies to join]
Bot: Checking RestoreCord...
RestoreCord API: User123 is verified ✅
Bot: Auto-accepting application!
Bot: Adding user to Discord server
[User123 joins server]
```

### Scenario 2: Unverified User Applies

```
[User456 applies to join]
Bot: Checking RestoreCord...
RestoreCord API: User456 NOT verified ❌
Bot: Opening group chat with User456
Bot: "Please verify: https://verify.myserver.com"
[User456 clicks link and verifies]
[5 seconds later...]
Bot: Checking RestoreCord again...
RestoreCord API: User456 is NOW verified ✅
Bot: Auto-accepting application!
Bot: Adding user to Discord server
[User456 joins server]
```

---

## ⚙️ API Calls Made

The bot makes these RestoreCord API calls:

### Check Single User
```
GET {RESTORECORD_URL}/api/check
?server={SERVER_ID}&user={USER_ID}

Response: {"verified": true}
```

### Get All Verified Users (Optional)
```
GET {RESTORECORD_URL}/api/members
?server={SERVER_ID}

Response: [{"user_id": "123", "verified": true}, ...]
```

**Note:** Only read operations, no write/pull operations!

---

## ❓ FAQ

**Q: Do I need "Pull members" permission?**  
A: No! The bot handles adding users to Discord. RestoreCord only tells who's verified.

**Q: What if my RestoreCord uses a different API?**  
A: The code handles multiple API response formats. Check logs if issues occur.

**Q: Can I use Discord OAuth2 instead?**  
A: Yes! Set `BOT_CLIENT_ID` instead of RestoreCord settings.

**Q: Does this work with the original meow.py?**  
A: Use `meow_with_auth.py` which integrates auth checking with meow.py logic.

**Q: How often does the bot check verification?**  
A: Every 5 seconds for pending applications (configurable via `AUTH_CHECK_INTERVAL`).

---

## 🔐 Security

✅ **Best Practices:**
- Store API key in environment variables
- Never commit API key to git
- Use minimal permissions (read-only)
- Keep RESTORECORD_API_KEY secret
- Rotate keys periodically

❌ **Don't:**
- Share API key publicly
- Commit to GitHub
- Give more permissions than needed
- Use in client-side code

---

## 🚀 Quick Start Checklist

- [ ] Get RestoreCord API key with "Read everything" permission
- [ ] Copy your RestoreCord URL
- [ ] Get your Discord server ID
- [ ] Edit `auth_handler.py` lines 67-69
- [ ] Run `python3 test_restorecord.py`
- [ ] Run `python3 meow_with_auth.py`
- [ ] Test with a user application
- [ ] Verify auto-accept works

---

## 📞 Support

**Having issues?**
1. Run `python3 test_restorecord.py`
2. Check bot logs for errors
3. Verify API key has correct permission
4. Check RestoreCord URL is accessible
5. Confirm server ID is correct

**Still need help?**
- Review RESTORECORD_API_SETUP.md
- Check SETUP_SUMMARY.txt
- Test API with curl/Postman
- Review bot logs

---

## ✅ Summary

You need:
- RestoreCord API key with **Read everything** permission
- 3 lines of configuration
- That's it!

The bot does all Discord work (GC, approval, adding users).  
RestoreCord just provides verification status (read-only).

Simple, clean, and works! 🎉
