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
from core.artwork import ArtworkCache, get_art


def _get_mpd_music_dir() -> str:
    """Get MPD music directory from config or default.

    Reads /etc/mpd.conf directly since `mpc config` is not a valid command.
    Falls back to default if config file is not found.
    """
    try:
        with open("/etc/mpd.conf", "r") as f:
            for line in f:
                line = line.strip()
                if line.startswith("music_directory"):
                    # Parse: music_directory "/mnt/nas/music"
                    parts = line.split('"')
                    if len(parts) >= 2:
                        return parts[1]
    except FileNotFoundError:
        pass
    # Fallback to default
    return "/mnt/nas/music"


def _resolve_song_path(song_file: str, music_dir: str) -> str:
    """Resolve a song file path against the MPD music directory.

    MPD returns file paths relative to the configured music_directory.
    Stream URLs (http://, https://, etc.) are returned unchanged.
    This function resolves relative paths to absolute filesystem paths.

    Args:
        song_file: Relative path from MPD (e.g., "Artist/Album/Track.flac")
        music_dir: Absolute path to MPD music directory

    Returns:
        Absolute filesystem path to the audio file, or stream URL unchanged
    """
    if not song_file:
        return ""
    # Skip stream URLs - they should not be resolved as local paths
    if song_file.startswith(("http://", "https://", "ftp://", "rtsp://")):
        return song_file
    # If already absolute, return as-is
    if os.path.isabs(song_file):
        return song_file
    # Resolve relative to music directory
    return os.path.join(music_dir, song_file)


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
    song = player.get_current_song() if connected else {}
    if song and song.get("file"):
        print(f"\nCurrent song: {song.get('artist', 'Unknown')} - {song.get('title', 'Unknown')}")

        # Resolve the song file path against MPD music directory
        music_dir = _get_mpd_music_dir()
        abs_file_path = _resolve_song_path(song["file"], music_dir)

        print(f"Resolved file path: {abs_file_path}")

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