# Auth Handler Documentation

## Overview

The Auth Handler is an authentication-based auto-accept system for Discord server applications. It allows server owners to pre-authorize users and automatically accept their applications, or require them to complete an authentication process before acceptance.

## Features

- **Auto-Accept for Authorized Users**: Users who are already in the authorization list are automatically accepted when they apply
- **Auth Request for New Users**: Users not in the auth list are prompted to complete authentication via a link (e.g., Telegram group or RestoreCord)
- **Pending Auth Monitoring**: Automatically approves users once they complete the authentication process
- **File-Based Auth Storage**: Simple JSON files for managing authorized and pending users
- **CLI Management Tool**: Easy-to-use command-line interface for managing authorized users

## Files

### Core Files

- **`auth_handler.py`**: Main authentication handler module
- **`meow_with_auth.py`**: Modified version of meow.py with auth integration
- **`auth_manager.py`**: CLI tool for managing authorized users

### Data Files (auto-generated)

- **`authorized_users.json`**: Stores list of authorized users
- **`pending_auth.json`**: Tracks users pending authentication

## How It Works

### Flow for Authorized Users

1. User submits application to join server
2. Auth handler checks if user is in `authorized_users.json`
3. If YES:
   - Opens interview channel
   - Sends welcome message
   - **Auto-approves the application immediately**
4. User is accepted to the server

### Flow for Non-Authorized Users

1. User submits application to join server
2. Auth handler checks if user is in `authorized_users.json`
3. If NO:
   - Opens group chat (GC) with the user
   - Sends authentication request message with auth link
   - Adds user to `pending_auth.json`
4. User clicks the auth link and completes authentication
5. Server admin adds user to authorized list (manually or via integration)
6. Auth monitor detects user is now authorized
7. **Auto-approves the application**
8. User is accepted to the server

## Setup Instructions

### 1. Basic Setup

1. **Copy your Discord token** to `auth_handler.py`:
   ```python
   TOKEN = "your_discord_user_token_here"
   ```

2. **Configure the auth link** in `auth_handler.py`:
   ```python
   AUTH_LINK = "https://t.me/addlist/your_telegram_group"  # Or your RestoreCord URL
   ```

3. **Optionally set RestoreCord URL** (if using RestoreCord):
   ```python
   RESTORECORD_URL = "https://your-restorecord-instance.com/verify"
   ```

### 2. Running the Bot

#### Option A: With Auth Handler (Recommended)

```bash
python meow_with_auth.py
```

This runs the bot with auth checking enabled. All applications will go through the auth process.

#### Option B: Standalone Auth Handler (Testing)

```bash
python auth_handler.py
```

This runs just the auth monitoring without the application polling (useful for testing).

### 3. Managing Authorized Users

#### Using the CLI Tool

```bash
python auth_manager.py
```

The CLI provides these options:
- **List Authorized Users**: View all users in the whitelist
- **List Pending Auth Users**: See who's waiting for auth
- **Authorize a User**: Manually add a user to the whitelist
- **Deauthorize a User**: Remove a user from the whitelist
- **Import Users from File**: Bulk add users from a text file
- **Export Authorized Users**: Save authorized users to a file
- **Clear All Authorized Users**: Reset the authorized list

#### Manually Authorizing Users

To manually add a user to the authorized list:

```bash
python auth_manager.py
# Select option 3 and enter the user ID
```

Or programmatically:
```python
from auth_handler import manually_authorize_user

manually_authorize_user("123456789012345678", "username")
```

#### Importing Users in Bulk

Create a text file with one user ID per line:
```
# authorized_users.txt
123456789012345678
987654321098765432
111222333444555666
```

Then import:
```bash
python auth_manager.py
# Select option 5 and enter filename
```

## Configuration Options

### In `auth_handler.py`

```python
# Discord Configuration
TOKEN = ""  # Your Discord user token
GUILD_ID = "1464067001256509452"  # Your server ID
OWN_USER_ID = "1411325023053938730"  # Your user ID

# Auth Configuration
AUTH_LINK = "https://t.me/addlist/..."  # The auth link users need to click
RESTORECORD_URL = ""  # Optional RestoreCord URL

# File paths
AUTH_FILES = {
    "authorized_users": "authorized_users.json",
    "pending_auth": "pending_auth.json"
}
```

### In `meow_with_auth.py`

```python
# Enable or disable auth handler
USE_AUTH_HANDLER = True  # Set to False to use original meow.py behavior

# Original meow.py configuration (used when auth is disabled)
MESSAGE_CONTENT = "..."
SERVER_INVITE_LINK = "..."
```

