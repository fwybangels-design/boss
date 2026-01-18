# Gateway Application Bot

A Discord application bot that acts as a gateway, redirecting applicants to the real server and automatically denying their application after a configurable delay.

## Features

- **Application Gateway**: Automatically opens and responds to Discord server applications with a custom gateway message
- **Auto-Deny**: Automatically denies applications after a configurable delay (default: 30 seconds)
- **Reapplication Support**: Allows users to reapply and receive the gateway message again
- **Real-Time Configuration**: Update settings without restarting the bot
- **Thread-Safe**: Uses threading locks for concurrent application processing
- **Interactive Menu**: User-friendly CLI menu for configuration

## How It Works

1. User applies to join the Discord server
2. Bot detects the application and opens an interview (group DM)
3. Bot sends a gateway message redirecting them to the real server
4. After the configured delay (default: 30 seconds), bot auto-denies the application
5. User can reapply and the process repeats

This prevents users from actually joining the application server while still providing them with information about the real server location.

## Installation

Install required dependencies:
```bash
pip install -r requirements.txt
```

## Usage

Run the gateway bot:
```bash
python gateway.py
```

## Configuration Menu

When you start the bot, you'll see an interactive menu:

```
============================================================
          🚪 GATEWAY APPLICATION BOT - CONTROL PANEL 🚪
============================================================
1. Set Application Token
2. Set Guild ID
3. Set Own User ID
4. Set Gateway Message
5. Set Auto-Deny Delay (seconds)
6. View Current Configuration
7. Start Gateway Bot
8. Exit
============================================================
```

### Setup Steps

1. **Set Application Token** (Option 1)
   - Enter your Discord user token (the token used to access the Discord API as yourself)
   - This token needs permission to view and manage applications for the guild

2. **Set Guild ID** (Option 2)
   - Enter the Discord server (guild) ID where applications will be processed
   - You can find this by enabling Developer Mode in Discord and right-clicking the server

3. **Set Own User ID** (Option 3) [Optional]
   - Enter your Discord user ID
   - This is used for tracking purposes

4. **Set Gateway Message** (Option 4)
   - Customize the message sent to applicants
   - Default: "The real server is here: discord.gg/example\nJoin telegram to never lose us: https://t.me/example"
   - Supports multiple lines - type your message and enter "END" on a new line when done
   - Example:
     ```
     The real server is here: discord.gg/yourserver
     Join our telegram to never lose us: https://t.me/yourgroup
     END
     ```

5. **Set Auto-Deny Delay** (Option 5)
   - Configure how long to wait before auto-denying (in seconds)
   - Default: 30 seconds
   - Recommendation: 30-60 seconds to give users time to read the message

6. **View Current Configuration** (Option 6)
   - Display all current settings
   - Use this to verify your configuration before starting

7. **Start Gateway Bot** (Option 7)
   - Starts the bot with current settings
   - Bot will continuously monitor for new applications
   - Press Ctrl+C to stop and return to menu
   - Settings can be changed in real-time by stopping and updating

## Real-Time Configuration Changes

One of the key features of this bot is that you can change settings without fully restarting:

1. Start the bot (Option 7)
2. Press Ctrl+C to stop monitoring
3. Update any settings (Options 1-5)
4. Start the bot again (Option 7)

The changes take effect immediately because the bot uses thread-safe configuration access.

## Example Workflow

```
1. Configure your token, guild ID, and gateway message
2. Start the bot
3. User applies to your Discord server
4. Bot opens interview DM with the user
5. Bot sends gateway message: "The real server is here: discord.gg/realserver..."
6. Bot waits 30 seconds
7. Bot auto-denies the application
8. User can apply again and receive the same gateway message
```

## Security Notes

- **Keep your token secure**: Never share your Discord token
- **Token permissions**: The token needs access to view and manage guild applications
- **Rate limiting**: The bot includes built-in delays to avoid API rate limits
- **Thread safety**: All configuration changes are protected by locks

## Comparison with meow.py

While `meow.py` is designed to manage applications with approval workflows based on friend requests and screenshots, `gateway.py` is specifically designed to:

- Act as a redirect/gateway mechanism
- Never actually approve applications
- Auto-deny after delivering the gateway message
- Allow repeated applications from the same user

## Troubleshooting

### Bot not detecting applications
- Verify your token is correct
- Ensure the guild ID matches your server
- Check that applications are actually being submitted

### Gateway message not sending
- Verify the bot can open interview DMs
- Check API response logs for errors
- Ensure the token has proper permissions

### Auto-deny not working
- Check the delay setting is reasonable (> 0 seconds)
- Verify the request ID is valid
- Look for error messages in the logs

## Files Created

This bot does not create any configuration files - all settings are stored in memory. This means:
- Settings are lost when you exit the program
- No risk of accidentally committing sensitive data
- Clean and simple operation

## Technical Details

- **Threading**: Uses daemon threads for processing multiple applications concurrently
- **Request Deduplication**: Tracks seen request IDs to prevent duplicate processing
- **Exponential Backoff**: Uses increasing delays when polling for interview channels
- **Thread-Safe Configuration**: All configuration access is protected by locks for real-time updates

## License

This project is provided as-is for educational purposes.
