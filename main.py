"""
Low-Resource Linux Music Player — Main Entry Point (Slice 1.5)

Bootstrap: creates MusicPlayer, Config, ArtworkCache and PluginManager,
then launches the Tkinter Dashboard.

Usage:
    python3 main.py
"""

import sys
import os
import time

# Ensure core package is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.player import MusicPlayer
from core.artwork import ArtworkCache
from core.config import Config
from plugins import PluginManager
from ui.dashboard import run_dashboard


def _get_mpd_music_dir(config: Config) -> str:
    """Get MPD music directory from config or default.

    Reads /etc/mpd.conf directly since `mpc config` is not a valid command.
    Falls back to default if config file is not found.
    """
    try:
        with open("/etc/mpd.conf", "r") as f:
            for line in f:
                line = line.strip()
                if line.startswith("music_directory"):
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


def main() -> int:
    """Entry point for Slice 1.5 — Tkinter Touch UI + Plugin System."""
    print("=" * 50)
    print("Low-Resource Linux Music Player")
    print("Slice 1.5: Tkinter Touch UI & Plugin System")
    print("=" * 50)

    # Load configuration
    config = Config()
    print(f"\nConfig loaded: {config.config_path}")

    # Connect to MPD (use settings from config)
    mpd_config = config.get("mpd", {})
    player = MusicPlayer(
        host=mpd_config.get("host", "localhost"),
        port=int(mpd_config.get("port", 6600)),
        timeout=float(mpd_config.get("timeout", 5.0)),
    )
    connected = player.connect()

    print(f"\nConnection status: {connected}")
    if not connected:
        print("❌ Could not connect to MPD. Is MPD running?")
        print("   On Pi: sudo systemctl start mpd")
        return 1

    # Create artwork cache
    cache = ArtworkCache(
        max_size_mb=config.get("cache.artwork_max_size_mb", 50),
    )
    print(f"Artwork cache ready: {cache.cache_dir}")

    # Create plugin manager
    plugin_mgr = PluginManager(core_engine=player, plugin_dir="plugins")
    plugin_mgr.load_plugins()
    print(f"Plugins loaded: {len(plugin_mgr.get_all_plugins())}")

    # Launch dashboard
    print("\nLaunching dashboard...")
    run_dashboard(
        music_player=player,
        artwork_cache=cache,
        config=config,
        fullscreen=config.get("ui.fullscreen", True),
    )

    # Cleanup
    plugin_mgr.shutdown_all()
    cache.close()
    player.disconnect()

    print("\n✅ Slice 1.5 test complete!")
    return 0


if __name__ == "__main__":
    sys.exit(main())