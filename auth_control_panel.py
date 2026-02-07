#!/usr/bin/env python3
"""
Auth RestoreCord Control Panel - Modern GUI
Advanced control panel with real-time config editing, start/stop controls, and live logs.
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import queue
import logging
import sys
import time
from datetime import datetime
import json
import os

# Import the auth module
try:
    import auth_restorecore_main as auth_module
    import auth_restorecore_config as config_module
except ImportError as e:
    print(f"Error importing auth modules: {e}")
    sys.exit(1)


class ColorScheme:
    """Professional color scheme for the control panel."""
    # Dark theme colors
    BG_DARK = "#1a1a2e"
    BG_MEDIUM = "#16213e"
    BG_LIGHT = "#0f3460"
    ACCENT_PRIMARY = "#00d4ff"
    ACCENT_SECONDARY = "#7c4dff"
    ACCENT_SUCCESS = "#00ff88"
    ACCENT_WARNING = "#ffd700"
    ACCENT_ERROR = "#ff4444"
    TEXT_PRIMARY = "#ffffff"
    TEXT_SECONDARY = "#b0b0b0"
    TEXT_MUTED = "#666666"
    
    # Button colors
    BTN_PRIMARY = "#00d4ff"
    BTN_SUCCESS = "#00ff88"
    BTN_DANGER = "#ff4444"
    BTN_WARNING = "#ffd700"


class LogHandler(logging.Handler):
    """Custom logging handler that sends logs to a queue for GUI display."""
    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue
        
    def emit(self, record):
        msg = self.format(record)
        self.log_queue.put(msg)


class AuthControlPanel:
    """Main control panel GUI application."""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Auth RestoreCord Control Panel")
        self.root.geometry("1400x900")
        self.root.configure(bg=ColorScheme.BG_DARK)
        
        # Set minimum size
        self.root.minsize(1200, 700)
        
        # Bot state
        self.bot_running = False
        self.monitor_thread = None
        self.log_queue = queue.Queue()
        
        # Config cache
        self.config_vars = {}
        
        # Setup logging
        self.setup_logging()
        
        # Create UI
        self.create_ui()
        
        # Start log updater
        self.update_logs()
        
        # Load current config
        self.load_config()
        
    def setup_logging(self):
        """Setup logging to capture bot logs."""
        log_handler = LogHandler(self.log_queue)
        log_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', 
                                                   datefmt='%H:%M:%S'))
        
        # Get the auth module logger
        auth_logger = logging.getLogger('auth_restorecore_main')
        auth_logger.addHandler(log_handler)
        auth_logger.setLevel(logging.INFO)
        
    def create_ui(self):
        """Create the main UI layout."""
        # Main container with two panels
        main_container = tk.Frame(self.root, bg=ColorScheme.BG_DARK)
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Left panel - Controls and Config (60%)
        left_panel = tk.Frame(main_container, bg=ColorScheme.BG_DARK)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # Right panel - Logs (40%)
        right_panel = tk.Frame(main_container, bg=ColorScheme.BG_DARK)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        # Create sections
        self.create_header(left_panel)
        self.create_control_section(left_panel)
        self.create_config_section(left_panel)
        self.create_log_section(right_panel)
        
    def create_header(self, parent):
        """Create the header section."""
        header = tk.Frame(parent, bg=ColorScheme.BG_MEDIUM, relief=tk.RAISED, bd=2)
        header.pack(fill=tk.X, pady=(0, 10))
        
        # Title with gradient effect (using unicode blocks)
        title = tk.Label(header, 
                        text="⚡ Auth RestoreCord Control Panel",
                        font=("Segoe UI", 24, "bold"),
                        fg=ColorScheme.ACCENT_PRIMARY,
                        bg=ColorScheme.BG_MEDIUM,
                        pady=15)
        title.pack()
        
        # Subtitle
        subtitle = tk.Label(header,
                           text="Real-time configuration & monitoring",
                           font=("Segoe UI", 11),
                           fg=ColorScheme.TEXT_SECONDARY,
                           bg=ColorScheme.BG_MEDIUM,
                           pady=5)
        subtitle.pack()
        
    def create_control_section(self, parent):
        """Create the control buttons section."""
        control_frame = tk.Frame(parent, bg=ColorScheme.BG_MEDIUM, relief=tk.RAISED, bd=2)
        control_frame.pack(fill=tk.X, pady=(0, 10), padx=5)
        
        # Section title
        title = tk.Label(control_frame,
                        text="● BOT CONTROLS",
                        font=("Segoe UI", 12, "bold"),
                        fg=ColorScheme.TEXT_PRIMARY,
                        bg=ColorScheme.BG_MEDIUM,
                        anchor=tk.W,
                        pady=10,
                        padx=15)
        title.pack(fill=tk.X)
        
        # Status indicator
        status_container = tk.Frame(control_frame, bg=ColorScheme.BG_MEDIUM)
        status_container.pack(fill=tk.X, padx=15, pady=(0, 10))
        
        tk.Label(status_container,
                text="Status:",
                font=("Segoe UI", 10),
                fg=ColorScheme.TEXT_SECONDARY,
                bg=ColorScheme.BG_MEDIUM).pack(side=tk.LEFT, padx=(0, 10))
        
        self.status_label = tk.Label(status_container,
                                     text="● STOPPED",
                                     font=("Segoe UI", 10, "bold"),
                                     fg=ColorScheme.ACCENT_ERROR,
                                     bg=ColorScheme.BG_MEDIUM)
        self.status_label.pack(side=tk.LEFT)
        
        # Button container
        btn_container = tk.Frame(control_frame, bg=ColorScheme.BG_MEDIUM)
        btn_container.pack(fill=tk.X, padx=15, pady=(0, 15))
        
        # Start button
        self.start_btn = tk.Button(btn_container,
                                   text="▶ START BOT",
                                   font=("Segoe UI", 11, "bold"),
                                   fg=ColorScheme.BG_DARK,
                                   bg=ColorScheme.ACCENT_SUCCESS,
                                   activebackground="#00cc77",
                                   relief=tk.FLAT,
                                   cursor="hand2",
                                   padx=20,
                                   pady=10,
                                   command=self.start_bot)
        self.start_btn.pack(side=tk.LEFT, padx=(0, 10), expand=True, fill=tk.X)
        
        # Stop button
        self.stop_btn = tk.Button(btn_container,
                                  text="■ STOP BOT",
                                  font=("Segoe UI", 11, "bold"),
                                  fg=ColorScheme.TEXT_PRIMARY,
                                  bg=ColorScheme.ACCENT_ERROR,
                                  activebackground="#cc0000",
                                  relief=tk.FLAT,
                                  cursor="hand2",
                                  padx=20,
                                  pady=10,
                                  state=tk.DISABLED,
                                  command=self.stop_bot)
        self.stop_btn.pack(side=tk.LEFT, padx=(0, 10), expand=True, fill=tk.X)
        
        # Reload config button
        reload_btn = tk.Button(btn_container,
                              text="⟳ RELOAD",
                              font=("Segoe UI", 11, "bold"),
                              fg=ColorScheme.TEXT_PRIMARY,
                              bg=ColorScheme.ACCENT_WARNING,
                              activebackground="#ddb800",
                              relief=tk.FLAT,
                              cursor="hand2",
                              padx=20,
                              pady=10,
                              command=self.load_config)
        reload_btn.pack(side=tk.LEFT, expand=True, fill=tk.X)
        
    def create_config_section(self, parent):
        """Create the configuration editing section."""
        config_frame = tk.Frame(parent, bg=ColorScheme.BG_MEDIUM, relief=tk.RAISED, bd=2)
        config_frame.pack(fill=tk.BOTH, expand=True, padx=5)
        
        # Section title
        title_container = tk.Frame(config_frame, bg=ColorScheme.BG_MEDIUM)
        title_container.pack(fill=tk.X, pady=10, padx=15)
        
        tk.Label(title_container,
                text="● CONFIGURATION",
                font=("Segoe UI", 12, "bold"),
                fg=ColorScheme.TEXT_PRIMARY,
                bg=ColorScheme.BG_MEDIUM,
                anchor=tk.W).pack(side=tk.LEFT)
        
        # Save button in title
        save_btn = tk.Button(title_container,
                            text="💾 SAVE & APPLY",
                            font=("Segoe UI", 9, "bold"),
                            fg=ColorScheme.BG_DARK,
                            bg=ColorScheme.ACCENT_PRIMARY,
                            activebackground="#00b8dd",
                            relief=tk.FLAT,
                            cursor="hand2",
                            padx=15,
                            pady=5,
                            command=self.save_config)
        save_btn.pack(side=tk.RIGHT)
        
        # Scrollable config area
        canvas = tk.Canvas(config_frame, bg=ColorScheme.BG_MEDIUM, highlightthickness=0)
        scrollbar = ttk.Scrollbar(config_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=ColorScheme.BG_MEDIUM)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(15, 0))
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 15))
        
        # Config fields
        self.create_config_fields(scrollable_frame)
        
    def create_config_fields(self, parent):
        """Create configuration input fields."""
        configs = [
            ("Discord Configuration", [
                ("TOKEN", "Discord User Token", True),
                ("GUILD_ID", "Server/Guild ID", False),
                ("OWN_USER_ID", "Your User ID", False),
                ("BOT_CLIENT_ID", "Bot Client ID (OAuth2)", False),
            ]),
            ("RestoreCord Settings", [
                ("RESTORECORD_URL", "RestoreCord URL", False),
                ("RESTORECORD_SERVER_ID", "RestoreCord Server ID", False),
                ("RESTORECORD_API_KEY", "API Key (optional)", True),
            ]),
            ("Application Requirements", [
                ("REQUIRE_ADD_PEOPLE", "Require Adding People (True/False)", False),
                ("REQUIRED_PEOPLE_COUNT", "Number of People to Add", False),
            ]),
            ("Server Configuration", [
                ("MAIN_SERVER_INVITE", "Main Server Invite Link", False),
            ]),
            ("Timing Settings", [
                ("CHANNEL_CREATION_WAIT", "Channel Creation Wait (seconds)", False),
                ("AUTH_CHECK_INTERVAL", "Auth Check Interval (seconds)", False),
            ])
        ]
        
        for section_title, fields in configs:
            # Section header
            section_header = tk.Frame(parent, bg=ColorScheme.BG_LIGHT, relief=tk.RIDGE, bd=1)
            section_header.pack(fill=tk.X, pady=(10, 5))
            
            tk.Label(section_header,
                    text=f"▸ {section_title}",
                    font=("Segoe UI", 10, "bold"),
                    fg=ColorScheme.ACCENT_SECONDARY,
                    bg=ColorScheme.BG_LIGHT,
                    anchor=tk.W,
                    padx=10,
                    pady=5).pack(fill=tk.X)
            
            # Fields
            for field_name, label_text, is_password in fields:
                field_frame = tk.Frame(parent, bg=ColorScheme.BG_MEDIUM)
                field_frame.pack(fill=tk.X, pady=3)
                
                # Label
                label = tk.Label(field_frame,
                               text=label_text,
                               font=("Segoe UI", 9),
                               fg=ColorScheme.TEXT_SECONDARY,
                               bg=ColorScheme.BG_MEDIUM,
                               anchor=tk.W)
                label.pack(anchor=tk.W, padx=(10, 0))
                
                # Entry field
                entry = tk.Entry(field_frame,
                               font=("Segoe UI", 10),
                               fg=ColorScheme.TEXT_PRIMARY,
                               bg=ColorScheme.BG_DARK,
                               insertbackground=ColorScheme.ACCENT_PRIMARY,
                               relief=tk.FLAT,
                               bd=0,
                               show="●" if is_password else "")
                entry.pack(fill=tk.X, padx=10, pady=(2, 0), ipady=5)
                
                self.config_vars[field_name] = entry
                
    def create_log_section(self, parent):
        """Create the live log viewer section."""
        log_frame = tk.Frame(parent, bg=ColorScheme.BG_MEDIUM, relief=tk.RAISED, bd=2)
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        # Section title
        title_container = tk.Frame(log_frame, bg=ColorScheme.BG_MEDIUM)
        title_container.pack(fill=tk.X, pady=10, padx=15)
        
        tk.Label(title_container,
                text="● LIVE LOGS",
                font=("Segoe UI", 12, "bold"),
                fg=ColorScheme.TEXT_PRIMARY,
                bg=ColorScheme.BG_MEDIUM,
                anchor=tk.W).pack(side=tk.LEFT)
        
        # Clear button
        clear_btn = tk.Button(title_container,
                             text="🗑 CLEAR",
                             font=("Segoe UI", 9, "bold"),
                             fg=ColorScheme.TEXT_PRIMARY,
                             bg=ColorScheme.ACCENT_ERROR,
                             activebackground="#cc0000",
                             relief=tk.FLAT,
                             cursor="hand2",
                             padx=15,
                             pady=5,
                             command=self.clear_logs)
        clear_btn.pack(side=tk.RIGHT)
        
        # Log text area
        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            font=("Consolas", 9),
            fg=ColorScheme.TEXT_PRIMARY,
            bg=ColorScheme.BG_DARK,
            insertbackground=ColorScheme.ACCENT_PRIMARY,
            relief=tk.FLAT,
            wrap=tk.WORD,
            state=tk.DISABLED
        )
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))
        
        # Configure log text tags for colored output
        self.log_text.tag_config("INFO", foreground=ColorScheme.ACCENT_PRIMARY)
        self.log_text.tag_config("WARNING", foreground=ColorScheme.ACCENT_WARNING)
        self.log_text.tag_config("ERROR", foreground=ColorScheme.ACCENT_ERROR)
        self.log_text.tag_config("SUCCESS", foreground=ColorScheme.ACCENT_SUCCESS)
        
    def load_config(self):
        """Load current configuration into the UI."""
        try:
            # Reload the config module
            import importlib
            importlib.reload(config_module)
            
            # Load values into fields
            config_map = {
                "TOKEN": getattr(config_module, "TOKEN", ""),
                "GUILD_ID": getattr(config_module, "GUILD_ID", ""),
                "OWN_USER_ID": getattr(config_module, "OWN_USER_ID", ""),
                "BOT_CLIENT_ID": getattr(config_module, "BOT_CLIENT_ID", ""),
                "RESTORECORD_URL": getattr(config_module, "RESTORECORD_URL", ""),
                "RESTORECORD_SERVER_ID": getattr(config_module, "RESTORECORD_SERVER_ID", ""),
                "RESTORECORD_API_KEY": getattr(config_module, "RESTORECORD_API_KEY", ""),
                "REQUIRE_ADD_PEOPLE": str(getattr(config_module, "REQUIRE_ADD_PEOPLE", True)),
                "REQUIRED_PEOPLE_COUNT": str(getattr(config_module, "REQUIRED_PEOPLE_COUNT", 2)),
                "MAIN_SERVER_INVITE": getattr(config_module, "MAIN_SERVER_INVITE", ""),
                "CHANNEL_CREATION_WAIT": str(getattr(config_module, "CHANNEL_CREATION_WAIT", 2)),
                "AUTH_CHECK_INTERVAL": str(getattr(config_module, "AUTH_CHECK_INTERVAL", 2)),
            }
            
            for field_name, value in config_map.items():
                if field_name in self.config_vars:
                    self.config_vars[field_name].delete(0, tk.END)
                    self.config_vars[field_name].insert(0, str(value))
            
            self.add_log("✓ Configuration loaded successfully", "SUCCESS")
            
        except Exception as e:
            self.add_log(f"✗ Error loading config: {e}", "ERROR")
            
    def save_config(self):
        """Save configuration changes to the config file."""
        try:
            config_path = "/home/runner/work/boss/boss/auth_restorecore_config.py"
            
            # Read current config file
            with open(config_path, 'r') as f:
                lines = f.readlines()
            
            # Update values
            new_lines = []
            for line in lines:
                updated = False
                for field_name, entry in self.config_vars.items():
                    if line.strip().startswith(f"{field_name} ="):
                        value = entry.get().strip()
                        
                        # Handle different types
                        if field_name == "REQUIRE_ADD_PEOPLE":
                            value = "True" if value.lower() in ['true', '1', 'yes'] else "False"
                            new_lines.append(f'{field_name} = {value}\n')
                        elif field_name in ["REQUIRED_PEOPLE_COUNT", "CHANNEL_CREATION_WAIT", "AUTH_CHECK_INTERVAL"]:
                            new_lines.append(f'{field_name} = {value}\n')
                        else:
                            new_lines.append(f'{field_name} = "{value}"\n')
                        updated = True
                        break
                
                if not updated:
                    new_lines.append(line)
            
            # Write back
            with open(config_path, 'w') as f:
                f.writelines(new_lines)
            
            # Reload the module
            import importlib
            importlib.reload(config_module)
            importlib.reload(auth_module)
            
            self.add_log("✓ Configuration saved and applied!", "SUCCESS")
            messagebox.showinfo("Success", "Configuration saved and applied successfully!")
            
        except Exception as e:
            self.add_log(f"✗ Error saving config: {e}", "ERROR")
            messagebox.showerror("Error", f"Failed to save configuration: {e}")
            
    def start_bot(self):
        """Start the auth bot."""
        if self.bot_running:
            return
            
        try:
            self.bot_running = True
            self.update_status("RUNNING", ColorScheme.ACCENT_SUCCESS)
            
            self.start_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.NORMAL)
            
            # Start the monitor thread
            self.monitor_thread = threading.Thread(
                target=auth_module.monitor_pending_auths,
                daemon=True
            )
            self.monitor_thread.start()
            
            self.add_log("✓ Bot started successfully!", "SUCCESS")
            self.add_log("⏳ Monitoring pending auth requests...", "INFO")
            
        except Exception as e:
            self.bot_running = False
            self.update_status("ERROR", ColorScheme.ACCENT_ERROR)
            self.add_log(f"✗ Error starting bot: {e}", "ERROR")
            messagebox.showerror("Error", f"Failed to start bot: {e}")
            
    def stop_bot(self):
        """Stop the auth bot."""
        if not self.bot_running:
            return
            
        try:
            self.bot_running = False
            self.update_status("STOPPED", ColorScheme.ACCENT_ERROR)
            
            self.start_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)
            
            # Note: The monitor thread will stop on next iteration
            self.add_log("✓ Bot stopped", "WARNING")
            
        except Exception as e:
            self.add_log(f"✗ Error stopping bot: {e}", "ERROR")
            
    def update_status(self, status_text, color):
        """Update the status indicator."""
        self.status_label.config(text=f"● {status_text}", fg=color)
        
    def add_log(self, message, tag="INFO"):
        """Add a log message to the log viewer."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_queue.put((f"[{timestamp}] {message}", tag))
        
    def update_logs(self):
        """Update the log viewer with queued messages."""
        try:
            while True:
                if isinstance(self.log_queue.queue[0], str):
                    # Old format (just string)
                    msg = self.log_queue.get_nowait()
                    tag = "INFO"
                else:
                    # New format (tuple with tag)
                    msg, tag = self.log_queue.get_nowait()
                
                self.log_text.config(state=tk.NORMAL)
                self.log_text.insert(tk.END, msg + "\n", tag)
                self.log_text.see(tk.END)
                self.log_text.config(state=tk.DISABLED)
        except queue.Empty:
            pass
        except:
            pass
        
        # Schedule next update
        self.root.after(100, self.update_logs)
        
    def clear_logs(self):
        """Clear all logs from the viewer."""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.add_log("Logs cleared", "INFO")


def main():
    """Main entry point."""
    root = tk.Tk()
    
    # Try to use a better theme if available
    try:
        root.tk.call("source", "azure.tcl")
        root.tk.call("set_theme", "dark")
    except:
        pass
    
    app = AuthControlPanel(root)
    root.mainloop()


if __name__ == "__main__":
    main()
