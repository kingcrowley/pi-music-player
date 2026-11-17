"""Slice 2.2 Test Script — Statistics UI & Insights

Usage:
    python3 tests/test_slice_2_2.py

Usage for quick import check:
    python3 -c "from tests.test_slice_2_2 import run_all_tests; run_all_tests()"
"""

import sys
import os
import time
import tempfile
import shutil
import unittest
import logging
import tkinter as tk
from unittest.mock import Mock, MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.stats import PlayStats
from core.config import Config
from ui.dashboard import Dashboard

RESULTS = []


def check(name: str, condition: bool, detail: str = ""):
    """Record a test result."""
    status = "PASS" if condition else "FAIL"
    mark = "PASS" if condition else "FAIL"
    RESULTS.append((status, name))
    print(f"  [{mark}] {status}: {name}" + (f" - {detail}" if detail else ""))


# A minimal mock MusicPlayer that returns controlled data for _update_ui tests.
class MockMusicPlayer:
    """Minimal mock of MusicPlayer for dashboard _update_ui tests.

    Provides get_status() and get_current_song() that return deterministic
    dicts so the dashboard's recording state-machine logic can be tested
    without a real MPD connection.
    """

    def __init__(self):
        # State machine
        self._state = "stopped"
        self._prev_state = "stopped"
        self._elapsed = 0.0
        self._duration = 300.0  # 5 min default
        self._volume = 50
        self._song_file = ""
        self._song_id = None
        self._title = "Test Track"
        self._artist = "Test Artist"
        self._album = "Test Album"

    def get_status(self):
        return {
            "state": self._state,
            "elapsed": self._elapsed,
            "duration": self._duration,
            "volume": str(self._volume),
        }

    def get_current_song(self):
        return {
            "file": self._song_file,
            "id": self._song_id,
            "title": self._title,
            "artist": self._artist,
            "album": self._album,
        }

    # Convenience: set a playing state with elapsed/duration
    def set_playing(self, elapsed=0.0, duration=None):
        self._state = "playing"
        self._elapsed = elapsed
        self._duration = duration if duration else self._duration
        # Derive id from file if not set
        if self._song_id is None and self._song_file:
            self._song_id = hash(self._song_file)

    # Set paused state
    def set_paused(self, elapsed=0.0, duration=None):
        self._state = "paused"
        self._elapsed = elapsed
        self._duration = duration if duration else self._duration

    # Set stopped state
    def set_stopped(self):
        self._state = "stopped"
        self._elapsed = 0.0

    # Simulate a track change
    def set_next_song(self, new_file, new_id=None, new_elapsed=0.0):
        self._state = "playing"
        self._prev_state = "playing"  # so transition_into_play triggers
        self._song_file = new_file
        self._song_id = new_id
        self._elapsed = new_elapsed
        self._title = f"Track from {new_file}"
        self._artist = "Artist"
        self._album = "Album"

    def set_status_state_song(self, state, elapsed=0.0, duration=None,
                               song_file="", song_id=None, song_title="Test Track"):
        """Set status state + song in one call (for combined drive)."""
        self._state = state
        self._elapsed = elapsed
        self._duration = duration if duration else self._duration
        self._song_file = song_file
        self._song_id = song_id
        self._title = song_title

    # End of MockMusicPlayer


