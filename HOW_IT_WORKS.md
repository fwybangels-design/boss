# How The Auth Application Bot Works

## Quick Summary

This bot automatically processes Discord server join applications using RestoreCord verification. When someone applies to join:

1. **If they're already verified on RestoreCord** → Bot auto-approves immediately (NO interview channel, NO messages) ✅
2. **If they're NOT verified** → Bot forwards an auth request → They authenticate on RestoreCord → Bot auto-approves → Sends success message ✅

## What Is Message Forwarding?

Instead of typing out new messages each time, the bot can **forward a pre-made template message** from your "secret server" for auth requests. Success messages are simple text (not forwarded).

### The Auth Request Message - FORWARD_AUTH_MESSAGE_ID

- **When it's used**: When a NEW user applies and needs to authenticate
- **What it does**: Forwards your template that says "Hey, verify on RestoreCord"
- **Why it's needed**: Tells users how to get verified
- **Example**: "🔐 Click this link to verify: [RestoreCord link]"
- **Additional text**: Optional extra text sent along with the forward

### Post-Acceptance Success Message

- **When it's used**: After a user completes RestoreCord verification and is approved
- **What it does**: Sends a simple success message (NOT forwarded)
- **Why it's needed**: Confirms approval and provides server invite link
- **Example**: "✅ Authentication successful! Make sure to join VC https://discord.gg/example"

## Why Use Forwarding Instead of Regular Messages?

### Without Forwarding (Old Way):
```
Bot types: "🔐 Click this link to verify: https://..."
```
Every auth request is newly typed by the bot.

### With Forwarding (New Way):
```
Bot forwards message #123 from Secret Server
(with optional additional text)
```
Auth request is a pre-made template from your secret server.

### Benefits:
1. **Consistency**: All auth requests look the same (formatting, emojis, text)
2. **Easy Updates**: Edit the template once in secret server, affects all future forwards
3. **Professional**: Messages can have rich formatting, images, embeds
4. **No Typos**: Set it once, forwards it perfectly every time
5. **Additional Text**: Can add custom text along with the forward

**Note:** Only auth request messages can be forwarded. Success messages are simple text sent after approval.

## Complete Flow Diagram

```
User Applies to Join Server
         ↓
    Bot Checks RestoreCord API:
    "Is user verified?"
         ↓
    ┌────┴────┐
   YES       NO
    │         │
    │         ↓
    │    Bot Opens Group Chat
    │    Bot Forwards AUTH REQUEST MESSAGE ← FORWARD_AUTH_MESSAGE_ID
    │    (Optional: + FORWARD_AUTH_ADDITIONAL_TEXT)
    │         │
    │         ↓
    │    User Clicks Link & Authenticates on RestoreCord
    │         │
    │         ↓
    │    Bot Polls RestoreCord API (every 2 seconds)
    │    Bot Detects User is Now Verified
    │         │
    ↓         ↓
Bot Auto-Approves Application
(NO interview channel for already verified)
    ↓
Bot Sends SUCCESS MESSAGE (simple text, not forwarded)
"✅ Authentication successful! Make sure to join VC [link]"
    ↓
✅ User Joins Server!
```

**CRITICAL:** Already verified users get NO interview channel and NO messages - just instant approval.

## Setting Up Message Forwarding

