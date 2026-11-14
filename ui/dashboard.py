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
        # Track whether a play row is currently active in the stats database
        self._play_row_active = False
        self._polling = False
        self._poll_thread: Optional[threading.Thread] = None

        # Statistics (Slice 2.2)
        self._showing_stats = False
        self._stats: Optional[PlayStats] = None
        self._stats_reset_pending = False
        # Track last elapsed time for repeat-one detection
        self._last_elapsed: Optional[float] = None
        # Track last-seen duration for completed-vs-stopped classification
        self._last_duration: float = 0.0
        # Flag: playback restarted on same queue entry (repeat-one)
        self._playback_restarted = False
        # Flag: a seek is in progress; suppress restart detection on next poll
        self._seek_pending = False
        # Previous MPD playback state for transition detection
        self._prev_state: Optional[str] = None
        if config is not None:
            # Create PlayStats from config mapping via Config.get_all().
            # A corrupt database or unwritable directory must not prevent
            # the dashboard from opening.
            # Pass config_owner=self to persist the consumed stats.reset flag.
            try:
                self._stats = PlayStats.from_config(config.get_all(), config_owner=config)
            except Exception as e:
                logger.warning("PlayStats initialization failed: %s", e)
                self._stats = None

        # Build UI
        self._build_ui()

        # Update stats button visibility after UI is built
        self._update_stats_button_visibility()

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
        # Only show stats button when statistics are enabled
        if self._stats is not None and self._stats.enabled:
            self.stats_button.pack(side=tk.LEFT, padx=SPACING["sm"], pady=SPACING["sm"])
        else:
            self.stats_button.pack_forget()

        # Row 5: Status Label
        self.status_label = StatusLabel(self, text="Connecting…")
        self.status_label.grid(row=5, column=0, pady=SPACING["md"])

        # Row 6: Statistics frame (hidden by default)
        self._stats_frame = None
        self._stats_content = None

    # --- Event Handlers ---

    def _on_play_pause(self) -> None:
        """Toggle play/pause.

        Pausing does NOT end the play event: the same track may resume,
        and _update_ui() only calls record_play_start() when the file
        path changes. Closing the row here would leave the resumed
        listening unrecordable.
        """
        self.music_player.toggle_play()

    def _on_stop(self) -> None:
        """Stop playback."""
        success = self.music_player.stop()
        if success and self._stats is not None and self._stats.enabled:
            try:
                self._stats.record_play_end(completed=False)
                self._play_row_active = False
            except Exception:
                pass

    def _on_prev(self) -> None:
        """Previous track."""
        success = self.music_player.previous()
        if success and self._stats is not None and self._stats.enabled:
            try:
                self._stats.record_play_end(skipped=True)
                self._play_row_active = False
            except Exception:
                pass

    def _on_next(self) -> None:
        """Next track."""
        success = self.music_player.next()
        if success and self._stats is not None and self._stats.enabled:
            try:
                self._stats.record_play_end(skipped=True)
                self._play_row_active = False
            except Exception:
                pass

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
        # Mark a pending seek so that a dropped elapsed value on the next poll
        # is not misinterpreted as a play restart.
        self._seek_pending = True

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

    def _update_stats_button_visibility(self) -> None:
        """Show or hide stats button based on stats availability."""
        if self._stats is not None and self._stats.enabled:
            self.stats_button.pack(side=tk.LEFT, padx=SPACING["sm"], pady=SPACING["sm"])
        else:
            self.stats_button.pack_forget()

    def _toggle_stats(self) -> None:
        """Toggle between now-playing view and statistics screen."""
        # Don't open an empty Stats screen when statistics are disabled
        if self._stats is None or not self._stats.enabled:
            return
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
        self.stats_button.set_text("← Back")

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
        self.stats_button.set_text("📊")

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

        # Content frame with canvas for scrolling (mouse wheel + touch drag)
        stats_canvas = tk.Canvas(self._stats_frame, bg=COLORS["bg"], highlightthickness=0)
        v_scrollbar = tk.Scrollbar(self._stats_frame, orient=tk.VERTICAL, command=stats_canvas.yview)
        stats_canvas.configure(yscrollcommand=v_scrollbar.set)

        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        stats_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=SPACING["md"], pady=SPACING["md"])

        self._stats_content = tk.Frame(stats_canvas, bg=COLORS["bg"])
        stats_canvas.create_window((0, 0), window=self._stats_content, anchor="nw")

        # Update scroll region when content changes
        def _on_content_configure(event):
            stats_canvas.configure(scrollregion=stats_canvas.bbox("all"))

        self._stats_content.bind("<Configure>", _on_content_configure)

        # Mouse-wheel scrolling (desktop) and touch-drag scrolling (Pi touchscreen)
        def _on_wheel(event):
            # Windows/Linux: event.delta is a multiple of 120; macOS: small ints.
            step = -1 if event.delta > 0 else 1
            stats_canvas.yview_scroll(step, "units")

        def _on_drag_start(event):
            stats_canvas.scan_mark(event.x, event.y)

        def _on_drag_move(event):
            stats_canvas.scan_dragto(event.x, event.y, gain=1)

        stats_canvas.bind("<Enter>", lambda e: stats_canvas.bind_all("<MouseWheel>", _on_wheel))
        stats_canvas.bind("<Leave>", lambda e: stats_canvas.unbind_all("<MouseWheel>"))
        stats_canvas.bind("<ButtonPress-1>", _on_drag_start)
        stats_canvas.bind("<B1-Motion>", _on_drag_move)

        # Back button
        TouchButton(
            self._stats_frame,
            text="← Back",
            width=120,
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
            # Keys are (artist, album) tuples — format as "Artist - Album".
            album_text = "\n".join(
                [f"{a} - {al}: {c} plays" for (a, al), c in list(album_playcounts.items())[:5]]
            )
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
                else:
                    tk.Label(
                        self._stats_content,
                        text="Export failed: check disk space/permissions",
                        font=FONTS["status"],
                        fg=COLORS["danger"],
                        bg=COLORS["bg"],
                        justify=tk.LEFT,
                    ).pack(pady=SPACING["xs"])
            except Exception as e:
                logger.warning("CSV export failed: %s", e)

        TouchButton(
            self._stats_content,
            text="Export CSV",
            width=120,
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

    @staticmethod
    def _completion_threshold(duration: float) -> float:
        """Return the elapsed-seconds threshold at which a track counts as completed.

        Uses 90% of the track length, but never less than 2 seconds below the
        end and never below 1 second. The floor stops very short tracks
        (duration <= 2s) from being marked complete the instant they start.
        """
        if duration <= 0:
            return float("inf")  # unknown length: never auto-complete
        return max(1.0, min(duration * 0.9, duration - 2.0))

    def _maybe_cleanup(self) -> None:
        """Run PlayStats cleanup (close old open plays + enforce max size).

        Called after a play row is finalized, not on every poll, so the size
        prune runs only when a play actually ends.
        """
        if self._stats is None or not self._stats.enabled:
            return
        try:
            self._stats.cleanup()
        except Exception as e:
            logger.warning("stats cleanup failed: %s", e)

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

        # A failed get_status() returns state="unknown" with elapsed/duration 0.
        # Treat that poll as unusable rather than as a real stop: acting on it
        # would close the active row (and the next poll would reopen it),
        # splitting one play into two.
        if state == "unknown" and status.get("state") in (None, "unknown"):
            # Still refresh the status label, but leave all playback/stats
            # state untouched until a valid status reply arrives.
            self.status_label.set_state("unknown")
            return

# Check for song change
        song_file = song.get("file", "")
        previous_song = self._current_song
        previous_file = None if previous_song is None else previous_song.get("file", "")
        # Use MPD's queue-entry id to detect repeated plays of the same file.
        # `id` is present in currentsong() and changes even when `file` stays
        # the same (repeat-one / same file in consecutive queue entries).
        song_id = song.get("id") or song.get("file")
        previous_id = None if previous_song is None else (previous_song.get("id") or previous_song.get("file"))

        song_changed = song_id != previous_id
        # Unknown poll: get_current_song() returns {} when MPD fails or nothing
        # is playing. Keep the active row and _current_song as they are — an
        # empty reply is not evidence that the track ended.
        song_unknown = not bool(song_file)

        # Detect transitions into active playback (stopped/paused -> playing).
        prev_state = self._prev_state
        transition_into_play = (state == "playing" and prev_state != "playing")
        # A transition out of playing (or paused) into stopped ends the play even
        # when the queue entry is unchanged. Handle it explicitly so a stop from
        # another client finalizes the row as "stopped" (instead of being
        # misread as a restart/skip) and a later replay opens a fresh row.
        stopped_transition = (
            state in ("stopped", "unknown")
            and prev_state in ("playing", "paused")
            and not song_changed
        )

        # Detect repeat-one: same queue-entry ID but elapsed dropped sharply.
        # Suppress when a user-initiated seek is pending (a backward seek also
        # drops elapsed sharply).
        prev_elapsed = self._last_elapsed
        prev_duration = self._last_duration
        seek_pending = self._seek_pending
        # Consume the seek guard only once the background seek has been applied
        # and its resulting position has been observed.
        self._seek_pending = False
        if song_changed:
            self._playback_restarted = False
        elif seek_pending:
            # A seek caused the elapsed change, not a restart.
            self._playback_restarted = False
        elif song_id == previous_id and prev_elapsed is not None and prev_elapsed > 5:
            self._playback_restarted = elapsed < prev_elapsed * 0.5
        else:
            self._playback_restarted = False

        # Always update the baselines for the next poll.
        self._last_elapsed = elapsed
        self._last_duration = duration
        self._prev_state = state

        # Empty reply handling.
        if song_unknown:
            if state in ("playing", "paused"):
                return
            if self._current_song is not None or self._play_row_active:
                if self._play_row_active and self._stats is not None and self._stats.enabled:
                    completed = (
                        prev_elapsed is not None
                        and prev_duration > 0
                        and prev_elapsed >= self._completion_threshold(prev_duration)
                    )
                    try:
                        self._stats.record_play_end(completed=completed, skipped=False)
                    except Exception as e:
                        logger.warning("record_play_end failed: %s", e)
                    self._play_row_active = False
                    self._maybe_cleanup()
                self._current_song = None
                self._update_track_info({})
                self._art_fetch_thread = None
                self._art_fetch_target = None
                self.album_art.clear_art()
            return

        # Finalize the previous row when the queue entry changed, playback
        # restarted (repeat-one), or playback stopped while this entry was
        # still loaded.
        should_finalize = (
            song_changed or self._playback_restarted or stopped_transition
        ) and self._play_row_active
        if should_finalize and self._stats is not None and self._stats.enabled:
            completed = (
                prev_elapsed is not None
                and prev_duration > 0
                and prev_elapsed >= self._completion_threshold(prev_duration)
            )
            try:
                if stopped_transition:
                    self._stats.record_play_end(completed=completed, skipped=False)
                else:
                    self._stats.record_play_end(completed=completed, skipped=not completed)
            except Exception as e:
                logger.warning("record_play_end failed: %s", e)
            self._play_row_active = False
            self._maybe_cleanup()

        # Open a new row only when playback is actually active (state ==
        # "playing"). Stopped/paused tracks never open a row.
        should_open = (
            not self._play_row_active
            and bool(song_file)
            and state == "playing"
            and self._stats is not None
            and self._stats.enabled
            and (song_changed or self._playback_restarted or transition_into_play)
        )
        if should_open:
            song_for_stats = dict(song)
            if duration > 0:
                song_for_stats["duration"] = duration
            try:
                result = self._stats.record_play_start(song_for_stats)
                if result:
                    self._play_row_active = True
                self._playback_restarted = False
            except Exception as e:
                logger.warning("record_play_start failed: %s", e)

        # Track-display updates are tied to an actual song change only.
        if song_changed:
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
        if self._stats is not None:
            try:
                self._stats.cleanup()
            except Exception as e:
                logger.warning("stats cleanup failed: %s", e)
            try:
                self._stats.close()
            except Exception as e:
                logger.warning("stats close failed: %s", e)
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