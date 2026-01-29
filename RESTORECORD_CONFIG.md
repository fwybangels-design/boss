# RestoreCord Configuration Guide

## What is RestoreCord?

RestoreCord is a Discord server verification system that helps maintain safe communities by verifying members. This auth handler can integrate with RestoreCord to automatically authorize users who have been verified on RestoreCord.

## Configuration Options

You have **3 ways** to configure RestoreCord:

### Option 1: Direct Configuration in auth_handler.py (Easiest)

Open `auth_handler.py` and set these values:

```python
RESTORECORD_URL = "https://verify.yourserver.com"  # Your RestoreCord instance URL
RESTORECORD_API_KEY = "your_api_key_here"  # Your API key (if required)
RESTORECORD_SERVER_ID = "1464067001256509452"  # Your Discord server ID
```

### Option 2: Environment Variables (Most Secure)

Set these environment variables:

```bash
export RESTORECORD_URL="https://verify.yourserver.com"
export RESTORECORD_API_KEY="your_api_key_here"
export RESTORECORD_SERVER_ID="1464067001256509452"
```

### Option 3: Use Discord OAuth2 Bot (Alternative)

If you don't want to use RestoreCord, you can use Discord's native OAuth2:

```python
BOT_CLIENT_ID = "your_discord_bot_client_id"
REDIRECT_URI = "https://discord.com/oauth2/authorized"
```

## Finding Your RestoreCord Settings

### 1. RestoreCord Instance URL

This is the base URL of your RestoreCord installation:
- **Self-hosted**: `https://verify.yourserver.com` or `https://yourdomain.com/verify`
- **Official RestoreCord**: Check with the RestoreCord service provider
- **Example**: `https://restorecord.com`

### 2. RestoreCord API Key

**Where to find it:**
1. Log into your RestoreCord dashboard
2. Go to **Settings** → **API** or **Developers**
3. Look for "API Key" or "Authorization Token"
4. Copy the key

**Format:** Usually looks like:
- `rc_1234567890abcdef` (RestoreCord format)
- `Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...` (JWT token)
- Or just a random string like `a1b2c3d4e5f6`

**Not all RestoreCord instances require an API key** - if yours doesn't, leave it blank.

### 3. RestoreCord Server ID

This is your Discord server (guild) ID:
1. Enable Developer Mode in Discord: **Settings** → **Advanced** → **Developer Mode**
2. Right-click your server icon
3. Click **Copy ID**
4. Paste this as `RESTORECORD_SERVER_ID`

## How RestoreCord Integration Works

### Flow Diagram

```
User applies to server
         │
         ▼
    Check local auth list
         │
         ├─ Found? → Auto-accept ✅
         │
         └─ Not found?
                │
                ▼
    Check RestoreCord API
                │
                ├─ Verified? → Auto-add & Auto-accept ✅
                │
                └─ Not verified?
                        │
                        ▼
                Send verification link
                        │
                        ▼
                User verifies on RestoreCord
                        │
                        ▼
                Monitor detects verification
                        │
                        ▼
                Auto-accept ✅
```

### What Happens

1. **User applies** to your Discord server
2. **Bot checks** local authorized users list
3. If not found, **bot checks RestoreCord** API
4. If verified on RestoreCord → **Auto-accept immediately**
5. If not verified → **Send RestoreCord verification link**
6. User completes verification on RestoreCord
7. **Monitor detects** and auto-accepts

## RestoreCord API Endpoints

The integration uses these common RestoreCord API endpoints:

### Check Single User Verification

```
GET {RESTORECORD_URL}/api/check?server={SERVER_ID}&user={USER_ID}
```

**Response examples:**
```json
// Pattern 1
{"verified": true}

// Pattern 2
{"status": "verified"}

// Pattern 3
{"member": {"user_id": "123", "verified": true}}
```

### Get All Verified Users (Bulk Sync)

```
GET {RESTORECORD_URL}/api/members?server={SERVER_ID}
```

**Response examples:**
```json
// Pattern 1
[
  {"user_id": "123456789", "verified": true},
  {"user_id": "987654321", "verified": true}
]

// Pattern 2
{
  "members": [
    {"id": "123456789"},
    {"id": "987654321"}
  ]
}
```

## Configuration Examples

### Example 1: Self-Hosted RestoreCord

```python
# auth_handler.py
RESTORECORD_URL = "https://verify.myserver.com"
RESTORECORD_API_KEY = "rc_a1b2c3d4e5f6g7h8"
RESTORECORD_SERVER_ID = "1464067001256509452"
```

