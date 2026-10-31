"""
Low-Resource Linux Music Player — Main Entry Point (Slice 1.2)

Minimal bootstrap. Core engine and UI come later per phase plan.
For now: test MPD connection and album art extraction.
"""

import sys
import os
import time

# Ensure core package is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.player import MusicPlayer
from core.artwork import ArtworkCache


def main():
    """Entry point for Slice 1.2 testing."""
    print("=" * 50)
    print("Low-Resource Linux Music Player")
    print("Slice 1.2: Album Art Handler")
    print("=" * 50)

    # Connect to MPD
    player = MusicPlayer()
    connected = player.connect()

    print(f"\nConnection status: {connected}")

    # Test album art extraction
    print("\n--- Album Art Test ---")
    cache = ArtworkCache(max_size_mb=5)

    # Get current song's art
    song = player.get_current_song()
    if song and song.get("file"):
        print(f"\nCurrent song: {song.get('artist', 'Unknown')} - {song.get('title', 'Unknown')}")

        # Resolve the song file path against MPD music directory
        music_dir = _get_mpd_music_dir(player)
        abs_file_path = _resolve_song_path(song["file"], music_dir)

        print(f"Resolved file path: {abs_file_path}")

        art_path = None
        if os.path.exists(abs_file_path):
            art_path = cache.get_art(abs_file_path)
        if art_path:
            print(f"Album art: {art_path}")
            print(f"  Size: {os.path.getsize(art_path)} bytes")
        else:
            print("No album art found for current track")
    else:
        print("No song currently playing")

    # Test MPD playback
    if connected:
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

    print("\n✅ Slice 1.2 test complete!")
    return 0


if __name__ == "__main__":
    sys.exit(main())