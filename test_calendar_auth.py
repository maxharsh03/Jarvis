#!/usr/bin/env python3
"""Test Google Calendar authentication and event creation."""

import sys
import os
from datetime import datetime, timedelta

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tools.google_api import ensure_authenticated, create_calendar_event

def test_calendar_auth():
    """Test authentication."""
    print("🔐 Testing Google Calendar authentication...")
    
    if ensure_authenticated():
        print("✅ Google Calendar authentication successful!")
        return True
    else:
        print("❌ Google Calendar authentication failed.")
        print("   Make sure you have:")
        print("   1. credentials.json in the auth/ directory")
        print("   2. Proper Google Calendar API permissions")
        print("   3. Run the OAuth flow at least once")
        return False

def test_calendar_event_creation():
    """Test event creation."""
    print("\n📅 Testing calendar event creation...")
    
    # Create test event
    title = "Test Event from Jarvis"
    start_time = datetime.now() + timedelta(hours=1)
    end_time = start_time + timedelta(hours=1)
    description = "This is a test event created by Jarvis to verify calendar integration."
    
    success = create_calendar_event(title, start_time, end_time, description)
    
    if success:
        print(f"✅ Successfully created test event: {title}")
        print(f"   Scheduled for: {start_time.strftime('%Y-%m-%d %H:%M')}")
        return True
    else:
        print("❌ Failed to create calendar event")
        return False

if __name__ == "__main__":
    print("🤖 Jarvis Calendar Integration Test")
    print("=" * 40)
    
    # Test authentication
    auth_success = test_calendar_auth()
    
    if auth_success:
        # Test event creation
        event_success = test_calendar_event_creation()
        
        if event_success:
            print("\n🎉 All tests passed! Calendar integration is working.")
        else:
            print("\n⚠️  Authentication works but event creation failed.")
    else:
        print("\n❌ Authentication failed. Please check your setup.")
        print("\nTo fix this:")
        print("1. Make sure auth/credentials.json exists")
        print("2. Run: python tools/calendar_oauth.py")
        print("3. Complete the OAuth flow in your browser")