### Example 2: Official RestoreCord Service

```python
# auth_handler.py
RESTORECORD_URL = "https://restorecord.com/verify"
RESTORECORD_API_KEY = ""  # Not required for public instance
RESTORECORD_SERVER_ID = "1464067001256509452"
```

### Example 3: Custom RestoreCord Instance with JWT

```python
# auth_handler.py
RESTORECORD_URL = "https://api.myserver.com/verification"
RESTORECORD_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"
RESTORECORD_SERVER_ID = "1464067001256509452"
```

## Testing Your Configuration

### Test Script

Create `test_restorecord.py`:

```python
from auth_handler import check_restorecord_verification, USE_RESTORECORD

if USE_RESTORECORD:
    print("✅ RestoreCord is configured")
    
    # Test with your user ID
    test_user_id = "YOUR_USER_ID_HERE"
    is_verified = check_restorecord_verification(test_user_id)
    
    if is_verified:
        print(f"✅ User {test_user_id} is verified on RestoreCord")
    else:
        print(f"❌ User {test_user_id} is NOT verified on RestoreCord")
else:
    print("❌ RestoreCord is NOT configured")
    print("Set RESTORECORD_URL and RESTORECORD_SERVER_ID")
```

Run it:
```bash
python test_restorecord.py
```

## Troubleshooting

### Issue: "RestoreCord is not configured"

**Solution:** Make sure both `RESTORECORD_URL` and `RESTORECORD_SERVER_ID` are set.

### Issue: API returns 401 Unauthorized

**Solution:** 
- Your RestoreCord instance requires an API key
- Set `RESTORECORD_API_KEY` with the correct key
- Check that the key hasn't expired

### Issue: API returns 404 Not Found

**Solution:**
- The API endpoint might be different for your RestoreCord instance
- Try these variations:
  - `/api/check`
  - `/api/verified`
  - `/api/v1/check`
  - `/verify/check`

### Issue: Users not auto-verifying

**Solution:**
1. Check RestoreCord API is responding: `curl {RESTORECORD_URL}/api/check?server={SERVER_ID}&user={USER_ID}`
2. Check logs for API errors
3. Verify `RESTORECORD_SERVER_ID` matches your Discord server
4. Make sure the monitor thread is running

### Issue: Different API Response Format

**Solution:** The code handles multiple response formats, but if yours is different:

1. Check the actual response:
   ```python
   import requests
   resp = requests.get(f"{RESTORECORD_URL}/api/check?server={SERVER_ID}&user={USER_ID}")
   print(resp.json())
   ```

2. Update `check_restorecord_verification()` in `auth_handler.py` to handle your format

## No RestoreCord? Use Discord OAuth2

If you don't have RestoreCord, use Discord's native OAuth2 bot authorization:

```python
# auth_handler.py
BOT_CLIENT_ID = "your_discord_application_client_id"
REDIRECT_URI = "https://discord.com/oauth2/authorized"

# Leave RestoreCord settings empty
RESTORECORD_URL = ""
RESTORECORD_API_KEY = ""
RESTORECORD_SERVER_ID = ""
```

Then users will authorize via Discord's OAuth2 flow instead.

## Advanced: Webhooks (Optional)

For real-time verification updates, set up a webhook:

```python
# flask_webhook.py
from flask import Flask, request
from auth_handler import add_authorized_user

app = Flask(__name__)

@app.route('/webhook/restorecord', methods=['POST'])
def restorecord_webhook():
    data = request.json
    user_id = data.get('user_id')
    if data.get('verified'):
        add_authorized_user(user_id, "RestoreCord_Webhook")
    return {'status': 'ok'}

if __name__ == '__main__':
    app.run(port=5000)
```

Configure webhook URL in RestoreCord dashboard:
```
https://your-server.com/webhook/restorecord
```

## Summary Checklist

- [ ] Set `RESTORECORD_URL` (your RestoreCord instance URL)
- [ ] Set `RESTORECORD_SERVER_ID` (your Discord server ID)
- [ ] Set `RESTORECORD_API_KEY` (if your instance requires it)
- [ ] Run test script to verify connection
- [ ] Start the bot: `python meow_with_auth.py`
- [ ] Test with a user application
- [ ] Check logs for any API errors

## Need Help?

1. Check RestoreCord documentation for your specific instance
2. Review bot logs for error messages
3. Test API endpoints manually with `curl` or Postman
4. Verify your Discord server ID is correct
5. Make sure the RestoreCord instance is online and accessible
