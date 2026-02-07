# Auth RestoreCord Control Panel - GUI

## 🎨 Professional GUI Control Panel

A modern, sleek graphical user interface for managing the Auth RestoreCord bot with real-time configuration editing, start/stop controls, and live log monitoring.

![Control Panel](screenshots/control_panel_preview.png)

## ✨ Features

### 🎯 Real-Time Control
- **Start/Stop Bot** - Control the bot with clickable buttons
- **Live Status Indicator** - Visual status (Running/Stopped)
- **Non-Blocking Operations** - Edit config while bot runs

### ⚙️ Configuration Editor
- **Click-to-Edit Fields** - All settings in one place
- **Organized Sections** - Grouped by category
- **Save & Apply** - Changes apply instantly
- **Auto-Reload** - Refresh config from file

### 📊 Live Log Viewer
- **Real-Time Logs** - See bot activity as it happens
- **Color-Coded Messages** - Info, Warning, Error, Success
- **Side Panel Layout** - Logs don't interfere with controls
- **Clear Function** - Clean up old logs

### 🎨 Professional Design
- **Dark Theme** - Easy on the eyes
- **Modern Colors** - Cyan, purple, and accent colors
- **Clean Layout** - 60/40 split (controls/logs)
- **Smooth Experience** - No corny emojis, just professional icons

## 🚀 Usage

### Launch the Control Panel

```bash
python3 auth_control_panel.py
```

Or double-click the file if your system supports it.

### Configuration Sections

The control panel organizes settings into logical groups:

#### 1. Discord Configuration
- **Token** - Your Discord user token (password protected)
- **Guild ID** - Server ID
- **User ID** - Your user ID
- **Bot Client ID** - For OAuth2

#### 2. RestoreCord Settings
- **URL** - RestoreCord API endpoint
- **Server ID** - RestoreCord server
- **API Key** - Optional API key

#### 3. Application Requirements
- **Require Add People** - Enable/disable people requirement
- **Required Count** - How many people to add

#### 4. Server Configuration
- **Main Server Invite** - Link for added users

#### 5. Timing Settings
- **Channel Creation Wait** - Delay for channel creation
- **Auth Check Interval** - How often to check status

### How to Use

1. **Launch** - Run `python3 auth_control_panel.py`
2. **Edit Config** - Click any field and type new values
3. **Save** - Click "💾 SAVE & APPLY" to apply changes
4. **Start Bot** - Click "▶ START BOT" to begin monitoring
5. **Watch Logs** - View real-time activity in the right panel
6. **Stop Bot** - Click "■ STOP BOT" when done

### While Running

- ✅ Edit config anytime (bot keeps running)
- ✅ Logs update in real-time
- ✅ Status indicator shows current state
- ✅ Click "⟳ RELOAD" to refresh from file
- ✅ Click "🗑 CLEAR" to clear old logs

## 🎨 Color Scheme

The control panel uses a professional color palette:

- **Background**: Dark navy (#1a1a2e, #16213e)
- **Primary Accent**: Cyan (#00d4ff)
- **Secondary Accent**: Purple (#7c4dff)
- **Success**: Green (#00ff88)
- **Warning**: Gold (#ffd700)
- **Error**: Red (#ff4444)
- **Text**: White/Gray for readability

## 📋 Requirements

```bash
# Python 3.6+
# tkinter (usually included with Python)

# Install if needed:
sudo apt-get install python3-tk  # Ubuntu/Debian
brew install python-tk@3.9       # macOS
```

## 🖥️ Layout

```
┌─────────────────────────────────────────────────────────────┐
│                ⚡ Auth RestoreCord Control Panel            │
│              Real-time configuration & monitoring            │
├──────────────────────────────────┬──────────────────────────┤
│                                  │                          │
│  ● BOT CONTROLS                  │   ● LIVE LOGS            │
│  Status: ● RUNNING               │                          │
│  [▶ START] [■ STOP] [⟳ RELOAD]  │   [12:34:56] Started...  │
│                                  │   [12:34:57] Checking... │
│  ● CONFIGURATION                 │   [12:34:58] User...     │
│  [💾 SAVE & APPLY]               │   [12:34:59] Approved... │
│                                  │                          │
│  ▸ Discord Configuration         │   [12:35:00] Logs...     │
│    Token: ●●●●●●●●●●●           │   [12:35:01] Continue... │
│    Guild ID: 1234567890          │   [12:35:02] Running...  │
│    ...                           │                          │
│                                  │   [🗑 CLEAR]             │
│  ▸ RestoreCord Settings          │                          │
│    URL: https://...              │                          │
│    ...                           │                          │
│                                  │                          │
│  ▸ Application Requirements      │                          │
│    Require Add People: True      │                          │
│    ...                           │                          │
│                                  │                          │
└──────────────────────────────────┴──────────────────────────┘
```

## 🔧 Technical Details

### Architecture

- **GUI Framework**: tkinter (Python's built-in GUI toolkit)
- **Threading**: Separate thread for bot monitoring
- **Logging**: Queue-based log forwarding to GUI
- **Config**: Direct file editing with hot-reload

### Features

- **Non-blocking**: Bot runs in background thread
- **Real-time**: Logs update via queue every 100ms
- **Thread-safe**: Proper locking for config access
- **Error handling**: Try-catch blocks with user feedback
- **Clean shutdown**: Proper thread termination

### File Structure

```
auth_control_panel.py          # Main GUI application
auth_restorecore_main.py       # Bot logic (imported)
auth_restorecore_config.py     # Config file (edited)
```

## 🎯 Use Cases

### Perfect For:

- **Quick Setup** - Visual config is easier than editing files
- **Monitoring** - Watch bot activity in real-time
- **Testing** - Start/stop quickly while developing
- **Management** - Control multiple settings in one place
- **Live Operations** - Adjust config without restarting

### Not Needed For:

- **Headless Servers** - Use command-line version instead
- **Automated Deployment** - Use environment variables
- **CI/CD** - Stick with programmatic configuration

## 🐛 Troubleshooting

### GUI Won't Start

```bash
# Install tkinter
sudo apt-get install python3-tk

# Check if working
python3 -c "import tkinter; print('OK')"
```

### Config Not Saving

- Check file permissions on `auth_restorecore_config.py`
- Make sure no syntax errors in config file
- Try "⟳ RELOAD" to refresh

### Logs Not Updating

- Make sure bot is started (click "▶ START BOT")
- Check that `auth_restorecore_main.py` is present
- Verify logger is configured in bot module

## 📝 License

Same as the main Auth RestoreCord project.

## 🙏 Credits

Built with Python's tkinter for cross-platform compatibility.
Design inspired by modern development tools and IDEs.
