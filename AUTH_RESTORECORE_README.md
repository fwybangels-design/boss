# Auth RestoreCord Bot - Consolidated Structure

The auth restorecore application bot has been reorganized into just **2 files** for simplicity:

## Files

### 1. `auth_restorecore_main.py` - Main Application
The main file containing all the logic:
- Core authentication functions
- RestoreCord API integration
- Discord API functions
- Auth monitoring and processing
- CLI management interface
- Configuration testing

**Key Functions:**
- `process_application_with_auth(user_id, request_id)` - Main entry point for processing applications
- `is_user_authorized(user_id)` - Check if a user is verified
- `check_restorecord_verification(user_id)` - Check RestoreCord API
- `monitor_pending_auths()` - Background thread for monitoring pending auths
- `check_and_process_auth(user_id, request_id)` - Core auth logic

### 2. `auth_restorecore_config.py` - Configuration
Contains all configuration variables:
- Discord credentials (TOKEN, GUILD_ID, etc.)
- RestoreCord settings (URL, API key, Server ID)
- Message templates
- Timing settings
- OAuth2 configuration

## Usage

### Command Line Interface

Run the CLI manager:
```bash
python auth_restorecore_main.py
```

### Command Line Options

```bash
# Start auth monitor
python auth_restorecore_main.py --monitor

# Test configuration
python auth_restorecore_main.py --test

# Check user verification status
python auth_restorecore_main.py --check-user USER_ID

# List pending auth users
python auth_restorecore_main.py --list-pending

# Show help
python auth_restorecore_main.py --help
```

### Programmatic Usage

Import and use in your code:

```python
from auth_restorecore_main import (
    process_application_with_auth,
    is_user_authorized,
    monitor_pending_auths
)

# Process an application with auth checking
is_authorized, channel_id = process_application_with_auth(user_id, request_id)

# Check if a user is authorized
if is_user_authorized(user_id):
    print("User is verified!")

# Start monitoring in background
import threading
monitor_thread = threading.Thread(target=monitor_pending_auths, daemon=True)
monitor_thread.start()
```

## Configuration

Edit `auth_restorecore_config.py` and set:

1. **Discord Token** (required):
   ```python
   TOKEN = "your_discord_token_here"
   ```

2. **RestoreCord** (for verification):
   ```python
   RESTORECORD_URL = "https://verify.yourserver.com"
   RESTORECORD_SERVER_ID = "your_server_id"
   RESTORECORD_API_KEY = "your_api_key"  # Optional
   ```

3. **Discord OAuth2** (alternative to RestoreCord):
   ```python
   BOT_CLIENT_ID = "your_bot_client_id"
   ```

4. **Application Requirements** (optional):
   ```python
   REQUIRE_ADD_PEOPLE = True  # Require adding people to group DM
   REQUIRED_PEOPLE_COUNT = 2  # Number of people to add
   ```

## Application Flow

When `REQUIRE_ADD_PEOPLE = True`:

1. User applies to join server
2. Bot opens interview channel and sends auth request
3. User must complete **BOTH** requirements:
   - ✅ Verify through RestoreCord (or OAuth2)
   - 👥 Add 2 people to the group DM
4. Bot monitors every 2 seconds
5. Once **BOTH** are complete → Auto-approve! ⚡

When `REQUIRE_ADD_PEOPLE = False`:
- Only RestoreCord verification is required
- No need to add people

## Integration with Other Bots

To use this in other bots (like meow.py):

```python
import auth_restorecore_main as auth_handler

# Then use auth_handler.function_name()
is_authorized, channel_id = auth_handler.process_application_with_auth(user_id, reqid)
```

## Features

- ✅ Real-time verification via RestoreCord API
- ✅ Auto-approval of verified users (no interview needed)
- ✅ Require users to add people to group DM before acceptance
- ✅ Background monitoring of pending auth requests
- ✅ Message forwarding support
- ✅ CLI management interface
- ✅ Configuration testing
- ✅ Thread-safe file operations

## Migration from Old Files

The following old files have been consolidated:
- `auth_handler.py` → `auth_restorecore_main.py`
- `auth_manager.py` → `auth_restorecore_main.py` (CLI features)
- `test_restorecord.py` → `auth_restorecore_main.py` (--test command)
- `example_auth_usage.py` → `auth_restorecore_main.py` (functions directly usable)
- RestoreCord config from `config.py` → `auth_restorecore_config.py`

The old files are kept for backwards compatibility but the new consolidated files are recommended.

## Security Notes

- Never commit your Discord token to git
- Use environment variables for sensitive data
- The bot uses RestoreCord API for verification - no local storage of auth data
- All file operations are thread-safe

## Support

For detailed configuration instructions, see the configuration test:
```bash
python auth_restorecore_main.py --test
```
