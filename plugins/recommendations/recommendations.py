"""
Recommendation Engine Plugin — Local co-occurrence model for music recommendations.

Builds artist→artist affinity matrix from listening sessions.
Provides: similar artists, genre radio, revisit candidates, new-to-you artists.
"""

import os
import sqlite3
import threading
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

from core.plugin_base import MusicPlayerPlugin


class MusicPlayerPlugin(MusicPlayerPlugin):
    """Local-only recommendation engine using co-occurrence counting.

    Named MusicPlayerPlugin because the plugin loader looks for a class with
    that name by default (see plugins/__init__.py:_load_plugin_class_from_dir).
    """

    def __init__(self, config: Dict[str, Any]):
        """Initialize with manifest settings.

        Args:
            config: Manifest data from config.json including 'settings'.
        """
        super().__init__(config)
        # Settings come from manifest's 'settings' object
        settings = config.get("settings", {}).get("recommendations", {})
        self.session_gap_seconds: int = settings.get("session_gap_seconds", 300)
        self.scan_library_on_startup: bool = settings.get("scan_library_on_startup", True)

        # Runtime state (set in initialize)
        self.db_path: Optional[str] = None
        self._conn: Optional[sqlite3.Connection] = None
        self._bg_thread: Optional[threading.Thread] = None
        self._stop_event: Optional[threading.Event] = None
        self._rebuild_lock: threading.Lock = threading.Lock()

        # Live pairing state (two slots to avoid self-pairing)
        self._last_finished: Optional[Dict[str, Any]] = None
        self._current: Optional[Dict[str, Any]] = None

        # Track current artist for recommendations
        self._current_artist: Optional[str] = None

    # ------------------------------------------------------------------
    # Plugin lifecycle
    # ------------------------------------------------------------------

    def initialize(self, core: Any) -> bool:
        """Initialize with core engine reference.

        Resolves database path, opens connection, registers hooks,
        starts background thread for library scan / rebuild.

        Args:
            core: Core engine (MusicPlayer with .config attached).

        Returns:
            True if initialization succeeded.
        """
        # Resolve database path from app config (fallback to PlayStats default)
        # core.config should be a Config instance (attached by main.py)
        if core and hasattr(core, "config") and hasattr(core.config, "get"):
            raw_db = core.config.get("stats.db_path", "")
            if not raw_db:
                from core.stats import PlayStats
                raw_db = PlayStats.DEFAULT_DB_PATH
        else:
            from core.stats import PlayStats
            raw_db = PlayStats.DEFAULT_DB_PATH

        self.db_path = os.path.expanduser(raw_db)

        # Open our own SQLite connection (same pattern as PlayStats)
        self._conn = sqlite3.connect(
            self.db_path,
            check_same_thread=False,
            isolation_level=None,  # autocommit
        )
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")

        # Ensure tables exist
        self._create_schema()

        # Store core for hook registration
        self.core = core

        # Register hooks: we'll be called back via PluginManager.trigger_hook
        self.register_hook("on_song_change", self._on_song_change)
        self.register_hook("on_playback_complete", self._on_playback_complete)

        # Start background thread for library scan / rebuild
        self._stop_event = threading.Event()
        self._bg_thread = threading.Thread(target=self._background_worker, daemon=True)
        self._bg_thread.start()

        return True

    def shutdown(self) -> None:
        """Stop background thread, close connection."""
        if self._stop_event:
            self._stop_event.set()
        if self._bg_thread and self._bg_thread.is_alive():
            self._bg_thread.join(timeout=5.0)
        if self._conn:
            self._conn.close()
            self._conn = None

    def _create_schema(self) -> None:
        """Create recommendation tables in play_stats.db.

        Also creates the plays table (mirrors PlayStats schema) so the
        background worker can safely read plays on first startup even if
        PlayStats hasn't created it yet.
        """
        cur = self._conn.cursor()
        # Plays table: mirrors PlayStats schema so rebuild can read it
        cur.execute("""
            CREATE TABLE IF NOT EXISTS plays (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                track_path TEXT NOT NULL,
                artist TEXT,
                album TEXT,
                title TEXT,
                started_at INTEGER NOT NULL,
                ended_at INTEGER,
                completed BOOLEAN DEFAULT 0,
                skipped BOOLEAN DEFAULT 0,
                duration_ms INTEGER
            )
        """)
        # Co-occurrence matrix: artist_a < artist_b (canonical order)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS cooccurrence (
                artist_a TEXT NOT NULL,
                artist_b TEXT NOT NULL,
                play_count INTEGER DEFAULT 1,
                PRIMARY KEY (artist_a, artist_b)
            )
        """)
        # Album+track data for genre radio / revisit / new-to-you
        cur.execute("""
            CREATE TABLE IF NOT EXISTS album_songs (
                path TEXT PRIMARY KEY,
                album TEXT,
                artist TEXT,
                genre TEXT
            )
        """)
        # Metadata: when was matrix last rebuilt (INTEGER Unix seconds)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS cooccurrence_meta (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                last_built_at INTEGER NOT NULL
            )
        """)
        self._conn.commit()

    # ------------------------------------------------------------------
    # Background worker: library scan + matrix rebuild
    # ------------------------------------------------------------------

    def _background_worker(self) -> None:
        """Daemon thread: library scan, then startup rebuild if stale."""
        if not self._stop_event:
            return

        # 1. Library scan (populate album_songs)
        if self.scan_library_on_startup:
            self._scan_library_if_empty()

        # 2. Rebuild if matrix is stale (missing or older than latest play)
        if self._should_rebuild():
            self.build_from_history()

        # Idle until shutdown
        while not self._stop_event.wait(timeout=60.0):
            pass

    def _scan_library_if_empty(self) -> None:
        """Scan MPD library into album_songs if table is empty."""
        if not self.core or not hasattr(self.core, "list_all_info"):
            return
        cur = self._conn.cursor()
        cur.execute("SELECT COUNT(*) FROM album_songs")
        if cur.fetchone()[0] > 0:
            return  # already populated
        try:
            library = self.core.list_all_info()
            if not library:
                return
            rows = []
            for track in library:
                path = track.get("file") or track.get("path")
                if not path:
                    continue
                artist = track.get("artist", "").strip()
                album = track.get("album", "").strip()
                genre = track.get("genre", "").strip()
                if not artist:
                    continue
                rows.append((path, album, artist, genre))
            if rows:
                cur = self._conn.cursor()
                cur.executemany(
                    "INSERT OR REPLACE INTO album_songs (path, album, artist, genre) VALUES (?, ?, ?, ?)",
                    rows,
                )
                self._conn.commit()
        except Exception:
            pass  # best effort

    def _should_rebuild(self) -> bool:
        """Check if matrix needs rebuilding.

        Only stamp last_built_at after a successful rebuild.
        The first build happens on startup if the matrix is missing.
        Subsequent rebuilds are triggered by the plugin hook payload timing.
        """
        if self._conn is None:
            return True
        try:
            cur = self._conn.cursor()
            cur.execute("SELECT last_built_at FROM cooccurrence_meta WHERE id = 1")
            meta_row = cur.fetchone()
            if meta_row is None:
                # No row yet - first build needed
                return True
            last_built = meta_row[0]
            cur.execute("SELECT MAX(ended_at) FROM plays WHERE ended_at IS NOT NULL")
            latest_play_row = cur.fetchone()
            if latest_play_row is None or latest_play_row[0] is None:
                return False
            latest_play = latest_play_row[0]
            return latest_play > last_built
        except sqlite3.OperationalError:
            # No such table yet - first build needed
            return True

    def build_from_history(self) -> None:
        """Rebuild co-occurrence matrix from plays table.

        Writes into temp cooccurrence_new, atomically swaps into cooccurrence,
        stamps cooccurrence_meta.last_built_at = MAX(plays.ended_at).
        Pauses live pair recording via lock during rebuild.
        """
        # Acquire lock to pause live writes
        with self._rebuild_lock:
            if self._stop_event and self._stop_event.is_set():
                return
            # Read all completed plays in chronological order
            cur = self._conn.cursor()
            cur.execute("""
                SELECT artist, started_at, ended_at
                FROM plays
                WHERE ended_at IS NOT NULL AND artist IS NOT NULL AND artist != ''
                ORDER BY started_at
            """)
            plays = cur.fetchall()
            if not plays:
                return

            # Get the max ended_at *at rebuild start* for staleness check
            cur.execute("SELECT MAX(ended_at) FROM plays WHERE ended_at IS NOT NULL")
            max_ended_at = cur.fetchone()[0] or 0

            # Build co-occurrence in temp table
            cur.execute("DROP TABLE IF EXISTS cooccurrence_new")
            cur.execute("""
                CREATE TABLE cooccurrence_new (
                    artist_a TEXT NOT NULL,
                    artist_b TEXT NOT NULL,
                    play_count INTEGER DEFAULT 1,
                    PRIMARY KEY (artist_a, artist_b)
                )
            """)

            # Session logic: gap < session_gap_seconds → pair; skip breaks session
            # We select ALL plays (completed or not) in chronological order.
            # A session is a run of completed plays with gap < session_gap_seconds
            # between previous ended_at and next started_at.
            # A play that is NOT completed (skip or stop, completed=0) breaks the session.

            cur.execute("""
                SELECT artist, started_at, ended_at, completed
                FROM plays
                WHERE ended_at IS NOT NULL AND artist IS NOT NULL AND artist != ''
                ORDER BY started_at
            """)
            all_plays = cur.fetchall()

            if not all_plays:
                # stamp and return
                cur.execute(
                    "REPLACE INTO cooccurrence_meta (id, last_built_at) VALUES (1, ?)",
                    (max_ended_at,)
                )
                self._conn.commit()
                return

            # Session grouping with skip-break logic
            pair_counts: Dict[Tuple[str, str], int] = defaultdict(int)

            prev_ended = None
            prev_artist = None

            for artist, started_at, ended_at, completed in all_plays:
                if completed:
                    if prev_ended is not None and prev_artist is not None:
                        gap = started_at - prev_ended
                        if gap < self.session_gap_seconds:
                            # canonical order
                            a, b = (prev_artist, artist) if prev_artist < artist else (artist, prev_artist)
                            if a != b:  # no same-artist pairs
                                pair_counts[(a, b)] += 1
                        else:
                            # gap too large: new session
                            pass
                    # advance only on completed plays
                    prev_ended = ended_at
                    prev_artist = artist
                else:
                    # Any non-completed play (skip or stop) breaks the session
                    prev_ended = None
                    prev_artist = None

            # Batch insert into temp table
            if pair_counts:
                rows = [(a, b, count) for (a, b), count in pair_counts.items()]
                cur.executemany(
                    "INSERT INTO cooccurrence_new (artist_a, artist_b, play_count) VALUES (?, ?, ?)",
                    rows,
                )

            # Atomic swap: drop old table, rename temp table, stamp meta —
            # all inside one transaction so readers never see a half-built matrix.
            # On any error, ROLLBACK leaves the connection clean.
            try:
                cur.execute("BEGIN IMMEDIATE")
                cur.execute("DROP TABLE IF EXISTS cooccurrence")
                cur.execute("ALTER TABLE cooccurrence_new RENAME TO cooccurrence")
                cur.execute(
                    "REPLACE INTO cooccurrence_meta (id, last_built_at) VALUES (1, ?)",
                    (max_ended_at,)
                )
                cur.execute("COMMIT")
            except Exception:
                try:
                    cur.execute("ROLLBACK")
                except Exception:
                    pass
                raise

    # ------------------------------------------------------------------
    # Hook handlers (called by PluginManager.trigger_hook)
    # ------------------------------------------------------------------

    def _on_song_change(self, track_info: Dict[str, Any]) -> None:
        """Called when a new track starts playing.

        track_info carries: {artist, album, title, path, started_at (Unix seconds)}.
        Uses two-slot logic to avoid self-pairing.
        """
        if not track_info or not track_info.get("artist"):
            return

        started_at = track_info.get("started_at", int(time.time()))
        artist = track_info["artist"].strip()
        if not artist:
            return

        # Update current artist for get_recommendations_for_current
        self._current_artist = artist

        # Pair with last finished if within session gap
        if self._last_finished is not None:
            last_artist = self._last_finished.get("artist", "").strip()
            if last_artist and last_artist != artist:
                last_ended = self._last_finished.get("ended_at")
                if last_ended is not None:
                    gap = started_at - last_ended
                    if gap < self.session_gap_seconds:
                        self._record_pair(last_artist, artist)

        # Move current → last_finished (slot rotation)
        self._last_finished = self._current
        # Set new current track
        self._current = {
            "artist": artist,
            "album": track_info.get("album", "").strip(),
            "title": track_info.get("title", "").strip(),
            "path": track_info.get("path", "").strip(),
            "started_at": started_at,
        }

    def _on_playback_complete(
        self,
        track_info: Dict[str, Any],
        completed: bool,
        skipped: bool
    ) -> None:
        """Called when a track ends (completed, skipped, or stopped)."""
        if not track_info or not track_info.get("artist"):
            return

        ended_at = int(time.time())
        artist = track_info["artist"].strip()
        if not artist:
            return

        if completed:
            # Track played to completion: stamp ended_at, rotate slots
            if self._current is not None:
                self._last_finished = self._current.copy()
                self._last_finished["ended_at"] = ended_at
            self._current = None
            # Update last_built_at so steady live plays don't trigger rebuild
            self._update_last_built_at(ended_at)
        else:
            # Skip or stop (completed=False, skipped=True/False): break session
            self._last_finished = None
            self._current = None

    def _update_last_built_at(self, ended_at: int) -> None:
        """Update cooccurrence_meta.last_built_at to prevent false staleness.

        Only UPDATE an existing row - never create one. If the matrix has
        never been built, the row is absent and the next startup rebuild
        will run; creating a row here would (incorrectly) mark the matrix
        as built and skip that rebuild forever.
        """
        with self._rebuild_lock:
            if self._conn:
                cur = self._conn.cursor()
                cur.execute(
                    "UPDATE cooccurrence_meta SET last_built_at = ? WHERE id = 1",
                    (ended_at,)
                )
                self._conn.commit()

    def _record_pair(self, artist_a: str, artist_b: str) -> None:
        """Record a co-occurrence pair in canonical order."""
        a, b = (artist_a, artist_b) if artist_a < artist_b else (artist_b, artist_a)
        if a == b:
            return
        with self._rebuild_lock:
            if self._conn:
                cur = self._conn.cursor()
                cur.execute(
                    "INSERT INTO cooccurrence (artist_a, artist_b, play_count) VALUES (?, ?, 1) "
                    "ON CONFLICT(artist_a, artist_b) DO UPDATE SET play_count = play_count + 1",
                    (a, b)
                )
                self._conn.commit()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_capabilities(self) -> List[str]:
        return self.config.get("capabilities", ["recommendations"])

    def get_similar_artists(self, artist: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Return co-occurring artists ranked by play_count DESC.

        Bidirectional: queries both columns; same-artist pairs excluded.
        Takes the rebuild lock so reads never see a half-built matrix.
        """
        if not self._conn:
            return []
        with self._rebuild_lock:
            cur = self._conn.cursor()
            cur.execute("""
                SELECT artist_a, artist_b, play_count
                FROM cooccurrence
                WHERE artist_a != artist_b
                AND (artist_a = ? OR artist_b = ?)
            """, (artist, artist))
            results = []
            for a, b, count in cur.fetchall():
                other = b if a == artist else a
                results.append({"artist": other, "score": count})
            results.sort(key=lambda x: x["score"], reverse=True)
            return results[:limit]

    def get_recommendations_for_current(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Recommendations based on currently playing track's artist."""
        if not self._current_artist:
            return []
        return self.get_similar_artists(self._current_artist, limit)

    def get_genre_radio(self, genre: str) -> List[str]:
        """Shuffled track paths from album_songs matching genre.

        Uses instr() so "Rock, Pop" matches both "Rock" and "Pop" queries.
        """
        if not self._conn:
            return []
        with self._rebuild_lock:
            cur = self._conn.cursor()
            cur.execute(
                "SELECT path FROM album_songs WHERE genre IS NOT NULL AND genre != '' AND instr(genre, ?) > 0",
                (genre,)
            )
            paths = [row[0] for row in cur.fetchall()]
        import random
        random.shuffle(paths)
        return paths

    def get_revisit_candidates(self, days: int = 30) -> List[str]:
        """One track path per album not played in last N days."""
        if not self._conn:
            return []
        with self._rebuild_lock:
            cutoff = int(time.time()) - days * 86400
            cur = self._conn.cursor()
            # Find albums with recent plays
            cur.execute("""
                SELECT DISTINCT album FROM plays
                WHERE ended_at IS NOT NULL AND ended_at >= ? AND album IS NOT NULL AND album != ''
            """, (cutoff,))
            recent_albums = {row[0] for row in cur.fetchall()}
            # Find one track per album not in recent_albums
            cur.execute("""
                SELECT path, album FROM album_songs
                WHERE album IS NOT NULL AND album != ''
            """)
            candidates = []
            seen_albums = set()
            for path, album in cur.fetchall():
                if album in recent_albums or album in seen_albums:
                    continue
                candidates.append(path)
                seen_albums.add(album)
            return candidates

    def get_new_to_you(self) -> List[str]:
        """Artists in library (album_songs) absent from play_stats.plays."""
        if not self._conn:
            return []
        with self._rebuild_lock:
            cur = self._conn.cursor()
            cur.execute("SELECT DISTINCT artist FROM plays WHERE artist IS NOT NULL AND artist != ''")
            played_artists = {row[0] for row in cur.fetchall()}
            cur.execute("SELECT DISTINCT artist FROM album_songs WHERE artist IS NOT NULL AND artist != ''")
            library_artists = {row[0] for row in cur.fetchall()}
            new_artists = library_artists - played_artists
            return list(new_artists)

    def fill_album_songs(self) -> None:
        """Public wrapper to trigger library scan (if scan_library_on_startup)."""
        self._scan_library_if_empty()