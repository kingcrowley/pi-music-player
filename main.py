"""
Low-Resource Linux Music Player — Main Entry Point (Slice 1.1)

Minimal bootstrap. Core engine and UI come later per phase plan.
For now: test MPD connection and basic playback.
"""

import sys
import os
import time

# Ensure core package is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.player import MusicPlayer


def main():
    """Entry point for Slice 1.1 testing."""
    print("=" * 50)
    print("Low-Resource Linux Music Player")
    print("Slice 1.1: MPD Connection & Basic Controls")
    print("=" * 50)

    # Connect to MPD
    player = MusicPlayer()

    print(f"\nConnection status: {player.is_connected()}")

    # Test commands (only if connected)
    if player.is_connected():
        print("\nCurrent status:", player.get_status())
        print("Current song:", player.get_current_song())

        input("\nPress Enter to toggle play...")
        player.toggle_play()
        time.sleep(2)
        print("Status after toggle:", player.get_status()["state"])

        input("Press Enter to go to next track...")
        player.next()
        time.sleep(1)
        print("Next song:", player.get_current_song())

        player.set_volume(50)
        print("Volume set to:", player.get_status()["volume"])

        input("Press Enter to stop playback...")
        player.stop()
        print("Final status:", player.get_status())
    else:
        print("❌ Could not connect to MPD. Is MPD running?")
        print("   On Pi: sudo systemctl start mpd")
        return 1

    print("\n✅ Slice 1.1 test complete!")
    return 0


if __name__ == "__main__":
    sys.exit(main())