## API / Integration Points

### Programmatic Usage

You can integrate the auth handler into your own code:

```python
from auth_handler import (
    is_user_authorized,
    add_authorized_user,
    process_application_with_auth,
    monitor_pending_auths
)

# Check if a user is authorized
if is_user_authorized("123456789012345678"):
    print("User is authorized!")

# Authorize a new user
add_authorized_user("123456789012345678", "username")

# Process an application with auth checking
is_authorized, channel_id = process_application_with_auth(user_id, request_id)

# Start the pending auth monitor in a thread
import threading
monitor_thread = threading.Thread(target=monitor_pending_auths, daemon=True)
monitor_thread.start()
```

### RestoreCord Integration (Future Enhancement)

To integrate with RestoreCord API:

1. Set up RestoreCord API endpoint
2. Poll RestoreCord for newly verified users
3. Automatically add verified users to authorized list

Example webhook handler:
```python
@app.route('/restorecord/webhook', methods=['POST'])
def restorecord_webhook():
    data = request.json
    user_id = data.get('user_id')
    username = data.get('username')
    
    # Add to authorized list
    add_authorized_user(user_id, username)
    
    return {'status': 'ok'}
```

## Messages

### Auto-Accept Message (for authorized users)

```
✅ **Welcome!**

You're already authenticated! Your application has been auto-accepted.
```

### Auth Request Message (for non-authorized users)

```
🔐 **Authentication Required**

You need to authenticate to join this server.
Please click the link below to verify yourself:

**Auth Link:** https://t.me/addlist/...

Once you've completed authentication, you'll be automatically accepted!
```

### Auth Success Message (after completing auth)

```
✅ **Authentication Successful!**

You've been verified! Approving your application now...
```

## Customization

### Changing Messages

Edit the message constants in `auth_handler.py`:

```python
AUTH_REQUEST_MESSAGE = "Your custom message here..."
AUTO_ACCEPT_MESSAGE = "Your custom welcome message..."
```

### Adjusting Monitor Interval

The auth monitor checks for newly authorized users every 5 seconds by default. To change:

```python
def monitor_pending_auths():
    # ...
    time.sleep(5)  # Change this value
```

### Using Different Auth Systems

You can integrate any authentication system by:

1. Modifying `is_user_authorized()` to check your system's API
2. Setting up webhooks to call `add_authorized_user()` when users verify
3. Customizing the auth link in `AUTH_LINK`

## Troubleshooting

### Issue: Users not being auto-approved

**Solution**: Check if the user is actually in the authorized list:
```bash
python auth_manager.py
# Select option 1 to list authorized users
```

### Issue: Auth link not working

**Solution**: Verify the `AUTH_LINK` is correctly set in `auth_handler.py` and the link is accessible.

### Issue: Bot not detecting pending auths

**Solution**: Ensure the auth monitor thread is running. Check logs for:
```
🔍 Auth monitor thread started
```

### Issue: Token errors

**Solution**: Make sure the TOKEN is set in both `auth_handler.py` and properly synced in `meow_with_auth.py`.

## Security Considerations

- **Token Security**: Never commit your Discord token to version control
- **Authorized Users List**: Keep `authorized_users.json` secure - it controls who can auto-join
- **Auth Links**: Ensure auth links lead to secure, trusted authentication systems
- **Rate Limiting**: The bot includes rate limit handling, but be mindful of Discord's limits

## Advanced Usage

### Integration with External Database

Replace file-based storage with database:

```python
def is_user_authorized(user_id):
    # Query your database
    result = db.query("SELECT * FROM authorized_users WHERE user_id = ?", user_id)
    return result is not None

def add_authorized_user(user_id, username):
    # Insert into database
    db.execute("INSERT INTO authorized_users VALUES (?, ?)", user_id, username)
```

### Webhook for Real-Time Auth Updates

Set up a simple Flask webhook:

```python
from flask import Flask, request
from auth_handler import add_authorized_user

app = Flask(__name__)

@app.route('/webhook/auth', methods=['POST'])
def auth_webhook():
    data = request.json
    add_authorized_user(data['user_id'], data['username'])
    return {'status': 'success'}

if __name__ == '__main__':
    app.run(port=5000)
```

## Support

For issues or questions:
1. Check the logs for error messages
2. Verify configuration in `auth_handler.py`
3. Test with `auth_manager.py` CLI tool
4. Review the troubleshooting section above

## License

This project is provided as-is for educational purposes.
