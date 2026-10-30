"""
MPD Connection & Basic Controls — Slice 1.1

Reliable MPD communication with automatic reconnection.
All MPD calls are wrapped in try/except — no exception propagates to UI.
"""

import time
from typing import Any, Dict, Optional
from mpd import MPDClient as LibMPDClient


class MusicPlayer:
    """MPD client wrapper with reconnection logic and safe command execution."""

    # Connection retry constants
    MAX_RETRIES = 10
    BASE_DELAY = 1.0  # seconds
    MAX_DELAY = 30.0  # seconds

    def __init__(self, host: str = "localhost", port: int = 6600, timeout: float = 5.0):
        """Initialize MusicPlayer with connection parameters.

        Args:
            host: MPD server hostname (default: localhost)
            port: MPD server port (default: 6600)
            timeout: Connection timeout in seconds (default: 5.0)
        """
        self.host = host
        self.port = port
        self.timeout = timeout
        self.client: Optional[LibMPDClient] = None
        self._connected = False
        self._last_known_state: Dict[str, Any] = {}

    def connect(self) -> bool:
        """Connect to MPD with exponential backoff retry logic.

        Returns:
            bool: True if connection succeeded, False after max retries
        """
        delay = self.BASE_DELAY
        last_exception = None

        for attempt in range(self.MAX_RETRIES):
            try:
                self.client = LibMPDClient()
                self.client.timeout = self.timeout
                self.client.connect(self.host, self.port)
                self._connected = True
                print(f"[MusicPlayer] Connected to MPD at {self.host}:{self.port}")
                return True
            except Exception as e:
                last_exception = e
                self._connected = False
                if self.client:
                    try:
                        self.client.close()
                        self.client.disconnect()
                    except Exception:
                        pass
                    self.client = None

                if attempt < self.MAX_RETRIES - 1:
                    print(f"[MusicPlayer] Connection attempt {attempt + 1} failed: {e}. Retrying in {delay:.1f}s...")
                    time.sleep(delay)
                    delay = min(delay * 2, self.MAX_DELAY)  # Exponential backoff
                else:
                    print(f"[MusicPlayer] Failed to connect after {self.MAX_RETRIES} attempts: {last_exception}")

        return False

    def _ensure_connected(self) -> bool:
        """Ensure we have a valid MPD connection, reconnecting if needed.

        Returns:
            bool: True if connected or reconnected, False otherwise
        """
        if self._connected and self.client:
            try:
                # Quick ping to verify connection
                self.client.ping()
                return True
            except Exception:
                self._connected = False

        return self.connect()

    def _execute_with_retry(self, command, *args, **kwargs) -> Any:
        """Execute an MPD command with one retry on failure.

        Attempts to run the provided MPD command once.
        If the command fails (raises an exception), reconnects to MPD
        and retries the command once before giving up.

        MPD commands return None on success and raise exceptions on failure.
        The result value is returned as-is (could be None for success).

        Args:
            command: Callable MPD command to execute
            *args: Positional arguments to pass to command
            **kwargs: Keyword arguments to pass to command

        Returns:
            Command execution result. MPD commands return None on success.
            Returns False if command could not be executed after reconnect.
            For playback control closures that return None on success,
            this method returns True to indicate success.
        """
        if not self._ensure_connected():
            return False

        try:
            result = command(*args, **kwargs)
            # MPD commands return None on success for control commands.
            # Return True for control success, otherwise return the actual result.
            if result is None:
                # Control command success (play, pause, etc.)
                return True
            # Query result — return as-is
            return result
        except Exception as e:
            print(f"[MusicPlayer] Command failed: {e}. Attempting reconnect...")
            # Try reconnect once
            if self.connect():
                try:
                    result = command(*args, **kwargs)
                    # Same logic: None means success for control commands
                    if result is None:
                        return True
                    return result
                except Exception as e2:
                    print(f"[MusicPlayer] Retry also failed: {e2}")
                    self._connected = False
            return False

    def is_connected(self) -> bool:
        """Check if currently connected to MPD.

        Returns:
            bool: True if connected, False otherwise
        """
        if not self._connected or not self.client:
            return False
        try:
            self.client.ping()
            return True
        except Exception:
            self._connected = False
            return False

    def get_status(self) -> Dict[str, Any]:
        """Get current MPD playback status.

        Returns:
            dict with keys: state, volume, elapsed, duration
            Returns safe defaults on failure
        """
        def _get_status():
            """Fetch raw status from MPD client."""
            return self.client.status() if self.client else {}

        result = self._execute_with_retry(_get_status)

        if result is False or result is None:
            # Return safe defaults
            return {
                "state": "unknown",
                "volume": "0",
                "elapsed": "0",
                "duration": "0",
            }

        # Normalize and cache
        self._last_known_state = {
            "state": result.get("state", "stop"),
            "volume": result.get("volume", "0"),
            "elapsed": result.get("elapsed", "0"),
            "duration": result.get("duration", "0"),
        }
        return self._last_known_state

    def get_current_song(self) -> Dict[str, Any]:
        """Get information about the currently playing song.

        Returns:
            dict with song metadata (artist, title, album, file, etc.)
            Returns empty dict on failure or if nothing is playing
        """
        def _get_song():
            """Fetch raw song metadata from MPD client."""
            return self.client.currentsong() if self.client else {}

        result = self._execute_with_retry(_get_song)

        if result is False or result is None:
            return {}

        if not isinstance(result, dict):
            return {}

        # Normalize keys - MPD returns various formats
        return {
            "artist": result.get("artist", ""),
            "title": result.get("title", ""),
            "album": result.get("album", ""),
            "file": result.get("file", ""),
            "time": result.get("time", ""),
            "track": result.get("track", ""),
            "genre": result.get("genre", ""),
            "date": result.get("date", ""),
        }

    def play(self) -> bool:
        """Start playback.

        Returns:
            bool: True if playback started successfully

        Internal:
            _do_play: Execute playback start command via MPD client.
                      Attempts to connect and send play command.
                      Returns True if MPD accepts the command.
        """
        def _do_play():
            """Execute MPD play command.

            Attempts to send play command to MPD client.
            Returns control to _execute_with_retry for result handling.
            """
            if self.client:
                self.client.play()
        return self._execute_with_retry(_do_play)

    def pause(self) -> bool:
        """Pause playback.

        Returns:
            bool: True if playback paused successfully

        Internal:
            _do_pause: Execute MPD pause command.
                       Attempts to send pause(1) command to MPD client.
                       Returns control to _execute_with_retry for result handling.
        """
        def _do_pause():
            """Execute MPD pause command.

            Attempts to send pause(1) command to MPD client.
            Returns control to _execute_with_retry for result handling.
            """
            if self.client:
                self.client.pause(1)
        return self._execute_with_retry(_do_pause)

    def toggle_play(self) -> bool:
        """Toggle between play and pause.

        Returns:
            bool: True if toggle succeeded

        Internal:
            _do_pause: If currently playing, send pause command.
            _do_play: If paused/stopped, send play command.
            Logic delegates to get_status() to determine current state.
        """
        status = self.get_status()
        if status.get("state") == "play":
            return self.pause()
        else:
            return self.play()

    def stop(self) -> bool:
        """Stop playback.

        Returns:
            bool: True if playback stopped successfully

        Internal:
            _do_stop: Execute MPD stop command.
        """
        def _do_stop():
            """Execute MPD stop command.

            Attempts to send stop command to MPD client.
            Returns control to _execute_with_retry for result handling.
            """
            if self.client:
                self.client.stop()
        return self._execute_with_retry(_do_stop)

    def next(self) -> bool:
        """Play next track in queue.

        Returns:
            bool: True if next track command succeeded

        Internal:
            _do_next: Execute MPD next command to move to next track.
        """
        def _do_next():
            """Execute MPD next command.

            Attempts to send next command to MPD client.
            Returns control to _execute_with_retry for result handling.
            """
            if self.client:
                self.client.next()
        return self._execute_with_retry(_do_next)

    def previous(self) -> bool:
        """Play previous track in queue.

        Returns:
            bool: True if previous command succeeded

        Internal:
            _do_previous: Execute MPD previous command.
        """
        def _do_previous():
            """Execute MPD previous command.

            Attempts to send previous command to MPD client.
            Returns control to _execute_with_retry for result handling.
            """
            if self.client:
                self.client.previous()
        return self._execute_with_retry(_do_previous)

    def set_volume(self, level: int) -> bool:
        """Set playback volume.

        Args:
            level: Volume level 0-100

        Returns:
            bool: True if volume set successfully

        Internal:
            _do_setvol: Execute MPD setvol command.
        """
        level = max(0, min(100, level))  # Clamp to valid range
        def _do_setvol():
            """Execute MPD setvol command to set playback volume.

            Attempts to send volume level to MPD client.
            Returns control to _execute_with_retry for result handling.
            """
            if self.client:
                self.client.setvol(level)
        return self._execute_with_retry(_do_setvol)

    def seek(self, position: float) -> bool:
        """Seek to position in current track (seconds).

        Args:
            position: Time in seconds from start of track

        Returns:
            bool: True if seek command succeeded

        Internal:
            _do_seek: Execute MPD seekcur command to seek.
        """
        def _do_seek():
            """Execute MPD seekcur command to seek to position.

            Attempts to send seek command to MPD client.
            Returns control to _execute_with_retry for result handling.
            """
            if self.client:
                self.client.seekcur(int(position))
        return self._execute_with_retry(_do_seek)

    def get_playlist(self) -> list:
        """Get current playlist.

        Returns:
            List of song dicts, empty list on failure
        """
        def _get_playlist():
            """Fetch current playlist from MPD client."""
            if self.client:
                return self.client.playlistinfo()
            return []

        result = self._execute_with_retry(_get_playlist)
        if result is False:
            return []
        return result or []

    def add_to_playlist(self, path: str) -> bool:
        """Add a track or directory to playlist.

        Args:
            path: Path relative to MPD music directory

        Returns:
            bool: True if add command succeeded
        """
        def _do_add():
            """Execute MPD add command.

            Attempts to add track/directory to MPD playlist.
            Returns control to _execute_with_retry for result handling.
            """
            if self.client:
                self.client.add(path)
        return self._execute_with_retry(_do_add)

    def clear_playlist(self) -> bool:
        """Clear the current playlist.

        Returns:
            bool: True if clear command succeeded
        """
        def _do_clear():
            """Execute MPD clear command to clear playlist.

            Attempts to send clear command to MPD client.
            Returns control to _execute_with_retry for result handling.
            """
            if self.client:
                self.client.clear()
        return self._execute_with_retry(_do_clear)


# Import-friendly alias for backward compatibility
# Note: MPDClient refers to the external library class (imported as LibMPDClient)
# MusicPlayer is the wrapper class
__all__ = ['MusicPlayer', 'LibMPDClient']