"""Tkinter touch dashboard for low-RAM Pi Zero 2 W music player.

Main window with album art, track info, playback controls, volume, progress bar,
and status indicator. Polls MPD every 1s and updates UI via root.after().
"""

import logging
import os
import threading
import time
import tkinter as tk
from typing import Optional, Dict, Any

from core.config import Config
from core.player import MusicPlayer
from core.artwork import ArtworkCache
from core.stats import PlayStats
from ui.styles import COLORS, FONTS, SPACING, WINDOW, TOUCH_TARGET_SIZE
from ui.widget import (
    TouchButton,
    ProgressBar,
    AlbumArtLabel,
    VolumeSlider,
    StatusLabel,
)


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


logger = logging.getLogger(__name__)


class Dashboard(tk.Tk):
    """Main touch dashboard window for music playback control.

    Polls MPD every 1s via background thread, updates UI via root.after().
    """

    def __init__(
        self,
        music_player: MusicPlayer,
        artwork_cache: ArtworkCache,
        config: Config,
        fullscreen: bool = True,
    ):
        super().__init__()

        self.music_player = music_player
        self.artwork_cache = artwork_cache
        self.config = config

        # Window setup
        self.title("Music Player")
        self.configure(bg=COLORS["bg"])
        if fullscreen:
            self.attributes("-fullscreen", True)
        else:
            self.geometry(f"{WINDOW['width']}x{WINDOW['height']}")

        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # State
        self._current_song: Optional[Dict[str, Any]] = None
        self._current_art = None
        self._art_fetch_thread: Optional[threading.Thread] = None
        # Track the file path of the song currently being fetched to reject stale completions
        self._art_fetch_target: Optional[str] = None
        self._polling = False
        self._poll_thread: Optional[threading.Thread] = None

        # Statistics (Slice 2.2)
        self._showing_stats = False
        self._stats: Optional[PlayStats] = None
        if config is not None:
            # Create PlayStats from config if available
            self._stats = PlayStats.from_config(config.config)

        # Build UI
        self._build_ui()

        # Start polling
        self._start_poll_loop()

    def _build_ui(self) -> None:
        """Build the main UI layout."""
        # Configure grid weights
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=3)  # album art area
        self.grid_rowconfigure(1, weight=0)  # track info
        self.grid_rowconfigure(2, weight=0)  # progress bar
        self.grid_rowconfigure(3, weight=0)  # time + volume
        self.grid_rowconfigure(4, weight=0)  # playback controls
        self.grid_rowconfigure(5, weight=0)  # status
        self.grid_rowconfigure(6, weight=0)  # stats (hidden by default)

        # Row 0: Album Art (center)
        self.album_art = AlbumArtLabel(self, size=300)
        self.album_art.grid(row=0, column=0, pady=(SPACING["xl"], SPACING["md"]))

        # Row 1: Track Info
        self.info_frame = tk.Frame(self, bg=COLORS["bg"])
        self.info_frame.grid(row=1, column=0, pady=SPACING["sm"])
        self.info_frame.grid_columnconfigure(0, weight=1)

        self.title_label = tk.Label(
            self.info_frame,
            text="No Track",
            font=FONTS["title"],
            fg=COLORS["fg"],
            bg=COLORS["bg"],
            wraplength=600,
        )
        self.title_label.pack(pady=SPACING["xs"])

        self.artist_label = tk.Label(
            self.info_frame,
            text="",
            font=FONTS["artist"],
            fg=COLORS["fg"],
            bg=COLORS["bg"],
            wraplength=600,
        )
        self.artist_label.pack(pady=SPACING["xs"])

        self.album_label = tk.Label(
            self.info_frame,
            text="",
            font=FONTS["album"],
            fg=COLORS["muted"],
            bg=COLORS["bg"],
            wraplength=600,
        )
        self.album_label.pack(pady=SPACING["xs"])

        # Row 2: Progress Bar
        self.progress_bar = ProgressBar(self, width=600, height=24)
        self.progress_bar.grid(row=2, column=0, pady=SPACING["md"])
        self.progress_bar.set_seek_callback(self._on_seek)

        # Row 3: Time + Volume
        self.time_volume_frame = tk.Frame(self, bg=COLORS["bg"])
        self.time_volume_frame.grid(row=3, column=0, pady=SPACING["sm"])
        self.time_volume_frame.grid_columnconfigure(1, weight=1)

        self.elapsed_label = tk.Label(
            self.time_volume_frame,
            text="00:00",
            font=FONTS["time"],
            fg=COLORS["fg"],
            bg=COLORS["bg"],
        )
        self.elapsed_label.grid(row=0, column=0, padx=SPACING["md"])

        self.volume_slider = VolumeSlider(
            self.time_volume_frame,
            orientation="horizontal",
            width=300,
            height=24,
        )
        self.volume_slider.set_volume_callback(self._on_volume_change)
        self.volume_slider.grid(row=0, column=1, padx=SPACING["md"])

        self.duration_label = tk.Label(
            self.time_volume_frame,
            text="00:00",
            font=FONTS["time"],
            fg=COLORS["fg"],
            bg=COLORS["bg"],
        )
        self.duration_label.grid(row=0, column=2, padx=SPACING["md"])

        # Row 4: Playback Controls
        self.controls_frame = tk.Frame(self, bg=COLORS["bg"])
        self.controls_frame.grid(row=4, column=0, pady=SPACING["lg"])

        self.prev_button = TouchButton(
            self.controls_frame,
            text="⏮",
            command=self._on_prev,
        )
        self.prev_button.pack(side=tk.LEFT, padx=SPACING["sm"], pady=SPACING["sm"])

        self.play_pause_button = TouchButton(
            self.controls_frame,
            text="▶",
            command=self._on_play_pause,
        )
        self.play_pause_button.pack(side=tk.LEFT, padx=SPACING["sm"], pady=SPACING["sm"])

        self.stop_button = TouchButton(
            self.controls_frame,
            text="⏹",
            command=self._on_stop,
        )
        self.stop_button.pack(side=tk.LEFT, padx=SPACING["sm"], pady=SPACING["sm"])

        self.next_button = TouchButton(
            self.controls_frame,
            text="⏭",
            command=self._on_next,
        )
        self.next_button.pack(side=tk.LEFT, padx=SPACING["sm"], pady=SPACING["sm"])

        self.stats_button = TouchButton(
            self.controls_frame,
            text="📊",
            command=self._toggle_stats,
        )
        self.stats_button.pack(side=tk.LEFT, padx=SPACING["sm"], pady=SPACING["sm"])

        # Row 5: Status Label
        self.status_label = StatusLabel(self, text="Connecting…")
        self.status_label.grid(row=5, column=0, pady=SPACING["md"])

        # Row 6: Statistics frame (hidden by default)
        self._stats_frame = None
        self._stats_content = None

    # --- Event Handlers ---

    def _on_play_pause(self) -> None:
        """Toggle play/pause."""
        self.music_player.toggle_play()

    def _on_stop(self) -> None:
        """Stop playback."""
        self.music_player.stop()

    def _on_prev(self) -> None:
        """Previous track."""
        self.music_player.previous()

    def _on_next(self) -> None:
        """Next track."""
        self.music_player.next()

    def _on_volume_change(self, volume: float) -> None:
        """Handle volume slider changes."""
        self.music_player.set_volume(int(volume * 100))

    def _on_seek(self, fraction: float) -> None:
        """Handle progress bar seek.

        Dispatch the seek to a background thread so MPD connection retries
        do not block the Tk event handler. The seek effect is immediate via
        MPD; UI is refreshed on the next poll iteration.
        """

        def _seek() -> None:
            try:
                status = self.music_player.get_status()
                duration = float(status.get("duration", 0))
                if duration > 0:
                    target_seconds = fraction * duration
                    self.music_player.seek(target_seconds)
            except Exception as e:
                logger.warning("Seek error: %s", e)
            # Schedule UI refresh on Tk thread
            self.after(0, self._refresh_ui)

        thread = threading.Thread(target=_seek, daemon=True)
        thread.start()

    def _refresh_ui(self) -> None:
        """Refresh UI on Tk thread after a background seek."""
        # Force a poll to pick up the new position immediately.
        try:
            status = self.music_player.get_status()
            song = self.music_player.get_current_song()
            self._update_ui(status, song)
        except Exception as e:
            logger.warning("Refresh error: %s", e)

    # --- Statistics Screen (Slice 2.2) ---

    def _toggle_stats(self) -> None:
        """Toggle between now-playing view and statistics screen."""
        self._showing_stats = not self._showing_stats
        if self._showing_stats:
            self._show_stats_view()
        else:
            self._show_now_playing_view()

    def _show_stats_view(self) -> None:
        """Show stats view, hide now-playing widgets."""
        # Hide now-playing widgets
        self.album_art.grid_remove()
        self.info_frame.grid_remove()
        self.progress_bar.grid_remove()
        self.time_volume_frame.grid_remove()
        self.controls_frame.grid_remove()
        self.status_label.grid_remove()
        self.stats_button.config(text="← Back")

        # Create stats frame if needed
        if self._stats_frame is None:
            self._create_stats_frame()
        else:
            self._stats_frame.grid()

        self._refresh_stats_content()

    def _show_now_playing_view(self) -> None:
        """Show now-playing widgets, hide stats."""
        self.album_art.grid()
        self.info_frame.grid()
        self.progress_bar.grid()
        self.time_volume_frame.grid()
        self.controls_frame.grid()
        self.status_label.grid()
        self.stats_button.config(text="📊")

        # Hide stats frame
        if self._stats_frame is not None:
            self._stats_frame.grid_remove()

    def _create_stats_frame(self) -> None:
        """Create the stats frame with all stats content."""
        if self._stats is None:
            return

        self._stats_frame = tk.Frame(self, bg=COLORS["bg"])
        self._stats_frame.grid(row=6, column=0, columnspan=1, pady=SPACING["lg"], padx=SPACING["md"], sticky="nsew")

        # Title
        tk.Label(
            self._stats_frame,
            text="📊 Play Statistics",
            font=FONTS["title"],
            fg=COLORS["fg"],
            bg=COLORS["bg"],
        ).pack(pady=SPACING["sm"])

        # Content frame
        self._stats_content = tk.Frame(self._stats_frame, bg=COLORS["bg"])
        self._stats_content.pack(fill=tk.BOTH, expand=True, padx=SPACING["md"], pady=SPACING["md"])

        # Back button
        TouchButton(
            self._stats_frame,
            text="← Back",
            command=self._toggle_stats,
        ).pack(side=tk.BOTTOM, pady=SPACING["sm"])

    def _refresh_stats_content(self) -> None:
        """Refresh stats content with latest data."""
        if self._stats is None or self._stats_content is None:
            return

        # Clear existing content
        for widget in self._stats_content.winfo_children():
            widget.destroy()

        # Top Artists
        artist_playcounts = self._stats.get_artist_playcounts()
        if artist_playcounts:
            artist_text = "\n".join([f"{a}: {c} plays" for a, c in list(artist_playcounts.items())[:5]])
            tk.Label(
                self._stats_content,
                text="Top Artists\n" + artist_text,
                font=FONTS["artist"],
                fg=COLORS["fg"],
                bg=COLORS["bg"],
                justify=tk.LEFT,
                wraplength=400,
            ).pack(pady=SPACING["xs"], anchor=tk.W)

        # Top Albums
        album_playcounts = self._stats.get_album_playcounts()
        if album_playcounts:
            album_text = "\n".join([f"{a}: {c} plays" for a, c in list(album_playcounts.items())[:5]])
            tk.Label(
                self._stats_content,
                text="Top Albums\n" + album_text,
                font=FONTS["album"],
                fg=COLORS["fg"],
                bg=COLORS["bg"],
                justify=tk.LEFT,
                wraplength=400,
            ).pack(pady=SPACING["xs"], anchor=tk.W)

        # Skip Rate
        skip_rates = self._stats.get_skip_rate()
        if skip_rates:
            skip_text = "\n".join([f"{a}: {r:.0f}%" for a, r in list(skip_rates.items())[:5]])
            tk.Label(
                self._stats_content,
                text="Skip Rate\n" + skip_text,
                font=FONTS["status"],
                fg=COLORS["fg"],
                bg=COLORS["bg"],
                justify=tk.LEFT,
                wraplength=400,
            ).pack(pady=SPACING["xs"], anchor=tk.W)

        # Listening Time Heatmap
        heatmap = self._stats.get_listening_time_heatmap()
        if heatmap:
            heatmap_text = "Listening Time (by day/hour)\n"
            day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            for day_idx in range(7):
                if heatmap[day_idx]:
                    hours = ", ".join([f"{h}:00={m}min" for h, m in sorted(heatmap[day_idx].items())])
                    heatmap_text += f"{day_names[day_idx]}: {hours}\n"
            tk.Label(
                self._stats_content,
                text=heatmap_text,
                font=FONTS["status"],
                fg=COLORS["fg"],
                bg=COLORS["bg"],
                justify=tk.LEFT,
                wraplength=400,
            ).pack(pady=SPACING["xs"], anchor=tk.W)

        # Export CSV button
        def _export_csv():
            try:
                csv_path = self._stats.export_csv()
                if csv_path:
                    tk.Label(
                        self._stats_content,
                        text=f"Exported to: {csv_path}",
                        font=FONTS["status"],
                        fg=COLORS["warning"],
                        bg=COLORS["bg"],
                        justify=tk.LEFT,
                    ).pack(pady=SPACING["xs"])
            except Exception as e:
                logger.warning("CSV export failed: %s", e)

        TouchButton(
            self._stats_content,
            text="Export CSV",
            command=_export_csv,
        ).pack(side=tk.TOP, pady=SPACING["sm"])

    # --- Polling Loop ---

    def _start_poll_loop(self) -> None:
        """Start background polling thread."""
        self._polling = True
        self._poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._poll_thread.start()

    def _poll_loop(self) -> None:
        """Background thread that polls MPD every 1 second."""
        while self._polling:
            try:
                self._fetch_and_schedule_update()
            except Exception as e:
                logger.warning("Poll loop error: %s", e)
            time.sleep(1.0)

    def _fetch_and_schedule_update(self) -> None:
        """Fetch MPD status and schedule UI update on main thread."""
        try:
            status = self.music_player.get_status()
            song = self.music_player.get_current_song()
            self.after(0, lambda: self._update_ui(status, song))
        except Exception as e:
            logger.warning("Fetch error: %s", e)

    @staticmethod
    def _map_mpd_state(state: str) -> str:
        """Map MPD state strings to StatusLabel state names.

        MPD uses: play, pause, stopped (and others like play, pause, stop)
        StatusLabel accepts: playing, paused, stopped, connecting, unknown
        """
        mapping = {
            "play": "playing",
            "pause": "paused",
            "stop": "stopped",
            "stopped": "stopped",
            "pause": "paused",
            "play": "playing",
        }
        return mapping.get(state, "unknown")

    def _update_ui(self, status: Dict[str, Any], song: Dict[str, Any]) -> None:
        """Update UI elements on main thread."""
        # Update status
        state = self._map_mpd_state(status.get("state", "unknown"))
        self.status_label.set_state(state)

        # Update play/pause button
        if state == "playing":
            self.play_pause_button.set_text("⏸")
            self.status_label.set_state("playing")
        elif state == "paused":
            self.play_pause_button.set_text("▶")
            self.status_label.set_state("paused")
        else:
            self.play_pause_button.set_text("▶")
            self.status_label.set_state("stopped")

        # Update volume
        volume = int(status.get("volume", 0))
        self.volume_slider.set_volume(volume / 100.0)

        # Update progress bar
        elapsed = float(status.get("elapsed", 0))
        duration = float(status.get("duration", 0))
        if duration > 0:
            self.progress_bar.set_progress(elapsed / duration)
        else:
            self.progress_bar.set_progress(0.0)

        # Update time labels
        self.elapsed_label.config(text=self._format_time(elapsed))
        self.duration_label.config(text=self._format_time(duration))

        # Check for song change
        song_file = song.get("file", "")
        previous_file = None if self._current_song is None else self._current_song.get("file", "")
        if song_file != previous_file:
            self._current_song = song
            self._update_track_info(song)
            self._fetch_album_art(song)

    def _format_time(self, seconds: float) -> str:
        """Format seconds as MM:SS or HH:MM:SS."""
        seconds = int(seconds)
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        if hours > 0:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        return f"{minutes}:{secs:02d}"

    def _update_track_info(self, song: Dict[str, Any]) -> None:
        """Update track info labels."""
        self.title_label.config(text=song.get("title", "Unknown"))
        self.artist_label.config(text=song.get("artist", "Unknown Artist"))
        self.album_label.config(text=song.get("album", "Unknown Album"))

    def _fetch_album_art(self, song: Dict[str, Any]) -> None:
        """Fetch album art in background thread.

        Retains the latest track's request while a fetch is active.
        When a fetch completes, rejects the result if the track no longer
        matches _current_song, then starts a new fetch for the current track.
        """
        file_path = song.get("file", "")
        if not file_path:
            self.after(0, self.album_art.clear_art)
            return

        # If a fetch is already in progress, update the target to the latest song
        # and let the current fetch complete (it will be rejected on completion)
        if self._art_fetch_thread and self._art_fetch_thread.is_alive():
            self._art_fetch_target = file_path
            return

        # No active fetch - start a new one for this song
        self._art_fetch_target = file_path

        def fetch_art():
            target_path = file_path
            if not target_path:
                self.after(0, self.album_art.clear_art)
                return

            # Resolve absolute path using core.player._resolve_song_path logic
            music_dir = _get_mpd_music_dir(self.config)
            abs_file_path = _resolve_song_path(target_path, music_dir)

            art_path = self.artwork_cache.get_art(abs_file_path)
            if art_path:
                try:
                    from PIL import Image, ImageTk
                    img = Image.open(art_path)
                    img = img.resize((300, 300), Image.Resampling.LANCZOS)
                    photo = ImageTk.PhotoImage(img)
                    # Only apply if this is still the current track
                    self.after(0, lambda: self._on_art_fetched(target_path, photo))
                except Exception as e:
                    logger.warning("Failed to load album art: %s", e)
                    self.after(0, lambda: self._on_art_fetched(target_path, None))
            else:
                self.after(0, lambda: self._on_art_fetched(target_path, None))

        self._art_fetch_thread = threading.Thread(target=fetch_art, daemon=True)
        self._art_fetch_thread.start()

    def _on_art_fetched(self, fetched_path: str, photo: Optional[object]) -> None:
        """Handle completion of an artwork fetch.

        Rejects the result if the fetched track no longer matches _current_song.
        If rejected and there's a newer pending target, starts a fetch for that.
        """
        current_path = self._current_song.get("file", "") if self._current_song else ""
        if fetched_path != current_path:
            # Stale fetch - discard and check if we should start a new one
            if self._art_fetch_target and self._art_fetch_target != fetched_path:
                # Clear the worker handle so the new fetch's is_alive() guard
                # in _fetch_album_art doesn't block because A's thread is
                # still alive while we're in its completion callback.
                self._art_fetch_thread = None
                # There's a newer target pending - start fetch for it
                self._fetch_album_art({"file": self._art_fetch_target})
            return

        # Fresh result for current track
        if photo:
            self.album_art.set_art(photo)
        else:
            self.album_art.clear_art()

    def _on_close(self) -> None:
        """Handle window close."""
        self._polling = False
        if self._poll_thread:
            self._poll_thread.join(timeout=2.0)
        self.destroy()


def run_dashboard(
    music_player: MusicPlayer,
    artwork_cache: ArtworkCache,
    config: Config,
    fullscreen: bool = True,
) -> None:
    """Create and run the dashboard."""
    app = Dashboard(music_player, artwork_cache, config, fullscreen)
    app.mainloop()


__all__ = ["Dashboard", "run_dashboard"]