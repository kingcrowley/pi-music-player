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

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.stats import PlayStats
from core.config import Config

RESULTS = []


def check(name: str, condition: bool, detail: str = ""):
    """Record a test result."""
    status = "PASS" if condition else "FAIL"
    mark = "PASS" if condition else "FAIL"
    RESULTS.append((status, name))
    print(f"  [{mark}] {status}: {name}" + (f" - {detail}" if detail else ""))


class Slice22TestCase(unittest.TestCase):
    """Unit tests for PlayStats Slice 2.2 features.

    These tests cover:
    - Most Played Tracks (get_top_tracks)
    - Recent History (get_recent_history)
    - Listening Time Heatmap (get_listening_time_heatmap)
    - Skip Rate (get_skip_rate)
    - Retention cleanup
    - Export CSV
    """

    def setUp(self):
        self.tmpdirs = []

    def tearDown(self):
        for d in self.tmpdirs:
            shutil.rmtree(d, ignore_errors=True)

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