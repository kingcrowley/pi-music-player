"""Tkinter touch dashboard for low-RAM Pi Zero 2 W music player.

Main window with album art, track info, playback controls, volume, progress bar,
and status indicator. Polls MPD every 1s and updates UI via root.after().
"""

import logging
import threading
import time
import tkinter as tk
from typing import Optional, Dict, Any

from core.config import Config
from core.player import MusicPlayer
from core.artwork import ArtworkCache
from ui.styles import COLORS, FONTS, SPACING, WINDOW
from ui.widget import (
    TouchButton,
    ProgressBar,
    AlbumArtLabel,
    VolumeSlider,
    StatusLabel,
)

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
        self._polling = False
        self._poll_thread: Optional[threading.Thread] = None

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

        # Row 0: Album Art (center)
        self.album_art = AlbumArtLabel(self, size=300)
        self.album_art.grid(row=0, column=0, pady=(SPACING["xl"], SPACING["md"]))

        # Row 1: Track Info
        info_frame = tk.Frame(self, bg=COLORS["bg"])
        info_frame.grid(row=1, column=0, pady=SPACING["sm"])
        info_frame.grid_columnconfigure(0, weight=1)

        self.title_label = tk.Label(
            info_frame,
            text="No Track",
            font=FONTS["title"],
            fg=COLORS["fg"],
            bg=COLORS["bg"],
            wraplength=600,
        )
        self.title_label.pack(pady=SPACING["xs"])

        self.artist_label = tk.Label(
            info_frame,
            text="",
            font=FONTS["artist"],
            fg=COLORS["fg"],
            bg=COLORS["bg"],
            wraplength=600,
        )
        self.artist_label.pack(pady=SPACING["xs"])

        self.album_label = tk.Label(
            info_frame,
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
        time_volume_frame = tk.Frame(self, bg=COLORS["bg"])
        time_volume_frame.grid(row=3, column=0, pady=SPACING["sm"])
        time_volume_frame.grid_columnconfigure(1, weight=1)

        self.elapsed_label = tk.Label(
            time_volume_frame,
            text="00:00",
            font=FONTS["time"],
            fg=COLORS["fg"],
            bg=COLORS["bg"],
        )
        self.elapsed_label.grid(row=0, column=0, padx=SPACING["md"])

        self.volume_slider = VolumeSlider(
            time_volume_frame,
            orientation="horizontal",
            width=300,
            height=24,
        )
        self.volume_slider.set_volume_callback(self._on_volume_change)
        self.volume_slider.grid(row=0, column=1, padx=SPACING["md"])

        self.duration_label = tk.Label(
            time_volume_frame,
            text="00:00",
            font=FONTS["time"],
            fg=COLORS["fg"],
            bg=COLORS["bg"],
        )
        self.duration_label.grid(row=0, column=2, padx=SPACING["md"])

        # Row 4: Playback Controls
        controls_frame = tk.Frame(self, bg=COLORS["bg"])
        controls_frame.grid(row=4, column=0, pady=SPACING["lg"])

        btn_config = {
            "width": TOUCH_TARGET_SIZE,
            "height": TOUCH_TARGET_SIZE,
            "font": FONTS["button"],
            "bg": COLORS["card_bg"],
            "fg": COLORS["fg"],
            "active_bg": COLORS["accent"],
        }

        self.prev_button = TouchButton(
            self,
            text="⏮",
            command=self._on_prev,
            **{k: v for k, v in {"width": TOUCH_TARGET_SIZE, "height": TOUCH_TARGET_SIZE}.items()},
        )
        self.prev_button._normal_bg = COLORS["card_bg"]
        self.prev_button._normal_fg = COLORS["fg"]
        self.prev_button._active_bg = COLORS["accent"]
        self.prev_button._active_fg = COLORS["fg"]
        self.prev_button._text_id = self.prev_button.create_text(
            TOUCH_TARGET_SIZE // 2,
            TOUCH_TARGET_SIZE // 2,
            text="⏮",
            font=FONTS["button"],
            fill=COLORS["fg"],
            anchor="center",
        )
        self.prev_button.config(bg=COLORS["card_bg"], highlightthickness=0)
        self.prev_button.itemconfig(self.prev_button._text_id, text="⏮", fill=COLORS["fg"])
        self.prev_button.pack(side=tk.LEFT, padx=SPACING["sm"], pady=SPACING["sm"])

        self.play_pause_button = TouchButton(
            self,
            text="▶",
            command=self._on_play_pause,
        )
        self.play_pause_button.pack(side=tk.LEFT, padx=SPACING["sm"], pady=SPACING["sm"])

        self.stop_button = TouchButton(
            self,
            text="⏹",
            command=self._on_stop,
        )
        self.stop_button.pack(side=tk.LEFT, padx=SPACING["sm"], pady=SPACING["sm"])

        self.next_button = TouchButton(
            self,
            text="⏭",
            command=self._on_next,
        )
        self.next_button.pack(side=tk.LEFT, padx=SPACING["sm"], pady=SPACING["sm"])

        # Row 5: Status Label
        self.status_label = StatusLabel(self, text="Connecting…")
        self.status_label.grid(row=5, column=0, pady=SPACING["md"])

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
        """Handle progress bar seek."""
        if self._current_song and self._current_song.get("duration"):
            duration_ms = self._current_song.get("duration", 0)
            if duration_ms > 0:
                target_ms = int(fraction * duration_ms)
                self.music_player.seek(target_ms / 1000.0)

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

    def _update_ui(self, status: Dict[str, Any], song: Dict[str, Any]) -> None:
        """Update UI elements on main thread."""
        # Update status
        state = status.get("state", "unknown")
        self.status_label.set_state(state)

        # Update play/pause button
        if state == "play":
            self.play_pause_button.set_text("⏸")
        else:
            self.play_pause_button.set_text("▶")

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
        if song_file != self._current_song.get("file", "") if self._current_song else True:
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
        """Fetch album art in background thread."""
        if self._art_fetch_thread and self._art_fetch_thread.is_alive():
            return

        def fetch_art():
            file_path = song.get("file", "")
            if not file_path:
                self.after(0, lambda: self.album_art._draw_placeholder())
                return

            # Resolve absolute path
            from core.player import MusicPlayer
            # We need to resolve the path relative to MPD music directory
            # For now, assume the cache can handle it
            art_path = self.artwork_cache.get_art(file_path)
            if art_path:
                try:
                    from PIL import Image, ImageTk
                    img = Image.open(art_path)
                    img = img.resize((300, 300), Image.Resampling.LANCZOS)
                    photo = ImageTk.PhotoImage(img)
                    self.after(0, lambda: self.album_art.set_art(photo))
                except Exception as e:
                    logger.warning("Failed to load album art: %s", e)
                    self.after(0, lambda: self.album_art._draw_placeholder())
            else:
                self.after(0, lambda: self.album_art._draw_placeholder())

        self._art_fetch_thread = threading.Thread(target=fetch_art, daemon=True)
        self._art_fetch_thread.start()

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