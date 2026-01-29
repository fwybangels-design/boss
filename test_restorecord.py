#!/usr/bin/env python3
"""
Test RestoreCord Configuration
Run this to verify your RestoreCord settings are correct
"""

import sys
import os

# Import from auth_handler
try:
    from auth_handler import (
        USE_RESTORECORD,
        RESTORECORD_URL,
        RESTORECORD_SERVER_ID,
        RESTORECORD_API_KEY,
        BOT_CLIENT_ID,
        AUTH_LINK,
        check_restorecord_verification
    )
    print("✅ Successfully imported auth_handler")
except ImportError as e:
    print(f"❌ Failed to import auth_handler: {e}")
    sys.exit(1)

print("\n" + "="*60)
print("  CONFIGURATION CHECK")
print("="*60)

# Check RestoreCord configuration
print("\n📋 RestoreCord Configuration:")
print(f"  URL: {RESTORECORD_URL or '❌ NOT SET'}")
print(f"  Server ID: {RESTORECORD_SERVER_ID or '❌ NOT SET'}")
print(f"  API Key: {'✅ SET' if RESTORECORD_API_KEY else '❌ NOT SET (may not be required)'}")
print(f"  Enabled: {'✅ YES' if USE_RESTORECORD else '❌ NO'}")

# Check Discord OAuth2 configuration
print("\n🔐 Discord OAuth2 Configuration:")
print(f"  Client ID: {BOT_CLIENT_ID or '❌ NOT SET'}")

# Show active auth method
print("\n🎯 Active Auth Method:")
if USE_RESTORECORD:
    print("  ✅ RestoreCord Verification")
    print(f"  Auth Link: {AUTH_LINK}")
elif BOT_CLIENT_ID:
    print("  ✅ Discord OAuth2 Bot Authorization")
    print(f"  Auth Link: {AUTH_LINK}")
else:
    print("  ⚠️  No auth method configured!")
    print("  You need to set either:")
    print("    - RestoreCord: RESTORECORD_URL + RESTORECORD_SERVER_ID")
    print("    - Discord OAuth2: BOT_CLIENT_ID")

# Test RestoreCord API if configured
if USE_RESTORECORD:
    print("\n" + "="*60)
    print("  TESTING RESTORECORD CONNECTION")
    print("="*60)
    
    test_user = input("\nEnter a Discord User ID to test (or press Enter to skip): ").strip()
    
    if test_user:
        print(f"\n🔍 Checking if user {test_user} is verified on RestoreCord...")
        try:
            is_verified = check_restorecord_verification(test_user)
            if is_verified:
                print(f"✅ User {test_user} IS verified on RestoreCord")
            else:
                print(f"❌ User {test_user} is NOT verified on RestoreCord")
        except Exception as e:
            print(f"❌ Error testing RestoreCord: {e}")
    else:
        print("⏭️  Skipping API test")

# Configuration instructions
print("\n" + "="*60)
print("  CONFIGURATION INSTRUCTIONS")
print("="*60)

if not USE_RESTORECORD and not BOT_CLIENT_ID:
    print("\n⚠️  You need to configure an auth method!")
    print("\nOption 1: RestoreCord")
    print("  1. Open auth_handler.py")
    print("  2. Set RESTORECORD_URL = 'https://your-restorecord-url.com'")
    print("  3. Set RESTORECORD_SERVER_ID = 'your_discord_server_id'")
    print("  4. Set RESTORECORD_API_KEY = 'your_api_key' (if required)")
    print("\nOption 2: Discord OAuth2")
    print("  1. Open auth_handler.py")
    print("  2. Set BOT_CLIENT_ID = 'your_discord_bot_client_id'")
    print("\nSee RESTORECORD_CONFIG.md for detailed instructions!")

elif USE_RESTORECORD:
    print("\n✅ RestoreCord is configured!")
    print("   Users will verify through RestoreCord")
    print("\nNext steps:")
    print("  1. Run: python meow_with_auth.py")
    print("  2. When users apply, they'll get the RestoreCord link")
    print("  3. Verified users are auto-accepted")

elif BOT_CLIENT_ID:
    print("\n✅ Discord OAuth2 is configured!")
    print("   Users will authorize via Discord OAuth2")
    print("\nNext steps:")
    print("  1. Set up OAuth2 redirect handling")
    print("  2. Run: python meow_with_auth.py")
    print("  3. Users authorize bot and get added to server")

print("\n" + "="*60)
print()