### Step 1: Create Your Secret Server
1. Create a private Discord server (or use existing one)
2. Create a channel (e.g., #message-templates)
3. This is your "secret server" where the auth request template lives

### Step 2: Create Your Auth Request Template Message
In your secret server channel, type and send this message:

**Auth Request Message:**
```
🔐 **Verification Required**

To join our server, please verify yourself:
Click here: https://restorecord.yourserver.com

Once verified, you'll be auto-approved within seconds!
```

**Important:** The message should contain your RestoreCord verification link.

### Step 3: Get The IDs
1. Enable Developer Mode in Discord (Settings → Advanced → Developer Mode)
2. Right-click the channel → Copy ID (this is your `FORWARD_SOURCE_CHANNEL_ID`)
3. Right-click the auth request message → Copy Message ID (this is your `FORWARD_AUTH_MESSAGE_ID`)

### Step 4: Configure config.py
```python
FORWARD_SOURCE_CHANNEL_ID = "123456789012345678"  # Your channel ID
FORWARD_AUTH_MESSAGE_ID = "111111111111111111"    # Auth request message ID

# Optional: Add extra text
FORWARD_AUTH_ADDITIONAL_TEXT = "Please complete verification to join!"
```

### Step 5: Run The Bot
```bash
python meow_with_auth.py
```

Now the bot will forward your auth request template message instead of typing new ones!

### Optional Additional Text

You can add extra text that gets sent **along with** the forwarded message:

```python
FORWARD_AUTH_ADDITIONAL_TEXT = "Important: Complete verification within 24 hours!"
```

When the bot forwards the auth request, it will show:
1. The forwarded message (your template)
2. Your additional text below it

This is useful for:
- Adding current announcements
- Personalizing without changing the template
- Adding temporary information

**Leave empty (`""`) if you don't want additional text.**

## Why Is This Better?

### Before (Regular Messages):
- Hard-coded text in Python code
- Need to edit code and restart bot to change messages
- Easy to make typos
- Different formatting each time you update

### After (Forwarding):
- Templates stored in Discord (visual editor)
- Edit templates anytime, no bot restart needed
- Perfect consistency
- Can use Discord's rich formatting, emojis, embeds

### Additional Benefits:
- **Instant Approval for Verified Users**: No interview channel = faster, cleaner process
- **RestoreCord API Polling**: Always checks the authoritative source, no stale data
- **No Local Storage**: No authorized_users.json to manage or sync
- **Simple Success Messages**: Post-acceptance message is straightforward, not a forward

## Troubleshooting

### "No message ID configured, falling back to regular send"
- You haven't set FORWARD_AUTH_MESSAGE_ID in config.py
- Bot will send regular text messages instead
- This is fine if you don't want forwarding

### "Failed to forward message"
- Check that all IDs are correct
- Make sure the bot/account can access the secret server channel
- Verify Developer Mode is enabled and you copied the right IDs

### Messages Not Forwarding
- Check `USE_MESSAGE_FORWARDING` is True (auto-set if channel ID is provided)
- Verify `FORWARD_SOURCE_CHANNEL_ID` is set
- Verify `FORWARD_AUTH_MESSAGE_ID` is set
- Check logs for specific error messages

### Users Not Being Approved
- Verify RestoreCord is properly configured (URL, SERVER_ID, API_KEY)
- Check user is actually verified on RestoreCord
- Check bot logs for RestoreCord API errors

## Quick Reference

| Config Variable | What It Does | Example Value |
|----------------|--------------|---------------|
| `RESTORECORD_URL` | RestoreCord instance URL | `"https://verify.server.com"` |
| `RESTORECORD_SERVER_ID` | Your server ID on RestoreCord | `"1234567890"` |
| `SERVER_INVITE_LINK` | Server invite in success message | `"https://discord.gg/example"` |
| `FORWARD_SOURCE_CHANNEL_ID` | Where auth template is stored | `"123456789012345678"` |
| `FORWARD_AUTH_MESSAGE_ID` | Template for auth requests | `"111111111111111111"` |
| `FORWARD_AUTH_ADDITIONAL_TEXT` | Extra text with auth forward | `"Check DMs!"` or `""` |

## Summary

**Message forwarding** tells the bot to forward a pre-made auth request template instead of typing new messages each time. This makes auth requests consistent, professional, and easy to update. You create the template once in a "secret server" and the bot forwards it.

**Already verified users** get instant approval with NO interview channel and NO messages - completely silent and automatic.

**Post-acceptance success messages** are simple text (not forwarded) with an optional server invite link.

**The flow is:**
1. **Already verified on RestoreCord** - Instant approval (silent)
2. **Not verified** - Forward auth request → User verifies on RestoreCord → Bot approves → Sends success message
