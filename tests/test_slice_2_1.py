"""Slice 2.1 Test Script — Database Schema & Event Capture (Play Statistics)

Usage:
    python3 tests/test_slice_2_1.py

Usage for quick import check:
    python3 -c "from tests.test_slice_2_1 import run_all_tests; run_all_tests()"
"""

import sys
import os
import tempfile
import time
import shutil
import unittest

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


class Slice21TestCase(unittest.TestCase):
    """Unit tests for PlayStats SQLite database and event capture."""

    def setUp(self):
        self.tmpdirs = []

    def tearDown(self):
        for d in self.tmpdirs:
            shutil.rmtree(d, ignore_errors=True)

    # --- PlayStats Core Functionality ---

    def test_record_play_start(self):
        """record_play_start inserts a row with started_at."""
        tmpdir = tempfile.mkdtemp()
        self.tmpdirs.append(tmpdir)
        db_path = os.path.join(tmpdir, "test.db")

        stats = PlayStats(db_path=db_path)
        try:
            result = stats.record_play_start({
                'file': '/music/artist/album/track.flac',
                'artist': 'Test Artist',
                'album': 'Test Album',
                'title': 'Test Track',
                'duration': 180000
            })
            check("record_play_start returns True", result is True)

            # Verify row exists after ending
            stats.record_play_end(completed=True)
            time.sleep(0.01)
            plays = stats.get_recent_plays(limit=5)
            check("Record appears in recent plays", len(plays) == 1)
            if plays:
                p = plays[0]
                check("Artist matches", p.get("artist") == "Test Artist")
                check("Album matches", p.get("album") == "Test Album")
                check("Title matches", p.get("title") == "Test Track")
                check("Duration matches", p.get("duration_ms") == 180000)
                check("started_at is set", p.get("started_at") is not None)
                check("ended_at is set", p.get("ended_at") is not None)
                check("completed is True", p.get("completed") is True)
                check("skipped is False", p.get("skipped") is False)
        finally:
            stats.close()

    def test_record_play_end_completed(self):
        """record_play_end with completed=True marks row as completed."""
        tmpdir = tempfile.mkdtemp()
        self.tmpdirs.append(tmpdir)
        db_path = os.path.join(tmpdir, "test.db")

        stats = PlayStats(db_path=db_path)
        try:
            stats.record_play_start({
                'file': '/music/artist/album/track.flac',
                'artist': 'Test Artist',
                'album': 'Test Album',
                'title': 'Test Track',
                'duration': 180000
            })
            time.sleep(0.1)
            result = stats.record_play_end(completed=True)
            check("record_play_end(completed=True) returns True", result is True)

            plays = stats.get_recent_plays(limit=5)
            check("Record marked as completed", len(plays) == 1 and plays[0].get("completed") is True)
            check("ended_at is set", plays[0].get("ended_at") is not None)
            check("skipped is False", plays[0].get("skipped") is False)
        finally:
            stats.close()

    def test_record_play_end_skipped(self):
        """record_play_end with skipped=True marks row as skipped."""
        tmpdir = tempfile.mkdtemp()
        self.tmpdirs.append(tmpdir)
        db_path = os.path.join(tmpdir, "test.db")

        stats = PlayStats(db_path=db_path)
        try:
            stats.record_play_start({
                'file': '/music/artist/album/track.flac',
                'artist': 'Test Artist',
                'album': 'Test Album',
                'title': 'Test Track',
                'duration': 180000
            })
            time.sleep(0.1)
            result = stats.record_play_end(completed=False, skipped=True)
            check("record_play_end(skipped=True) returns True", result is True)

            plays = stats.get_recent_plays(limit=5)
            check("Record marked as skipped", len(plays) == 1 and plays[0].get("skipped") is True)
            check("completed is False", plays[0].get("completed") is False)
        finally:
            stats.close()

    def test_get_recent_plays(self):
        """get_recent_plays returns correct rows in descending order."""
        tmpdir = tempfile.mkdtemp()
        self.tmpdirs.append(tmpdir)
        db_path = os.path.join(tmpdir, "test.db")

        stats = PlayStats(db_path=db_path)
        try:
            # Insert 3 plays
            for i in range(3):
                stats.record_play_start({
                    'file': f'/music/track{i}.flac',
                    'artist': f'Artist {i}',
                    'album': 'Album',
                    'title': f'Track {i}',
                    'duration': 180000
                })
                time.sleep(0.01)
                stats.record_play_end(completed=True)

            plays = stats.get_recent_plays(limit=5)
            check("Returns all 3 plays", len(plays) == 3)
            # Should be in descending order (most recent first)
            check("Most recent first (Track 2)", plays[0]["title"] == "Track 2")
            check("Second is Track 1", plays[1]["title"] == "Track 1")
            check("Third is Track 0", plays[2]["title"] == "Track 0")

            # Test limit
            plays_limited = stats.get_recent_plays(limit=2)
            check("Limit parameter works", len(plays_limited) == 2)
        finally:
            stats.close()

    def test_get_total_plays(self):
        """get_total_plays returns correct count of completed plays."""
        tmpdir = tempfile.mkdtemp()
        self.tmpdirs.append(tmpdir)
        db_path = os.path.join(tmpdir, "test.db")

        stats = PlayStats(db_path=db_path)
        try:
            check("Total plays is 0 initially", stats.get_total_plays() == 0)

            # Add 2 completed plays
            for i in range(2):
                stats.record_play_start({
                    'file': f'/music/track{i}.flac',
                    'artist': 'Artist',
                    'album': 'Album',
                    'title': f'Track {i}',
                    'duration': 180000
                })
                stats.record_play_end(completed=True)

            check("Total plays is 2 after 2 completions", stats.get_total_plays() == 2)

            # Add a skipped play (should not count)
            stats.record_play_start({
                'file': '/music/track_skipped.flac',
                'artist': 'Artist',
                'album': 'Album',
                'title': 'Skipped Track',
                'duration': 180000
            })
            stats.record_play_end(completed=False, skipped=True)

            check("Skipped track not counted in total", stats.get_total_plays() == 2)
        finally:
            stats.close()

    def test_get_artist_stats(self):
        """get_artist_stats returns correct aggregates for an artist."""
        tmpdir = tempfile.mkdtemp()
        self.tmpdirs.append(tmpdir)
        db_path = os.path.join(tmpdir, "test.db")

        stats = PlayStats(db_path=db_path)
        try:
            # Add 3 plays by same artist (2 completed, 1 skipped)
            for i in range(2):
                stats.record_play_start({
                    'file': f'/music/artist/track{i}.flac',
                    'artist': 'Test Artist',
                    'album': 'Album',
                    'title': f'Track {i}',
                    'duration': 180000  # 180s each
                })
                stats.record_play_end(completed=True)

            # One skipped (duration not counted)
            stats.record_play_start({
                'file': '/music/artist/track_skipped.flac',
                'artist': 'Test Artist',
                'album': 'Album',
                'title': 'Skipped Track',
                'duration': 180000
            })
            stats.record_play_end(completed=False, skipped=True)

            stats_data = stats.get_artist_stats('Test Artist')
            check("Artist stats plays = 2 (only completed)", stats_data.get("plays") == 2)
            check("Artist stats playtime_ms = 360000", stats_data.get("playtime_ms") == 360000)
        finally:
            stats.close()

    # --- Persistence ---

    def test_records_survive_close_and_reopen(self):
        """Records survive close() and reopening the database."""
        tmpdir = tempfile.mkdtemp()
        self.tmpdirs.append(tmpdir)
        db_path = os.path.join(tmpdir, "test.db")

        # First session: insert 2 plays
        stats = PlayStats(db_path=db_path)
        try:
            stats.record_play_start({
                'file': '/music/track1.flac',
                'artist': 'Artist 1',
                'album': 'Album 1',
                'title': 'Track 1',
                'duration': 180000
            })
            stats.record_play_end(completed=True)

            stats.record_play_start({
                'file': '/music/track2.flac',
                'artist': 'Artist 2',
                'album': 'Album 2',
                'title': 'Track 2',
                'duration': 240000
            })
            stats.record_play_end(completed=True)
        finally:
            stats.close()

        # Second session: reopen and verify
        stats2 = PlayStats(db_path=db_path)
        try:
            plays = stats2.get_recent_plays(limit=5)
            check("Records survive close/reopen", len(plays) == 2)
            check("First track preserved", any(p["title"] == "Track 1" for p in plays))
            check("Second track preserved", any(p["title"] == "Track 2" for p in plays))
            check("Total plays = 2", stats2.get_total_plays() == 2)
        finally:
            stats2.close()

    def test_stats_disabled(self):
        """Stats no-op when disabled via enabled=False."""
        tmpdir = tempfile.mkdtemp()
        self.tmpdirs.append(tmpdir)
        db_path = os.path.join(tmpdir, "test.db")

        stats = PlayStats(db_path=db_path, enabled=False)
        try:
            result_start = stats.record_play_start({
                'file': '/music/track.flac',
                'artist': 'Artist',
                'album': 'Album',
                'title': 'Track',
                'duration': 180000
            })
            result_end = stats.record_play_end(completed=True)
            check("record_play_start returns False when disabled", result_start is False)
            check("record_play_end returns False when disabled", result_end is False)
            check("No records inserted when disabled", stats.get_total_plays() == 0)
        finally:
            stats.close()

    # --- Config integration ---

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

    def test_config_stats_persisted(self):
        """Stats config values can be persisted."""
        tmpdir = tempfile.mkdtemp()
        self.tmpdirs.append(tmpdir)
        config_path = os.path.join(tmpdir, "config.json")

        cfg = Config(config_path)
        cfg.set("stats.enabled", False)
        cfg.set("stats.max_size_mb", 5)
        cfg.save()

        cfg2 = Config(config_path)
        check("stats.enabled persisted as False", cfg2.get("stats.enabled") is False)
        check("stats.max_size_mb persisted as 5", cfg2.get("stats.max_size_mb") == 5)

    def test_config_non_dict_raises_valueerror(self):
        """Config loading [] raises ValueError (not AttributeError)."""
        tmpdir = tempfile.mkdtemp()
        self.tmpdirs.append(tmpdir)
        config_path = os.path.join(tmpdir, "config.json")

        with open(config_path, "w") as f:
            f.write("[]")

        try:
            Config(config_path)
            check("Should raise ValueError for [] config", False)
        except ValueError as e:
            check("[] config raises ValueError", "JSON object" in str(e))
        except Exception as e:
            check("Should raise ValueError, not other exception", False)

    # --- Edge cases ---

    def test_get_artist_stats_nonexistent(self):
        """get_artist_stats returns zeros for unknown artist."""
        tmpdir = tempfile.mkdtemp()
        self.tmpdirs.append(tmpdir)
        db_path = os.path.join(tmpdir, "test.db")

        stats = PlayStats(db_path=db_path)
        try:
            stats_data = stats.get_artist_stats("Unknown Artist")
            check("Unknown artist returns 0 plays", stats_data.get("plays") == 0)
            check("Unknown artist returns 0 playtime", stats_data.get("playtime_ms") == 0)
        finally:
            stats.close()

    def test_get_recent_plays_empty(self):
        """get_recent_plays returns empty list on empty DB."""
        tmpdir = tempfile.mkdtemp()
        self.tmpdirs.append(tmpdir)
        db_path = os.path.join(tmpdir, "test.db")

        stats = PlayStats(db_path=db_path)
        try:
            plays = stats.get_recent_plays(limit=5)
            check("Empty DB returns empty list", plays == [])
        finally:
            stats.close()


def run_all_tests():
    """Run all Slice 2.1 acceptance tests."""
    print("=" * 60)
    print("Slice 2.1: Database Schema & Event Capture (Play Statistics)")
    print("=" * 60)

    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(Slice21TestCase)
    runner = unittest.TextTestRunner(verbosity=1)
    result = runner.run(suite)

    if not result.wasSuccessful():
        print("\n[WARN] Slice 2.1: Unit tests failed")
        return False

    total = len(RESULTS)
    passed = sum(1 for s, _ in RESULTS if s == "PASS")
    print(f"\nResults: {passed}/{total} checks passed")

    if passed == total:
        print("\n[OK] Slice 2.1: ACCEPTANCE CRITERIA MET")
        return True
    else:
        print(f"\n[WARN] Slice 2.1: {total - passed} check(s) failed")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)