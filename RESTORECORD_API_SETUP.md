# RestoreCord API Key Setup Guide

## 🎯 Quick Answer: Which API Permissions Do You Need?

For the auth handler to work, you need:

### ✅ REQUIRED Permissions:
- **members** - To check if users are verified and get list of verified members

### ✅ RECOMMENDED (Optional):
- **servers** - To verify server info (helps with validation)

### ❌ NOT NEEDED:
- ~~account~~ - Not needed
- ~~bots~~ - Not needed
- ~~analytics~~ - Not needed
- ~~server operations~~ - Not needed (no backups/firewall required)

---

## 📋 Step-by-Step Setup

### Step 1: Get Your RestoreCord API Key

1. Log into your RestoreCord dashboard
2. Go to **Settings** → **API** or **Developers**
3. Click **Create New API Key** or **Generate Key**
4. Select these permissions:
   - ✅ **members** (required)
   - ✅ **servers** (recommended)
5. Click **Generate** or **Create**
6. Copy the API key (you'll only see it once!)

**Example API key format:**
```
rc_1a2b3c4d5e6f7g8h9i0j
```

### Step 2: Configure in auth_handler.py

Open `/home/runner/work/boss/boss/auth_handler.py` and set:

```python
# RestoreCord Configuration
RESTORECORD_URL = "https://your-restorecord-instance.com"  # Your RestoreCord URL
RESTORECORD_API_KEY = "rc_1a2b3c4d5e6f7g8h9i0j"  # Your API key from Step 1
RESTORECORD_SERVER_ID = "1464067001256509452"  # Your Discord server ID
```

**OR** use environment variables (more secure):

```bash
export RESTORECORD_URL="https://your-restorecord-instance.com"
export RESTORECORD_API_KEY="rc_1a2b3c4d5e6f7g8h9i0j"
export RESTORECORD_SERVER_ID="1464067001256509452"
```

### Step 3: Test Your Configuration

Run the test script:

```bash
python3 test_restorecord.py
```

You should see:
```
✅ RestoreCord is configured!
✅ RestoreCord Verification
```

---

## 🔍 What Each Permission Does

### Members Permission (REQUIRED)

**What it does:**
- Allows checking if a specific user is verified: `GET /api/check?user={user_id}`
- Allows getting list of all verified users: `GET /api/members?server={server_id}`

**Why we need it:**
- To check if users are verified when they apply
- To auto-accept verified users
- To sync verified users to local cache

**API calls used:**
```python
# Check single user
GET /api/check?server={server_id}&user={user_id}
Response: {"verified": true}

# Get all verified users
GET /api/members?server={server_id}
Response: [{"user_id": "123", "verified": true}, ...]
```

### Servers Permission (RECOMMENDED)

**What it does:**
- Allows getting server information: `GET /api/servers/{server_id}`
- Validates that the server exists in RestoreCord

**Why it's helpful:**
- Validates your configuration at startup
- Provides better error messages
- Can check server status

**API calls used:**
```python
GET /api/servers/{server_id}
Response: {"id": "123", "name": "My Server", "verified_count": 42}
```

### Permissions You DON'T Need

❌ **account** - Only needed for managing your RestoreCord account settings  
❌ **bots** - Only needed for RestoreCord bot management  
❌ **analytics** - Only needed for viewing statistics dashboard  
❌ **server operations** - Only needed for:
  - Creating/restoring backups
  - Pulling members to other servers
  - Managing firewall rules

**None of these are needed for just checking member verification!**

---

## 📝 Configuration Examples

### Example 1: Self-Hosted RestoreCord

```python
# auth_handler.py

RESTORECORD_URL = "https://verify.myserver.com"
RESTORECORD_API_KEY = "rc_a1b2c3d4e5f6g7h8"  # members + servers permission
RESTORECORD_SERVER_ID = "1464067001256509452"
```

### Example 2: RestoreCord.com Service

```python
# auth_handler.py

RESTORECORD_URL = "https://restorecord.com"
RESTORECORD_API_KEY = "rc_prod_9x8y7z6w5v4u3t2s"  # members permission only
RESTORECORD_SERVER_ID = "1464067001256509452"
```

### Example 3: Using Environment Variables

```bash
# .env file or export commands
export RESTORECORD_URL="https://api.restorecord.com"
export RESTORECORD_API_KEY="rc_1234567890abcdefghij"
export RESTORECORD_SERVER_ID="1464067001256509452"
```

Then in your terminal:
```bash
source .env
python3 meow_with_auth.py
```

---

## 🧪 Testing Your API Key

### Quick Test Script

Create `test_api_key.py`:

```python
import requests

# Your settings
RESTORECORD_URL = "https://your-instance.com"
RESTORECORD_API_KEY = "your_api_key_here"
RESTORECORD_SERVER_ID = "your_server_id"

# Test API connection
headers = {"Authorization": f"Bearer {RESTORECORD_API_KEY}"}

# Test 1: Check server info (if servers permission enabled)
print("Testing server info...")
resp = requests.get(
    f"{RESTORECORD_URL}/api/servers/{RESTORECORD_SERVER_ID}",
    headers=headers
)
print(f"Status: {resp.status_code}")
if resp.status_code == 200:
    print(f"✅ Server info: {resp.json()}")
else:
    print(f"❌ Error: {resp.text}")

# Test 2: Check members (requires members permission)
print("\nTesting members endpoint...")
resp = requests.get(
    f"{RESTORECORD_URL}/api/members?server={RESTORECORD_SERVER_ID}",
    headers=headers
)
print(f"Status: {resp.status_code}")
if resp.status_code == 200:
    members = resp.json()
    print(f"✅ Found {len(members)} verified members")
else:
    print(f"❌ Error: {resp.text}")
```

Run it:
```bash
python3 test_api_key.py
```

---

## ❓ Troubleshooting

### Error: "403 Forbidden" or "Insufficient permissions"

**Problem:** Your API key doesn't have the required permissions

**Solution:**
1. Go back to RestoreCord dashboard
2. Edit your API key
3. Make sure **members** permission is enabled
4. Regenerate key if needed
5. Update `RESTORECORD_API_KEY` with new key

### Error: "401 Unauthorized"

**Problem:** Invalid or expired API key

**Solution:**
1. Check that you copied the full API key
2. Make sure there are no extra spaces
3. Key might be expired - generate a new one
4. Update `RESTORECORD_API_KEY`

### Error: "404 Not Found"

**Problem:** Wrong API endpoint or server ID

**Solution:**
1. Verify `RESTORECORD_URL` is correct
2. Check that `RESTORECORD_SERVER_ID` matches your Discord server
3. Try different endpoint variations:
   - `/api/members`
   - `/api/v1/members`
   - `/verify/members`

### No users showing as verified

**Problem:** No data in RestoreCord yet

**Solution:**
1. Make sure users have verified on RestoreCord first
2. Check RestoreCord dashboard to see verified users
3. Try syncing: Call `sync_restorecord_users()` function
4. Verify the server ID matches

---

## 🔐 Security Best Practices

### ✅ DO:
- Store API key in environment variables
- Keep API key secret (don't commit to git)
- Use minimal required permissions (just members)
- Rotate keys periodically
- Use HTTPS for API calls

### ❌ DON'T:
- Commit API key to GitHub
- Share API key publicly
- Give more permissions than needed
- Use API key in client-side code
- Leave old keys active after rotating

---

## 🚀 Quick Start Checklist

- [ ] Get RestoreCord API key with **members** permission
- [ ] Copy your RestoreCord instance URL
- [ ] Get your Discord server ID
- [ ] Open `auth_handler.py`
- [ ] Set `RESTORECORD_URL`
- [ ] Set `RESTORECORD_API_KEY`
- [ ] Set `RESTORECORD_SERVER_ID`
- [ ] Run `python3 test_restorecord.py` to verify
- [ ] Start bot: `python3 meow_with_auth.py`
- [ ] Test with a user application

---

## 📞 Need Help?

**RestoreCord API not working?**
1. Check your API key has **members** permission
2. Verify the URL and server ID are correct
3. Test with the test script above
4. Check RestoreCord dashboard for verified users
5. Review bot logs for specific error messages

**Still having issues?**
- Check RestoreCord documentation for your specific instance
- Review `RESTORECORD_CONFIG.md` for detailed setup
- Test API endpoints with `curl` or Postman
- Verify server ID in Discord (right-click server → Copy ID)
