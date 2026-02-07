#!/bin/bash
# Launcher script for Auth RestoreCord Control Panel

echo "╔════════════════════════════════════════════════════════════╗"
echo "║      Auth RestoreCord Control Panel - Launcher           ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed!"
    echo "Please install Python 3 and try again."
    exit 1
fi

# Check if tkinter is available
if ! python3 -c "import tkinter" 2>/dev/null; then
    echo "⚠️  tkinter is not installed!"
    echo ""
    echo "Install it with:"
    echo "  Ubuntu/Debian: sudo apt-get install python3-tk"
    echo "  macOS: brew install python-tk@3.9"
    echo "  Windows: Usually included with Python"
    echo ""
    exit 1
fi

echo "✅ Python 3: $(python3 --version)"
echo "✅ tkinter: Available"
echo ""
echo "🚀 Launching Control Panel..."
echo ""

# Launch the control panel
python3 auth_control_panel.py

echo ""
echo "Control Panel closed."