class Slice22TestCase(unittest.TestCase):
    """Unit tests for PlayStats Slice 2.2 features.

    These tests cover:
    - Most Played Tracks (get_top_tracks)
    - Recent History (get_recent_history)
    - Listening Time Heatmap (get_listening_time_heatmap)
    - Skip Rate (get_skip_rate)
    - Retention cleanup
    - Export CSV
    - Dashboard _update_ui state-machine (new tests below)
    """

    def setUp(self):
        self.tmpdirs = []
        self._root = None
        self._dash = None

    def tearDown(self):
        # Clean up Dashboard and Tk root if present
        if self._dash:
            try:
                self._dash.destroy()
            except Exception:
                pass
        if self._root:
            try:
                self._root.destroy()
            except Exception:
                pass
        for d in self.tmpdirs:
            shutil.rmtree(d, ignore_errors=True)

    def _make_dashboard(self, stats_enabled=True):
        """Create a headless Dashboard with polling disabled."""
        self._root = tk.Tk()
        self._root.withdraw()
        tmpdir = tempfile.mkdtemp()
        self.tmpdirs.append(tmpdir)
        cfg = Config(os.path.join(tmpdir, "config.json"))
        if not stats_enabled:
            cfg.set("stats.enabled", False)
        else:
            cfg.set("stats.db_path", os.path.join(tmpdir, "stats.db"))
        mp = MagicMock()
        mp.get_status.return_value = {"state": "stop", "elapsed": 0.0, "duration": 0.0, "volume": "50"}
        mp.get_current_song.return_value = {}
        # No artwork available: return None so the background fetch is a no-op.
        artwork_cache = MagicMock()
        artwork_cache.get_art.return_value = None
        with patch.object(Dashboard, "_start_poll_loop", lambda self: None):
            self._dash = Dashboard(mp, artwork_cache, cfg, fullscreen=False)
        return self._dash

    # --- get_top_tracks ---

    def test_get_top_tracks_basic(self):
        """get_top_tracks returns top tracks by play count."""
        tmpdir = tempfile.mkdtemp()
        self.tmpdirs.append(tmpdir)
        db_path = os.path.join(tmpdir, "test.db")

        stats = PlayStats(db_path=db_path, enabled=True)
        try:
            now = int(time.time())

            # Insert plays: 2 for track A, 1 for track B, 1 skipped for track C
            for i, (track, comp, skip) in enumerate([
                ('track_a.mp3', True, False),
                ('track_a.mp3', True, False),   # second play of same track
                ('track_b.mp3', True, False),
                ('track_c.mp3', False, True),   # skipped, should not count in top tracks
            ]):
                stats._conn.execute(
                    "INSERT INTO plays (track_path, artist, album, title, started_at, ended_at, completed, skipped, duration_ms) VALUES (?,?,?,?,?,?,?,?,?)",
                    (track, f"Artist {i}", f"Album {i}", f"Title {i}",
                     now - 100, now - 100 + 30, comp, skip, 30000),
                )
            stats._conn.commit()
            top = stats.get_top_tracks(limit=5)
            check("Top tracks returns list", isinstance(top, list))
            check("Track A has 2 plays", any(t.get("play_count") == 2 for t in top))
            check("Track B has 1 play", any(t.get("play_count") == 1 for t in top))
            check("Skipped track excluded from top",
                  not any(t.get("file") == 'track_c.mp3' for t in top))
            stats.close()

        finally:
            stats.close()
            os.remove(db_path) if os.path.exists(db_path) else None

    def test_get_top_tracks_limit(self):
        """get_top_tracks respects the limit argument."""
        tmpdir = tempfile.mkdtemp()
        self.tmpdirs.append(tmpdir)
        db_path = os.path.join(tmpdir, "test.db")

        stats = PlayStats(db_path=db_path, enabled=True)
        try:
            now = int(time.time())
            for i in range(10):
                stats._conn.execute(
                    "INSERT INTO plays (track_path, artist, album, title, started_at, ended_at, completed, skipped, duration_ms) VALUES (?,?,?,?,?,?,?,?,?)",
                    (f't{i}.mp3', 'A', 'Al', f'T{i}', now - 100, now, 1, 0, 30000),
                )
            stats._conn.commit()
            top = stats.get_top_tracks(limit=3)
            check("Limit=3 returns 3 rows", len(top) == 3)
            stats.close()

        finally:
            stats.close()
            os.remove(db_path) if os.path.exists(db_path) else None

    # --- get_recent_history ---

    def test_get_recent_history_basic(self):
        """get_recent_history returns recent completed plays."""
        tmpdir = tempfile.mkdtemp()
        self.tmpdirs.append(tmpdir)
        db_path = os.path.join(tmpdir, "test.db")

        stats = PlayStats(db_path=db_path, enabled=True)
        try:
            now = int(time.time())
            # Recent completed play
            stats._conn.execute(
                "INSERT INTO plays (track_path, artist, album, title, started_at, ended_at, completed, skipped, duration_ms) VALUES (?,?,?,?,?,?,?,?,?)",
                ('recent.mp3', 'Recent Artist', 'Recent Album', 'Recent Title',
                 now - 100, now, 1, 0, 200000),
            )
            stats._conn.commit()
            recent = stats.get_recent_history(limit=5)
            check("Returns list", isinstance(recent, list))
            check("Recent play included", any(h.get("title") == "Recent Title" for h in recent))
            check("ended_at is populated", recent[0].get("ended_at") is not None)
            stats.close()

        finally:
            stats.close()
            os.remove(db_path) if os.path.exists(db_path) else None

    def test_get_recent_history_order(self):
        """get_recent_history returns rows most-recent-first."""
        tmpdir = tempfile.mkdtemp()
        self.tmpdirs.append(tmpdir)
        db_path = os.path.join(tmpdir, "test.db")

        stats = PlayStats(db_path=db_path, enabled=True)
        try:
            now = int(time.time())
            for i in range(3):
                stats._conn.execute(
                    "INSERT INTO plays (track_path, artist, album, title, started_at, ended_at, completed, skipped, duration_ms) VALUES (?,?,?,?,?,?,?,?,?)",
                    (f't{i}.mp3', 'A', 'Al', f'T{i}', now - 100 + i, now - 90 + i, 1, 0, 30000),
                )
            stats._conn.commit()
            recent = stats.get_recent_history(limit=5)
            check("Most recent first", recent[0]["title"] == "T2")
            check("Third is oldest", recent[2]["title"] == "T0")
            stats.close()

        finally:
            stats.close()
            os.remove(db_path) if os.path.exists(db_path) else None

    # --- get_skip_rate ---

    def test_get_skip_rate_basic(self):
        """get_skip_rate returns skip percentages per artist."""
        tmpdir = tempfile.mkdtemp()
        self.tmpdirs.append(tmpdir)
        db_path = os.path.join(tmpdir, "test.db")

        stats = PlayStats(db_path=db_path, enabled=True)
        try:
            now = int(time.time())
            # Artist 1: 1 completed + 1 skipped = 50%
            stats._conn.execute(
                "INSERT INTO plays (track_path, artist, album, title, started_at, ended_at, completed, skipped, duration_ms) VALUES (?,?,?,?,?,?,?,?,?)",
                ('t1.mp3', 'Artist 1', 'Album 1', 'Track 1',
                 now - 30, now - 20, 1, 0, 30000),
            )
            stats._conn.execute(
                "INSERT INTO plays (track_path, artist, album, title, started_at, ended_at, completed, skipped, duration_ms) VALUES (?,?,?,?,?,?,?,?,?)",
                ('t2.mp3', 'Artist 1', 'Album 1', 'Track 2',
                 now - 20, now - 10, 0, 1, 30000),  # skipped
            )
            # Artist 2: 1 completed, no skips
            stats._conn.execute(
                "INSERT INTO plays (track_path, artist, album, title, started_at, ended_at, completed, skipped, duration_ms) VALUES (?,?,?,?,?,?,?,?,?)",
                ('t3.mp3', 'Artist 2', 'Album 2', 'Track 3',
                 now - 10, now, 1, 0, 30000),
            )
            stats._conn.commit()
            rates = stats.get_skip_rate()
            check("Returns dict", isinstance(rates, dict))
            check("Artist 1 has skip rate", "Artist 1" in rates)
            check("Artist 1 skip rate is 50%", abs(rates.get("Artist 1", 0) - 50.0) < 0.01)
            check("Artist 2 skip rate is 0%", abs(rates.get("Artist 2", -1) - 0.0) < 0.01)
            stats.close()

        finally:
            stats.close()
            os.remove(db_path) if os.path.exists(db_path) else None

    def test_get_skip_rate_disabled(self):
        """get_skip_rate returns empty dict when disabled."""
        tmpdir = tempfile.mkdtemp()
        self.tmpdirs.append(tmpdir)
        db_path = os.path.join(tmpdir, "test.db")

        stats = PlayStats(db_path=db_path, enabled=False)
        try:
            check("Returns empty dict when disabled", stats.get_skip_rate() == {})
            stats.close()

        finally:
            stats.close()
            os.remove(db_path) if os.path.exists(db_path) else None

    # --- get_listening_time_heatmap ---

    def test_get_listening_time_heatmap_basic(self):
        """get_listening_time_heatmap returns heatmap by day/hour."""
        tmpdir = tempfile.mkdtemp()
        self.tmpdirs.append(tmpdir)
        db_path = os.path.join(tmpdir, "test.db")

        stats = PlayStats(db_path=db_path, enabled=True)
        try:
            # Manually populate the heatmap cache
            stats._listening_time_heatmap = {
                0: {9: 60, 14: 120},  # Mon: 9am=1h, 2pm=2h
                1: {8: 45},            # Tue: 8am=45m
            }
            hm = stats.get_listening_time_heatmap()
            check("Returns dict", isinstance(hm, dict))
            check("Has Monday data", 0 in hm)
            check("Tuesday hour has data", 1 in hm and 8 in hm[1])
            check("Monday 9am = 60 min", hm[0].get(9) == 60)
            stats.close()

        finally:
            stats.close()
            os.remove(db_path) if os.path.exists(db_path) else None

    def test_get_listening_time_heatmap_disabled(self):
        """get_listening_time_heatmap returns empty dict when disabled."""
        tmpdir = tempfile.mkdtemp()
        self.tmpdirs.append(tmpdir)
        db_path = os.path.join(tmpdir, "test.db")

        stats = PlayStats(db_path=db_path, enabled=False)
        try:
            check("Returns empty dict when disabled", stats.get_listening_time_heatmap() == {})
            stats.close()

        finally:
            stats.close()
            os.remove(db_path) if os.path.exists(db_path) else None

    # --- retention ---

    def test_retention_deletes_completed(self):
        """Retention deletes completed plays older than the window."""
        tmpdir = tempfile.mkdtemp()
        self.tmpdirs.append(tmpdir)
        db_path = os.path.join(tmpdir, "test.db")

        stats = PlayStats(db_path=db_path, enabled=True)
        try:
            stats._retention_seconds = 10  # very short for testing
            now = int(time.time())

            # Old completed play
            old = now - 20 * 24 * 3600
            stats._conn.execute(
                "INSERT INTO plays (track_path, artist, album, title, started_at, ended_at, completed, skipped, duration_ms) VALUES (?,?,?,?,?,?,?,?,?)",
                ('old_c.mp3', 'A', 'Al', 'T', old, old + 100, 1, 0, 245000),
            )
            # Recent completed play
            stats._conn.execute(
                "INSERT INTO plays (track_path, artist, album, title, started_at, ended_at, completed, skipped, duration_ms) VALUES (?,?,?,?,?,?,?,?,?)",
                ('new_c.mp3', 'B', 'Bl', 'T', now - 100, now, 1, 0, 200000),
            )
            stats._conn.commit()
            stats.cleanup()

            remaining = [r[0] for r in
                         stats._conn.execute("SELECT track_path FROM plays").fetchall()]
            check("Old completed deleted", 'old_c.mp3' not in remaining)
            check("Recent completed kept", 'new_c.mp3' in remaining)
            stats.close()

        finally:
            stats.close()
            os.remove(db_path) if os.path.exists(db_path) else None

    def test_retention_deletes_skipped_and_stopped(self):
        """Retention also deletes skipped and stopped plays older than the window."""
        tmpdir = tempfile.mkdtemp()
        self.tmpdirs.append(tmpdir)
        db_path = os.path.join(tmpdir, "test.db")

        stats = PlayStats(db_path=db_path, enabled=True)
        try:
            stats._retention_seconds = 10
            now = int(time.time())

            # Old skipped play
            old = now - 20 * 24 * 3600
            stats._conn.execute(
                "INSERT INTO plays (track_path, artist, album, title, started_at, ended_at, completed, skipped, duration_ms) VALUES (?,?,?,?,?,?,?,?,?)",
                ('old_s.mp3', 'A', 'Al', 'T', old - 3600, old + 50, 0, 1, 120000),
            )
            # Old stopped play
            stats._conn.execute(
                "INSERT INTO plays (track_path, artist, album, title, started_at, ended_at, completed, skipped, duration_ms) VALUES (?,?,?,?,?,?,?,?,?)",
                ('old_t.mp3', 'B', 'Bl', 'T', old - 7200, old + 30, 0, 0, 60000),
            )
            # Recent completed play
            stats._conn.execute(
                "INSERT INTO plays (track_path, artist, album, title, started_at, ended_at, completed, skipped, duration_ms) VALUES (?,?,?,?,?,?,?,?,?)",
                ('new_c.mp3', 'C', 'Cl', 'T', now - 100, now, 1, 0, 200000),
            )
            stats._conn.commit()
            stats.cleanup()

            remaining = [r[0] for r in
                         stats._conn.execute("SELECT track_path FROM plays").fetchall()]
            check("Old skipped deleted", 'old_s.mp3' not in remaining)
            check("Old stopped deleted", 'old_t.mp3' not in remaining)
            check("Recent completed kept", 'new_c.mp3' in remaining)
            stats.close()

        finally:
            stats.close()
            os.remove(db_path) if os.path.exists(db_path) else None

    def test_retention_keeps_open_plays_close_them(self):
        """Retention closes open plays without deleting them."""
        tmpdir = tempfile.mkdtemp()
        self.tmpdirs.append(tmpdir)
        db_path = os.path.join(tmpdir, "test.db")

        stats = PlayStats(db_path=db_path, enabled=True)
        try:
            stats._retention_seconds = 10
            now = int(time.time())

            # Open play (ended_at is NULL)
            stats._conn.execute(
                "INSERT INTO plays (track_path, artist, album, title, started_at, ended_at, completed, skipped, duration_ms) VALUES (?,?,?,?,?,?,?,?,?)",
                ('open.mp3', 'A', 'Al', 'T', now - 50, None, 0, 0, 50000),
            )
            stats._conn.commit()
            stats.cleanup()

            row = stats._conn.execute(
                "SELECT ended_at, completed FROM plays WHERE track_path = ?",
                ('open.mp3',)
            ).fetchone()
            check("Open play closed (ended_at set)", row is not None and row[0] is not None)
            stats.close()

        finally:
            stats.close()
            os.remove(db_path) if os.path.exists(db_path) else None

    def test_retention_disabled(self):
        """cleanup() does nothing when stats disabled."""
        tmpdir = tempfile.mkdtemp()
        self.tmpdirs.append(tmpdir)
        db_path = os.path.join(tmpdir, "test.db")

        stats = PlayStats(db_path=db_path, enabled=False)
        try:
            stats.cleanup()  # should not raise
            check("cleanup does not raise when disabled", True)
            stats.close()

        finally:
            stats.close()
            os.remove(db_path) if os.path.exists(db_path) else None

    # --- export_csv ---

    def test_export_csv_basic(self):
        """export_csv writes a valid CSV file."""
        tmpdir = tempfile.mkdtemp()
        self.tmpdirs.append(tmpdir)
        db_path = os.path.join(tmpdir, "test.db")

        stats = PlayStats(db_path=db_path, enabled=True)
        try:
            now = int(time.time())
            stats._conn.execute(
                "INSERT INTO plays (track_path, artist, album, title, started_at, ended_at, completed, skipped, duration_ms) VALUES (?,?,?,?,?,?,?,?,?)",
                ('test.mp3', 'Artist', 'Album', 'Track',
                 now - 30, now, 1, 0, 30000),
            )
            stats._conn.commit()
            path = stats.export_csv()
            check("Returns path", path is not None and isinstance(path, str))
            check("File exists", os.path.exists(path) if path else False)
            if path and os.path.exists(path):
                with open(path) as f:
                    header = f.readline().strip()
                    check("CSV has header", "id" in header)
                    rows = f.readlines()
                    check("Has at least 1 data row", len(rows) >= 1)
            stats.close()

        finally:
            stats.close()
            os.remove(db_path) if os.path.exists(db_path) else None

    def test_export_csv_disabled(self):
        """export_csv returns None when stats disabled."""
        tmpdir = tempfile.mkdtemp()
        self.tmpdirs.append(tmpdir)
        db_path = os.path.join(tmpdir, "test.db")

        stats = PlayStats(db_path=db_path, enabled=False)
        try:
            path = stats.export_csv()
            check("Returns None when disabled", path is None)
            stats.close()

        finally:
            stats.close()
            os.remove(db_path) if os.path.exists(db_path) else None

    # --- integration: retention + top_tracks ---

    def test_retention_and_top_tracks_integration(self):
        """After retention cleanup, get_top_tracks reflects only surviving plays."""
        tmpdir = tempfile.mkdtemp()
        self.tmpdirs.append(tmpdir)
        db_path = os.path.join(tmpdir, "test.db")

        stats = PlayStats(db_path=db_path, enabled=True)
        try:
            stats._retention_seconds = 10
            now = int(time.time())

            # 2 old completed plays of the same track
            for _ in range(2):
                old = now - 20 * 24 * 3600
                stats._conn.execute(
                    "INSERT INTO plays (track_path, artist, album, title, started_at, ended_at, completed, skipped, duration_ms) VALUES (?,?,?,?,?,?,?,?,?)",
                    ('old.mp3', 'X', 'Al', 'OldTrack', old, old + 100, 1, 0, 30000),
                )
            # 1 recent completed play of a different track
            stats._conn.execute(
                "INSERT INTO plays (track_path, artist, album, title, started_at, ended_at, completed, skipped, duration_ms) VALUES (?,?,?,?,?,?,?,?,?)",
                ('recent.mp3', 'Y', 'Bl', 'RecentTrack', now - 100, now, 1, 0, 30000),
            )
            stats._conn.commit()
            stats.cleanup()

            top = stats.get_top_tracks(limit=5)
            check("Recent track appears in top",
                  any(t.get("title") == "RecentTrack" for t in top))
            check("Old track gone after cleanup",
                  not any(t.get("title") == "OldTrack" for t in top))
            stats.close()

        finally:
            stats.close()
            os.remove(db_path) if os.path.exists(db_path) else None

    # --- dashboard _update_ui state-machine ---

    def _drive_update_ui(self, status, song):
        """Drive one poll of _update_ui and return the dashboard."""
        self._dash._update_ui(status, song)
        return self._dash

    @staticmethod
    def _all_rows(stats):
        """Return every play row (completed + skipped + stopped) as dicts."""
        cur = stats._conn.execute(
            "SELECT track_path, ended_at, completed, skipped FROM plays ORDER BY id ASC"
        )
        return [
            {"file": r[0], "ended_at": r[1], "completed": bool(r[2]), "skipped": bool(r[3])}
            for r in cur.fetchall()
        ]

    def _open_row(self, file="a.mp3", song_id="1", elapsed=10.0, duration=300.0):
        """Drive a playing poll so the dashboard opens a stats row."""
        self._drive_update_ui(
            {"state": "play", "elapsed": elapsed, "duration": duration, "volume": "50"},
            {"file": file, "id": song_id, "title": "T", "artist": "A", "album": "Al"},
        )

    def test_update_ui_unknown_status_keeps_row_open(self):
        """Unknown status poll does not close an active play row."""
        self._dash = self._make_dashboard(stats_enabled=True)
        self._open_row()
        self.assertTrue(self._dash._play_row_active, "Playing poll should open a row")
        # Send unknown status: should bail out before touching stats state
        self._drive_update_ui(
            {"state": "unknown", "elapsed": 0.0, "duration": 0.0, "volume": "50"},
            {"file": "a.mp3", "id": "1", "title": "T", "artist": "A", "album": "Al"},
        )
        self.assertTrue(self._dash._play_row_active, "Unknown status should keep row open")
        # _prev_state is not updated on the unusable-poll early return
        self.assertEqual(self._dash._prev_state, "playing",
                         "_prev_state should keep the last valid state")
        self.assertEqual(len(self._all_rows(self._dash._stats)), 1,
                         "No extra row should be created")
        self.assertIsNone(self._all_rows(self._dash._stats)[0]["ended_at"],
                          "Active row should remain open")

    def test_update_ui_empty_song_playing_keeps_row_open(self):
        """Empty song reply while playing does not finalize/close the row."""
        self._dash = self._make_dashboard(stats_enabled=True)
        self._open_row()
        self.assertTrue(self._dash._play_row_active, "Playing poll should open a row")
        current_song = self._dash._current_song
        self.assertIsNotNone(current_song, "current_song should be set after first poll")
        # Empty song while playing — should return early, keep row
        self._drive_update_ui(
            {"state": "play", "elapsed": 10.0, "duration": 300.0, "volume": "50"}, {}
        )
        self.assertTrue(self._dash._play_row_active, "Empty song while playing should keep row open")
        self.assertEqual(self._dash._current_song, current_song,
                         "current_song should be preserved")
        rows = self._all_rows(self._dash._stats)
        self.assertEqual(len(rows), 1, "No new row should be created")
        self.assertIsNone(rows[0]["ended_at"], "Row should remain open")

    def test_update_ui_stopped_finalizes_as_stopped(self):
        """Stopped transition with same song finalizes row as stopped (skipped=False)."""
        self._dash = self._make_dashboard(stats_enabled=True)
        self._open_row()
        self.assertTrue(self._dash._play_row_active, "Playing poll should open a row")
        # Send stopped status (same song/id) → stopped_transition
        self._drive_update_ui(
            {"state": "stop", "elapsed": 10.0, "duration": 300.0, "volume": "50"},
            {"file": "a.mp3", "id": "1", "title": "T", "artist": "A", "album": "Al"},
        )
        self.assertFalse(self._dash._play_row_active, "Row should be finalized after stopped transition")
        rows = self._all_rows(self._dash._stats)
        self.assertEqual(len(rows), 1, "Exactly one row expected")
        last = rows[0]
        self.assertIsNotNone(last["ended_at"], "Row should be closed")
        self.assertFalse(last["completed"], "stopped finalize should set completed=False")
        self.assertFalse(last["skipped"], "stopped finalize should set skipped=False")

    def test_update_ui_repeat_one_restarts(self):
        """Same queue entry, elapsed drops 200→20: old row finalized, new row opened."""
        self._dash = self._make_dashboard(stats_enabled=True)
        self._open_row(elapsed=200.0)
        self.assertTrue(self._dash._play_row_active, "First poll should open a row")
        # Second poll: same id, elapsed drops to 20s → repeat-one restart
        self._drive_update_ui(
            {"state": "play", "elapsed": 20.0, "duration": 300.0, "volume": "50"},
            {"file": "a.mp3", "id": "1", "title": "T", "artist": "A", "album": "Al"},
        )
        # Old row finalized (skipped, since 200 < threshold 270), new row opened
        rows = self._all_rows(self._dash._stats)
        self.assertEqual(len(rows), 2, "Old row finalized + new row opened")
        self.assertIsNotNone(rows[0]["ended_at"], "Old row should be closed")
        self.assertFalse(rows[0]["completed"], "200/300 is below threshold → not completed")
        self.assertTrue(rows[0]["skipped"], "Repeat-one finalize should mark old row skipped")
        self.assertIsNone(rows[1]["ended_at"], "New row should be open")
        self.assertTrue(self._dash._play_row_active, "A new row should be active after restart")

    def test_update_ui_seek_pending_suppresses_restart(self):
        """Seek pending before poll suppresses repeat-one restart (no finalize)."""
        self._dash = self._make_dashboard(stats_enabled=True)
        self._open_row(elapsed=200.0)
        self.assertTrue(self._dash._play_row_active, "First poll should open a row")
        # Pretend a user seek is in flight
        self._dash._seek_pending = True
        # Second poll: elapsed drops 200→20 (a seek, not a restart)
        self._drive_update_ui(
            {"state": "play", "elapsed": 20.0, "duration": 300.0, "volume": "50"},
            {"file": "a.mp3", "id": "1", "title": "T", "artist": "A", "album": "Al"},
        )
        self.assertFalse(self._dash._seek_pending, "seek_pending should be consumed after poll")
        self.assertFalse(self._dash._playback_restarted, "Seek pending should suppress restart detection")
        # Still just one open row — no spurious finalize
        rows = self._all_rows(self._dash._stats)
        self.assertEqual(len(rows), 1, "No extra row from a seek")
        self.assertIsNone(rows[0]["ended_at"], "Row should remain open after seek")
        self.assertTrue(self._dash._play_row_active, "Row should remain active after suppressed restart")

    def test_update_ui_track_change_finalizes_old_opens_new(self):
        """Track change (song_changed=True) finalizes old row and opens new row."""
        self._dash = self._make_dashboard(stats_enabled=True)
        self._open_row(file="a.mp3", song_id="1", elapsed=10.0)
        self.assertTrue(self._dash._play_row_active, "Song A should open a row")
        # Song B starts (different file/id) → song_changed
        self._drive_update_ui(
            {"state": "play", "elapsed": 0.0, "duration": 300.0, "volume": "50"},
            {"file": "b.mp3", "id": "2", "title": "Track B", "artist": "B", "album": "Bl"},
        )
        self.assertTrue(self._dash._play_row_active, "New row for Song B should be opened")
        rows = self._all_rows(self._dash._stats)
        self.assertEqual(len(rows), 2, "Song A finalized + Song B opened")
        a_row = rows[0]
        self.assertEqual(a_row["file"], "a.mp3")
        self.assertIsNotNone(a_row["ended_at"], "Song A row should be closed")
        self.assertFalse(a_row["completed"], "Track A at 10/300 should not be completed")
        self.assertTrue(a_row["skipped"], "Track A should be skipped (not completed)")
        self.assertEqual(rows[1]["file"], "b.mp3")
        self.assertIsNone(rows[1]["ended_at"], "Song B row should be open")

    def test_update_ui_transition_into_play_opens_row(self):
        """Stopped → Playing (transition_into_play) opens a new row."""
        self._dash = self._make_dashboard(stats_enabled=True)
        # First poll: stopped (baseline)
        self._drive_update_ui(
            {"state": "stop", "elapsed": 0.0, "duration": 0.0, "volume": "50"},
            {"file": "a.mp3", "id": "1", "title": "T", "artist": "A", "album": "Al"},
        )
        self.assertFalse(self._dash._play_row_active, "Stopped state should not open a row")
        # Now transition to playing — should open a new row
        self._open_row(elapsed=0.0)
        self.assertTrue(self._dash._play_row_active, "Stopped→playing should open a new row")
        rows = self._all_rows(self._dash._stats)
        self.assertEqual(len(rows), 1, "Exactly one row should be opened")
        self.assertIsNone(rows[0]["ended_at"], "Opened row should be open")

    def test_update_ui_paused_to_playing_opens_row(self):
        """Paused → Playing (transition_into_play) opens a new row."""
        self._dash = self._make_dashboard(stats_enabled=True)
        # First poll: paused (baseline) — no row
        self._drive_update_ui(
            {"state": "pause", "elapsed": 10.0, "duration": 300.0, "volume": "50"},
            {"file": "a.mp3", "id": "1", "title": "T", "artist": "A", "album": "Al"},
        )
        self.assertFalse(self._dash._play_row_active, "Paused should not open a row")
        # Playing poll → transition_into_play opens a row
        self._open_row(elapsed=20.0)
        self.assertTrue(self._dash._play_row_active, "paused→playing should open a row")

    def test_update_ui_empty_song_stopped_finalizes_row(self):
        """Empty song reply + state=stop with active row finalizes row by threshold."""
        self._dash = self._make_dashboard(stats_enabled=True)
        # Open a row with elapsed 270/300 (at the completion threshold)
        self._open_row(elapsed=270.0, duration=300.0)
        self.assertTrue(self._dash._play_row_active, "Playing poll should open a row")
        # Empty song + stopped → finalize using previous elapsed/duration
        self._drive_update_ui(
            {"state": "stop", "elapsed": 270.0, "duration": 300.0, "volume": "50"}, {}
        )
        self.assertFalse(self._dash._play_row_active, "Row should be finalized after empty+stop")
        self.assertIsNone(self._dash._current_song, "current_song should be cleared on finalize")
        rows = self._all_rows(self._dash._stats)
        self.assertEqual(len(rows), 1, "Exactly one row expected")
        last = rows[0]
        self.assertIsNotNone(last["ended_at"], "Row should be closed")
        self.assertTrue(last["completed"],
                        "completed should be True when prev_elapsed >= threshold (270/300)")

    def test_update_ui_disabled_stats_no_row_open(self):
        """stats.enabled=False should not open/close rows."""
        self._dash = self._make_dashboard(stats_enabled=False)
        self.assertIsNotNone(self._dash._stats, "stats object still exists when disabled")
        self.assertFalse(self._dash._stats.enabled, "stats should be disabled")
        # Sending playing status must not open a row
        self._open_row()
        self.assertFalse(self._dash._play_row_active, "Disabled stats should not open rows")

    def test_update_ui_short_track_completion(self):
        """3s track at 2.5s elapsed: threshold=1.0 → completed=True on stop."""
        self._dash = self._make_dashboard(stats_enabled=True)
        # Open a row on a 3s track at 2.5s elapsed (> threshold 1.0)
        self._open_row(elapsed=2.5, duration=3.0)
        self.assertTrue(self._dash._play_row_active, "Playing poll should open a row")
        # Stop: threshold(3.0) = 1.0, prev_elapsed 2.5 >= 1.0 → completed
        self._drive_update_ui(
            {"state": "stop", "elapsed": 2.5, "duration": 3.0, "volume": "50"},
            {"file": "a.mp3", "id": "1", "title": "T", "artist": "A", "album": "Al"},
        )
        self.assertFalse(self._dash._play_row_active, "Row should be finalized")
        rows = self._all_rows(self._dash._stats)
        self.assertEqual(len(rows), 1, "Exactly one row expected")
        self.assertTrue(rows[0]["completed"], "short track at 2.5/3.0 should be completed")

    def test_update_ui_zero_duration_never_complete(self):
        """duration=0 → _completion_threshold(0)=inf → finalize is never 'completed'."""
        self._dash = self._make_dashboard(stats_enabled=True)
        # Open a row on a zero-duration track (duration unknown)
        self._open_row(elapsed=100.0, duration=0.0)
        self.assertTrue(self._dash._play_row_active, "Playing poll should still open a row")
        # Stopped transition: threshold(0)=inf → 100 >= inf is False → completed=False
        self._drive_update_ui(
            {"state": "stop", "elapsed": 100.0, "duration": 0.0, "volume": "50"},
            {"file": "a.mp3", "id": "1", "title": "T", "artist": "A", "album": "Al"},
        )
        self.assertFalse(self._dash._play_row_active, "Row should be finalized on stop")
        rows = self._all_rows(self._dash._stats)
        self.assertEqual(len(rows), 1, "Exactly one row expected")
        self.assertFalse(rows[0]["completed"], "zero-duration track must never be completed")


    # --- config ---

    def test_config_stats_keys_exist(self):
        """Config DEFAULT_CONFIG includes stats keys."""
        config = Config()
        enabled = config.get("stats.enabled")
        db_path = config.get("stats.db_path")
        max_size = config.get("stats.max_size_mb")
        retention = config.get("stats.retention_days")

        check("stats.enabled defaults to True", enabled is True)
        check("stats.db_path has default", db_path is not None)
        check("stats.max_size_mb defaults to 10", max_size == 10)
        check("stats.retention_days defaults to 365", retention == 365)


def run_all_tests():
    """Run all tests and print summary."""
    suite = unittest.TestLoader().loadTestsFromTestCase(Slice22TestCase)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    passed = result.testsRun - len(result.failures) - len(result.errors)
    failed = len(result.failures) + len(result.errors)
    print(f"\n{'='*50}")
    print(f"Tests run: {result.testsRun}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"{'='*50}")
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)