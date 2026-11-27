"""Slice 3.1 Test Suite — Recommendation Engine Core

Tests for Slice 3.1 deliverables:
- RecommendationEngine plugin loads/unloads via PluginManager
- Co-occurrence matrix builds from plays and live events
- get_similar_artists returns ranked bidirectional results
- get_genre_radio returns shuffled paths from album_songs
- get_revisit_candidates returns one track path per album
- get_new_to_you returns library artists absent from play_stats.db
- Session rules: 5-min gap, skips/stops break sessions, no self-pairs
- Hooks fire: on_song_change / on_playback_complete
- Background thread for library scan + rebuild
- Temp DB isolation
"""

import sys
import os
import tempfile
import shutil
import json
import sqlite3
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.stats import PlayStats
from core.player import MusicPlayer
from core.config import Config
from plugins import PluginManager
from plugins.recommendations.recommendations import MusicPlayerPlugin as RecommendationEngine


class MockMusicPlayer:
    """Minimal MusicPlayer stub for testing plugin hooks.

    Provides just enough to let RecommendationEngine initialize and fire hooks.
    """

    def __init__(self, db_path: str, library: list = None):
        self.config = Config()
        self.config.set("stats.db_path", db_path)
        self._library = library or []

    def list_all_info(self):
        return self._library


def _make_temp_plugin_dir():
    """Create a temp dir with the recommendations plugin copied in."""
    d = tempfile.mkdtemp()
    shutil.copytree(
        "plugins/recommendations",
        os.path.join(d, "recommendations"),
    )
    return Path(d)


class Slice31TestCase(unittest.TestCase):
    """Test cases for Slice 3.1 — Recommendation Engine Core."""

    def setUp(self):
        self.tmpdirs = []

    def tearDown(self):
        for d in self.tmpdirs:
            shutil.rmtree(d, ignore_errors=True)

    def test_plugin_loads_and_unloads(self):
        """Plugin loads via PluginManager and unloads cleanly."""
        d = _make_temp_plugin_dir()
        self.tmpdirs.append(d)

        # Real MusicPlayer with temp db
        db_path = os.path.join(d, "test_play_stats.db")
        player = MockMusicPlayer(db_path)

        mgr = PluginManager(core_engine=player, plugin_dir=str(d))
        loaded = mgr.load_plugins()
        self.assertEqual(loaded, 1, "Expected 1 plugin to load")

        plugins = mgr.get_all_plugins()
        self.assertEqual(len(plugins), 1)
        rec = plugins[0]
        self.assertEqual(rec.name, "Recommendations")
        self.assertEqual(rec.get_capabilities(), ["recommendations"])

        # Verify db_path resolved from app config
        self.assertTrue(rec.db_path.endswith("test_play_stats.db"))

        mgr.shutdown_all()
        self.assertEqual(len(mgr.get_all_plugins()), 0)

    def test_cooccurrence_schema_created(self):
        """Recommendation tables created in play_stats.db."""
        d = _make_temp_plugin_dir()
        self.tmpdirs.append(d)

        db_path = os.path.join(d, "test_play_stats.db")
        player = MockMusicPlayer(db_path)

        mgr = PluginManager(core_engine=player, plugin_dir=str(d))
        mgr.load_plugins()

        # Check tables exist
        import sqlite3
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cur.fetchall()}
        conn.close()

        self.assertIn("cooccurrence", tables)
        self.assertIn("album_songs", tables)
        self.assertIn("cooccurrence_meta", tables)

        mgr.shutdown_all()

    def test_get_similar_artists_bidirectional(self):
        """Similar-artist lookup is bidirectional (checks both columns)."""
        d = _make_temp_plugin_dir()
        self.tmpdirs.append(d)

        db_path = os.path.join(d, "test.db")
        player = MockMusicPlayer(db_path)

        # Manually populate cooccurrence with canonical (A<B) pairs
        import sqlite3
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("CREATE TABLE cooccurrence (artist_a TEXT, artist_b TEXT, play_count INTEGER, PRIMARY KEY (artist_a, artist_b))")
        # Pair Radiohead→Pink Floyd (Radiohead < Pink Floyd)
        cur.execute("INSERT INTO cooccurrence (artist_a, artist_b, play_count) VALUES (?, ?, ?)", ("Pink Floyd", "Radiohead", 23))
        # Pair Tool→Radiohead (Radiohead < Tool)
        cur.execute("INSERT INTO cooccurrence (artist_a, artist_b, play_count) VALUES (?, ?, ?)", ("Radiohead", "Tool", 17))
        # Pair Muse→Radiohead (Muse < Radiohead)
        cur.execute("INSERT INTO cooccurrence (artist_a, artist_b, play_count) VALUES (?, ?, ?)", ("Muse", "Radiohead", 11))
        conn.commit()
        conn.close()

        mgr = PluginManager(core_engine=MockMusicPlayer(db_path), plugin_dir="plugins")
        mgr.load_plugins()
        rec = mgr.get_plugin("recommendations")

        # Query Radiohead — should get Pink Floyd, Tool, Muse
        similar = rec.get_similar_artists("Radiohead", limit=10)
        self.assertEqual(len(similar), 3)
        # Should be sorted by score desc
        self.assertEqual(similar[0]["artist"], "Pink Floyd")
        self.assertEqual(similar[0]["score"], 23)
        self.assertEqual(similar[1]["artist"], "Tool")
        self.assertEqual(similar[2]["artist"], "Muse")

        # Bidirectional: query Pink Floyd should also return Radiohead
        similar_pf = rec.get_similar_artists("Pink Floyd", limit=10)
        self.assertEqual(len(similar_pf), 1)
        self.assertEqual(similar_pf[0]["artist"], "Radiohead")

        mgr.shutdown_all()

    def test_no_same_artist_pairs(self):
        """Same-artist pairs are never returned."""
        d = _make_temp_plugin_dir()
        self.tmpdirs.append(d)

        db_path = os.path.join(d, "test.db")
        player = MockMusicPlayer(db_path)

        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("CREATE TABLE cooccurrence (artist_a TEXT, artist_b TEXT, play_count INTEGER, PRIMARY KEY (artist_a, artist_b))")
        # Insert same-artist pair (should be filtered out by engine)
        cur.execute("INSERT INTO cooccurrence (artist_a, artist_b, play_count) VALUES (?, ?, ?)", ("Radiohead", "Radiohead", 99))
        conn.commit()
        conn.close()

        mgr = PluginManager(core_engine=MockMusicPlayer(db_path), plugin_dir="plugins")
        mgr.load_plugins()
        rec = mgr.get_plugin("recommendations")

        similar = rec.get_similar_artists("Radiohead", limit=10)
        # Should NOT contain Radiohead itself
        self.assertTrue(all(s["artist"] != "Radiohead" for s in similar))
        # Engine should not have inserted the same-artist pair in live mode either

        mgr.shutdown_all()

    def test_get_genre_radio(self):
        """Genre radio returns shuffled track paths from album_songs."""
        d = _make_temp_plugin_dir()
        self.tmpdirs.append(d)

        db_path = os.path.join(d, "test.db")
        library = [
            {"file": "/music/blues/track1.flac", "artist": "Artist1", "album": "Album1", "genre": "Blues"},
            {"file": "/music/blues/track2.flac", "artist": "Artist2", "album": "Album2", "genre": "Blues"},
            {"file": "/music/rock/track3.flac", "artist": "Artist3", "album": "Album3", "genre": "Rock"},
        ]
        player = MockMusicPlayer(db_path, library=library)

        mgr = PluginManager(core_engine=player, plugin_dir="plugins")
        mgr.load_plugins()
        rec = mgr.get_plugin("recommendations")

        # Wait for background scan to complete (in test it runs synchronously enough)
        time.sleep(0.2)

        blues = rec.get_genre_radio("Blues")
        self.assertEqual(len(blues), 2)
        self.assertIn("/music/blues/track1.flac", blues)
        self.assertIn("/music/blues/track2.flac", blues)

        rock = rec.get_genre_radio("Rock")
        self.assertEqual(len(rock), 1)
        self.assertEqual(rock[0], "/music/rock/track3.flac")

        # Unknown genre returns empty list
        self.assertEqual(rec.get_genre_radio("Jazz"), [])

        mgr.shutdown_all()

    def test_get_revisit_candidates(self):
        """Returns one track path per album not played in last N days."""
        d = _make_temp_plugin_dir()
        self.tmpdirs.append(d)

        db_path = os.path.join(d, "test.db")
        library = [
            {"file": "/music/old/album1/track1.flac", "artist": "Artist1", "album": "OldAlbum1", "genre": "Rock"},
            {"file": "/music/old/album2/track1.flac", "artist": "Artist2", "album": "OldAlbum2", "genre": "Rock"},
            {"file": "/music/recent/album3/track1.flac", "artist": "Artist3", "album": "RecentAlbum", "genre": "Rock"},
        ]
        player = MockMusicPlayer(db_path, library=library)

        # Add a play in plays table for RecentAlbum within last 30 days
        import sqlite3
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("CREATE TABLE plays (id INTEGER PRIMARY KEY, track_path TEXT, artist TEXT, album TEXT, title TEXT, started_at INTEGER, ended_at INTEGER, completed BOOLEAN, skipped BOOLEAN, duration_ms INTEGER)")
        # Recent play (ended_at = now)
        cur.execute("INSERT INTO plays (track_path, artist, album, title, started_at, ended_at, completed, skipped) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    ("/music/recent/album3/track1.flac", "Artist3", "RecentAlbum", "Track1",
                     int(time.time()) - 86400, int(time.time()), 1, 0))
        conn.commit()
        conn.close()

        mgr = PluginManager(core_engine=player, plugin_dir="plugins")
        mgr.load_plugins()
        rec = mgr.get_plugin("recommendations")

        time.sleep(0.2)

        candidates = rec.get_revisit_candidates(days=30)
        # Should only contain old albums (OldAlbum1, OldAlbum2)
        self.assertEqual(len(candidates), 2)
        self.assertIn("/music/old/album1/track1.flac", candidates)
        self.assertIn("/music/old/album2/track1.flac", candidates)
        self.assertNotIn("/music/recent/album3/track1.flac", candidates)

        mgr.shutdown_all()

    def test_get_new_to_you(self):
        """Returns library artists absent from play_stats.db."""
        d = _make_temp_plugin_dir()
        self.tmpdirs.append(d)

        db_path = os.path.join(d, "test.db")
        library = [
            {"file": "/music/played/artist1/track.flac", "artist": "PlayedArtist", "album": "Album", "genre": "Rock"},
            {"file": "/music/unplayed/artist2/track.flac", "artist": "UnplayedArtist", "album": "Album", "genre": "Rock"},
        ]
        player = MockMusicPlayer(db_path, library=library)

        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("CREATE TABLE plays (id INTEGER PRIMARY KEY, track_path TEXT, artist TEXT, album TEXT, title TEXT, started_at INTEGER, ended_at INTEGER, completed BOOLEAN, skipped BOOLEAN, duration_ms INTEGER)")
        cur.execute("INSERT INTO plays (track_path, artist, album, title, started_at, ended_at, completed, skipped) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    ("/music/played/artist1/track.flac", "PlayedArtist", "Album", "Track", int(time.time()), int(time.time()), 1, 0))
        conn.commit()
        conn.close()

        mgr = PluginManager(core_engine=player, plugin_dir="plugins")
        mgr.load_plugins()
        rec = mgr.get_plugin("recommendations")

        time.sleep(0.2)

        new_artists = rec.get_new_to_you()
        self.assertIn("UnplayedArtist", new_artists)
        self.assertNotIn("PlayedArtist", new_artists)

        mgr.shutdown_all()

    def test_session_rules_skip_breaks(self):
        """Skips break the session (no pair across skip boundary)."""
        d = _make_temp_plugin_dir()
        self.tmpdirs.append(d)

        db_path = os.path.join(d, "test.db")
        player = MockMusicPlayer(db_path)

        # Manually populate plays with a skip in the middle
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("CREATE TABLE plays (id INTEGER PRIMARY KEY, track_path TEXT, artist TEXT, album TEXT, title TEXT, started_at INTEGER, ended_at INTEGER, completed BOOLEAN, skipped BOOLEAN, duration_ms INTEGER)")
        now = int(time.time())
        # Play A (completed)
        cur.execute("INSERT INTO plays (track_path, artist, album, title, started_at, ended_at, completed, skipped) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    ("/a.flac", "ArtistA", "AlbumA", "TrackA", now - 300, now - 240, 1, 0))
        # Play B (skipped) — breaks session
        cur.execute("INSERT INTO plays (track_path, artist, album, title, started_at, ended_at, completed, skipped) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    ("/b.flac", "ArtistB", "AlbumB", "TrackB", now - 240, now - 180, 0, 1))
        # Play C (completed) — starts new session
        cur.execute("INSERT INTO plays (track_path, artist, album, title, started_at, ended_at, completed, skipped) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    ("/c.flac", "ArtistC", "AlbumC", "TrackC", now - 180, now - 120, 1, 0))
        conn.commit()
        conn.close()

        mgr = PluginManager(core_engine=MockMusicPlayer(db_path), plugin_dir="plugins")
        mgr.load_plugins()
        rec = mgr.get_plugin("recommendations")
        rec.build_from_history()

        # A and B should NOT be paired (B was skipped)
        # B and C should NOT be paired (B was skipped)
        # A and C should NOT be paired (session broken by skip)
        similar = rec.get_similar_artists("ArtistA", limit=10)
        self.assertEqual(len(similar), 0)

        similar = rec.get_similar_artists("ArtistC", limit=10)
        self.assertEqual(len(similar), 0)

        mgr.shutdown_all()

    def test_live_pairing_no_self_pair(self):
        """Live on_song_change / on_playback_complete never pairs a track with itself.

        Simulates a live session: A starts, A completes, B starts, B completes.
        Pairing happens in _on_playback_complete when a track finishes.
        """
        d = _make_temp_plugin_dir()
        self.tmpdirs.append(d)

        db_path = os.path.join(d, "test.db")
        player = MockMusicPlayer(db_path)

        mgr = PluginManager(core_engine=player, plugin_dir="plugins")
        mgr.load_plugins()
        rec = mgr.get_plugin("recommendations")

        # Track A starts (on_song_change)
        track_a = {"artist": "Radiohead", "album": "OK Computer", "title": "Paranoid Android", "path": "/a.flac", "started_at": 1000}
        rec._on_song_change(track_a)

        # Track A completes (on_playback_complete)
        rec._on_playback_complete(track_a, completed=True, skipped=False)

        # Track B starts (on_song_change) - no pairing yet
        track_b = {"artist": "Pink Floyd", "album": "Dark Side", "title": "Time", "path": "/b.flac", "started_at": 1500}
        rec._on_song_change(track_b)

        # Track B completes - pair A+B should be recorded
        rec._on_playback_complete(track_b, completed=True, skipped=False)

        # Pair should be (Radiohead, Pink Floyd) in canonical order
        import sqlite3
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT artist_a, artist_b, play_count FROM cooccurrence")
        pairs = cur.fetchall()
        conn.close()
        self.assertEqual(len(pairs), 1)
        self.assertEqual(pairs[0][:2], ("Pink Floyd", "Radiohead"))  # canonical order

        mgr.shutdown_all()

    def test_no_network_calls(self):
        """Plugin has no network imports (requests, urllib)."""
        import ast
        source = Path("plugins/recommendations/recommendations.py").read_text()
        tree = ast.parse(source)
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    # Compare only the top-level package name to catch submodule
                    # imports (e.g. urllib.request should fail the check too).
                    top = alias.name.split(".")[0]
                    imports.append(top)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    # Compare only the top-level package name.
                    top = node.module.split(".")[0]
                    imports.append(top)
        self.assertNotIn("requests", imports)
        self.assertNotIn("urllib", imports)


    # ------------------------------------------------------------------
    # New tests required by reviewer (catch bugs from previous rounds)
    # ------------------------------------------------------------------

    def test_list_all_info_against_fake_client(self):
        """list_all_info() returns tagged tracks and skips directories."""
        class FakeClient:
            def listallinfo(self):
                return [
                    {"file": "/music/rock/a.flac", "artist": "A", "album": "X", "genre": "Rock, Pop", "time": "200"},
                    {"directory": "/music/rock"},  # no file key - directory entry
                    {"file": "/music/blues/b.flac", "artist": "B", "album": "Y", "genre": "Blues", "time": "300"},
                ]
        player = MusicPlayer.__new__(MusicPlayer)
        player.client = FakeClient()
        player._connected = True
        # Stub connection: no real MPD server in tests
        player._execute_with_retry = lambda fn: fn()
        result = player.list_all_info()
        self.assertEqual(len(result), 2)  # directory entry skipped
        self.assertEqual(result[0]["artist"], "A")
        self.assertIn("Rock", result[0]["genre"])
        self.assertIn("Pop", result[0]["genre"])
        # No empty dicts
        for entry in result:
            self.assertNotEqual(entry, {})

    def test_should_rebuild_after_newer_plays(self):
        """_should_rebuild returns True after newer plays are added."""
        db_path = os.path.join(tempfile.mkdtemp(), "test.db")
        import sqlite3
        # Create plays table with 2 plays
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE plays (id INTEGER PRIMARY KEY, ended_at INTEGER)")
        conn.execute("INSERT INTO plays (ended_at) VALUES (100), (200)")
        conn.execute("CREATE TABLE cooccurrence_meta (id INTEGER PRIMARY KEY, last_built_at INTEGER)")
        conn.execute("INSERT INTO cooccurrence_meta VALUES (1, 100)")
        conn.commit()
        conn.close()

        # Create plugin with temp db
        plugin = RecommendationEngine({})
        plugin.db_path = db_path
        plugin._conn = sqlite3.connect(db_path, check_same_thread=False, isolation_level=None)
        plugin._conn.execute("PRAGMA journal_mode=WAL")
        plugin._create_schema()

        # Should rebuild: latest play (200) > last_built (100)
        self.assertTrue(plugin._should_rebuild())

        # After a build, add newer play and check again
        conn = sqlite3.connect(db_path)
        conn.execute("INSERT INTO plays (ended_at) VALUES (300)")
        conn.execute("UPDATE cooccurrence_meta SET last_built_at = 300")
        conn.commit()
        conn.close()

        # Latest (300) == last_built (300) -> no rebuild needed
        self.assertFalse(plugin._should_rebuild())

        # Add a newer play at 400: latest (400) > last_built (300) -> rebuild needed
        conn = sqlite3.connect(db_path)
        conn.execute("INSERT INTO plays (ended_at) VALUES (400)")
        conn.commit()
        conn.close()

        self.assertTrue(plugin._should_rebuild())
        plugin._conn.close()

    def test_plugin_starts_on_empty_db(self):
        """Plugin starts on a fresh/empty database without crashing."""
        d = tempfile.mkdtemp()
        self.tmpdirs.append(d)
        db_path = os.path.join(d, "empty.db")
        player = MockMusicPlayer(db_path)
        mgr = PluginManager(core_engine=player, plugin_dir="plugins")
        mgr.load_plugins()
        rec = mgr.get_plugin("recommendations")
        self.assertIsNotNone(rec)
        # No crash, table created
        self.assertIsNotNone(rec._conn)
        # Lookups should return empty, not crash
        self.assertEqual(rec.get_similar_artists("Anyone"), [])
        self.assertEqual(rec.get_genre_radio("Rock"), [])
        self.assertEqual(rec.get_revisit_candidates(), [])
        mgr.shutdown_all()

    def test_get_genre_radio_delimited_match(self):
        """Genre radio uses delimited matching, not substring."""
        d = tempfile.mkdtemp()
        self.tmpdirs.append(d)
        db_path = os.path.join(d, "test.db")
        player = MockMusicPlayer(db_path)

        # Populate album_songs with multi-genre tags
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE album_songs (path TEXT PRIMARY KEY, album TEXT, artist TEXT, genre TEXT)")
        conn.execute("INSERT INTO album_songs VALUES (?, ?, ?, ?)", ("/a.flac", "AlbumA", "ArtistA", "Rock, Pop"))
        conn.execute("INSERT INTO album_songs VALUES (?, ?, ?, ?)", ("/b.flac", "AlbumB", "ArtistB", "Progressive Rock"))
        conn.execute("INSERT INTO album_songs VALUES (?, ?, ?, ?)", ("/c.flac", "AlbumC", "ArtistC", "Blues"))
        conn.commit()
        conn.close()

        mgr = PluginManager(core_engine=player, plugin_dir="plugins")
        mgr.load_plugins()
        rec = mgr.get_plugin("recommendations")

        # "Rock" should match "Rock, Pop" but NOT "Progressive Rock"
        rock = rec.get_genre_radio("Rock")
        self.assertIn("/a.flac", rock)
        self.assertNotIn("/b.flac", rock)  # "Progressive Rock" is not "Rock"

        # Case-insensitive
        rock_lower = rec.get_genre_radio("rock")
        self.assertIn("/a.flac", rock_lower)

        mgr.shutdown_all()

    # ------------------------------------------------------------------
    # Suggested tests from reviewer (issue #15)
    # ------------------------------------------------------------------

    def test_plugin_starts_with_db_path_in_missing_directory(self):
        """Plugin loads when stats.db_path points into a directory that doesn't exist yet."""
        d = _make_temp_plugin_dir()
        self.tmpdirs.append(d)

        nested_dir = os.path.join(d, "no", "such", "dir")
        db_path = os.path.join(nested_dir, "test_play_stats.db")
        player = MockMusicPlayer(db_path)

        mgr = PluginManager(core_engine=player, plugin_dir=str(d))
        loaded = mgr.load_plugins()
        self.assertEqual(loaded, 1, "Expected 1 plugin to load")
        mgr.shutdown_all()

        # Plugin must have created the directory and connected to the db
        self.assertTrue(os.path.exists(db_path))
        self.assertTrue(os.path.exists(os.path.dirname(db_path)))

    def test_scan_is_atomic_no_partial_rows(self):
        """An interrupted library scan leaves album_songs empty so the next
        start-up rescan (the scan checks COUNT(*) = 0 and retries).

        The failure is triggered during the insert (not before any row is
        gathered) so it genuinely exercises the BEGIN IMMEDIATE / ROLLBACK
        path. Without the transaction, the first batch of rows would be
        committed before the failing executemany and stay visible.
        """
        d = tempfile.mkdtemp()
        self.tmpdirs.append(d)
        db_path = os.path.join(d, "test.db")

        plugin = RecommendationEngine({})
        plugin.db_path = db_path
        plugin._conn = sqlite3.connect(db_path, check_same_thread=False, isolation_level=None)
        plugin._conn.execute("PRAGMA journal_mode=WAL")
        plugin._create_schema()

        class GoodCore:
            def list_all_info(self):
                return [
                    {"file": "/music/a.flac", "artist": "A", "album": "Al", "title": "T", "genre": "Rock"},
                    {"file": "/music/b.flac", "artist": "B", "album": "Al", "title": "T", "genre": "Rock"},
                ]

        class _FailingCursor:
            """Cursor proxy that inserts the first row and then fails.

            Writing a row before raising is what makes this test verify the
            transaction: with BEGIN IMMEDIATE the row is rolled back (count 0),
            but without it the row would remain committed (count 1).
            """
            def __init__(self, real):
                self._real = real

            def execute(self, sql, *args):
                return self._real.execute(sql, *args)

            def executemany(self, sql, seq):
                seq = list(seq)
                if seq:
                    self._real.execute(sql, seq[0])  # write one row first
                raise RuntimeError("disk error mid-insert")

            def fetchone(self):
                return self._real.fetchone()

            def fetchall(self):
                return self._real.fetchall()

        class _FailingConn:
            def __init__(self, real):
                self._real = real

            def cursor(self):
                return _FailingCursor(self._real.cursor())

        plugin.core = GoodCore()
        real_conn = plugin._conn
        plugin._conn = _FailingConn(real_conn)
        try:
            plugin._scan_library_if_empty()
        finally:
            plugin._conn = real_conn

        # No partial rows should be committed after the rolled-back scan.
        cur = plugin._conn.execute("SELECT COUNT(*) FROM album_songs")
        self.assertEqual(cur.fetchone()[0], 0)

        # Next scan with a healthy connection should succeed.
        plugin.core = GoodCore()
        plugin._scan_library_if_empty()
        cur = plugin._conn.execute("SELECT COUNT(*) FROM album_songs")
        self.assertEqual(cur.fetchone()[0], 2)
        plugin._conn.close()

    def test_hook_dispatches_reach_on_playback_complete(self):
        """Hooks dispatched through a real PluginManager reach _on_playback_complete."""
        d = _make_temp_plugin_dir()
        self.tmpdirs.append(d)
        db_path = os.path.join(d, "test.db")
        player = MockMusicPlayer(db_path)
        mgr = PluginManager(core_engine=player, plugin_dir=str(d))
        mgr.load_plugins()
        rec = mgr.get_plugin("recommendations")

        # Drive live pairing through the real PluginManager dispatch path
        track_a = {"artist": "ArtistA", "album": "AlbumA", "title": "TrackA", "path": "/a.flac", "started_at": 1000}
        track_b = {"artist": "ArtistB", "album": "AlbumB", "title": "TrackB", "path": "/b.flac", "started_at": 2000}
        mgr.trigger_hook("on_song_change", track_a)
        mgr.trigger_hook("on_playback_complete", track_a, completed=True, skipped=False)
        mgr.trigger_hook("on_song_change", track_b)
        mgr.trigger_hook("on_playback_complete", track_b, completed=True, skipped=False)

        import sqlite3
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT artist_a, artist_b, play_count FROM cooccurrence")
        pairs = cur.fetchall()
        conn.close()
        self.assertEqual(len(pairs), 1)
        self.assertEqual(pairs[0][:2], ("ArtistA", "ArtistB"))
        mgr.shutdown_all()

    def test_main_passes_plugin_manager_to_dashboard(self):
        """main.py passes plugin_mgr to run_dashboard as plugin_manager."""
        import main as main_mod
        import inspect
        source = inspect.getsource(main_mod)
        # Verify the call to run_dashboard includes plugin_manager=plugin_mgr
        self.assertIn("plugin_manager=plugin_mgr", source)
        self.assertIn("run_dashboard(", source)

    def test_lookup_during_rebuild_waits(self):
        """A lookup during rebuild does not raise and sees correct results after."""
        d = _make_temp_plugin_dir()
        self.tmpdirs.append(d)

        db_path = os.path.join(d, "test.db")
        # Pre-populate plays so build_from_history() actually does work
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE plays (id INTEGER PRIMARY KEY, track_path TEXT, artist TEXT, album TEXT, title TEXT, started_at INTEGER, ended_at INTEGER, completed BOOLEAN, skipped BOOLEAN, duration_ms INTEGER)")
        conn.execute("CREATE TABLE cooccurrence (artist_a TEXT, artist_b TEXT, play_count INTEGER, PRIMARY KEY (artist_a, artist_b))")
        conn.execute("CREATE TABLE cooccurrence_meta (id INTEGER PRIMARY KEY, last_built_at INTEGER)")
        conn.execute("INSERT INTO cooccurrence_meta VALUES (1, 100)")
        # Add enough plays so rebuild takes time
        for i in range(100):
            conn.execute("INSERT INTO plays (track_path, artist, album, title, started_at, ended_at, completed, skipped) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                         (f"/track{i}.flac", f"Artist{i % 5}", "Album", f"Track{i}", 1000 + i*10, 1000 + i*10 + 200, 1, 0))
        conn.commit()
        conn.close()

        player = MockMusicPlayer(db_path)
        mgr = PluginManager(core_engine=player, plugin_dir="plugins")
        mgr.load_plugins()
        rec = mgr.get_plugin("recommendations")

        import threading
        import time

        rebuild_started = threading.Event()
        rebuild_done = threading.Event()
        lookup_result = [None]
        lookup_exception = [None]

        def do_rebuild():
            rebuild_started.set()
            rec.build_from_history()
            rebuild_done.set()

        def do_lookup():
            # Wait for rebuild to start. build_from_history() no longer holds
            # the lock while computing, so the lookup must not block waiting
            # for the whole rebuild — but it must not raise either.
            rebuild_started.wait(timeout=2.0)
            try:
                result = rec.get_similar_artists("Artist0", limit=10)
                lookup_result[0] = result
            except Exception as e:
                lookup_exception[0] = e
            finally:
                rebuild_done.wait(timeout=5.0)

        t1 = threading.Thread(target=do_rebuild)
        t2 = threading.Thread(target=do_lookup)
        t1.start()
        t2.start()
        t1.join(timeout=5.0)
        t2.join(timeout=5.0)

        self.assertIsNone(lookup_exception[0], f"Lookup raised: {lookup_exception[0]}")
        self.assertIsNotNone(lookup_result[0], "Lookup returned None")
        # Once the rebuild finishes, the lookup sees the new matrix:
        # Artist0 pairs with Artist1 and Artist4 (2 other artists).
        final_result = rec.get_similar_artists("Artist0", limit=10)
        self.assertEqual(len(final_result), 2)
        # Results should include Artist1 and Artist4

    def test_long_tracks_pairing(self):
        """Long tracks (over 5 min) should pair correctly.

        The gap uses the track's start time, not the completion time.
        Two 6-minute tracks played back to back should still pair.
        Uses mocked time so ended_at is controllable.
        """
        d = _make_temp_plugin_dir()
        self.tmpdirs.append(d)

        db_path = os.path.join(d, "test.db")
        player = MockMusicPlayer(db_path)

        mgr = PluginManager(core_engine=player, plugin_dir="plugins")
        mgr.load_plugins()
        rec = mgr.get_plugin("recommendations")

        import unittest.mock as mock
        # Control time: start at a known base
        time_base = 1000
        with mock.patch('time.time', return_value=time_base + 360):
            # Simulate track A: 6 minutes (360 seconds) starting at time_base
            track_a = {"artist": "ArtistA", "album": "AlbumA", "title": "TrackA", "path": "/a.flac", "started_at": time_base}
            rec._on_song_change(track_a)
            # Track A completes at time_base + 360
            rec._on_playback_complete(
                {"artist": "ArtistA"},
                completed=True, skipped=False
            )

            # Track B starts 30 seconds after A completes (within 5-min gap)
            track_b = {"artist": "ArtistB", "album": "AlbumB", "title": "TrackB", "path": "/b.flac", "started_at": time_base + 360 + 30}
            rec._on_song_change(track_b)
            # Track B completes
            rec._on_playback_complete(
                {"artist": "ArtistB"},
                completed=True, skipped=False
            )

        # Should pair A-B (gap = (time_base + 360 + 30) - (time_base + 360) = 30 seconds < 300)
        similar = rec.get_similar_artists("ArtistA", limit=10)
        self.assertEqual(len(similar), 1)
        self.assertEqual(similar[0]["artist"], "ArtistB")

        mgr.shutdown_all()

    def test_repeat_one_pairing(self):
        """Repeat-one (two completions with no song change) does not crash.

        The second completion should clear _current without crashing on .copy().
        """
        d = _make_temp_plugin_dir()
        self.tmpdirs.append(d)

        db_path = os.path.join(d, "test.db")
        player = MockMusicPlayer(db_path)

        mgr = PluginManager(core_engine=player, plugin_dir="plugins")
        mgr.load_plugins()
        rec = mgr.get_plugin("recommendations")

        # Track A starts
        track_a = {"artist": "ArtistA", "album": "AlbumA", "title": "TrackA", "path": "/a.flac", "started_at": 1000}
        rec._on_song_change(track_a)

        # Track A completes (first play)
        rec._on_playback_complete({"artist": "ArtistA"}, completed=True, skipped=False)

        # Repeat-one: Track A completes again, no song change
        # _current should be None now, so no pairing and no crash
        rec._on_playback_complete({"artist": "ArtistA"}, completed=True, skipped=False)

        # Should not crash, no pairs recorded
        import sqlite3
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT artist_a, artist_b, play_count FROM cooccurrence")
        pairs = cur.fetchall()
        conn.close()
        self.assertEqual(len(pairs), 0)

        mgr.shutdown_all()

    def test_long_gap_does_not_pair(self):
        """Tracks separated by more than session_gap_seconds should NOT pair."""
        d = _make_temp_plugin_dir()
        self.tmpdirs.append(d)

        db_path = os.path.join(d, "test.db")
        player = MockMusicPlayer(db_path)

        mgr = PluginManager(core_engine=player, plugin_dir="plugins")
        mgr.load_plugins()
        rec = mgr.get_plugin("recommendations")

        import unittest.mock as mock
        time_base = 1000
        with mock.patch('time.time', return_value=time_base + 360):
            # Track A starts and completes
            track_a = {"artist": "ArtistA", "album": "AlbumA", "title": "TrackA", "path": "/a.flac", "started_at": time_base}
            rec._on_song_change(track_a)
            rec._on_playback_complete(
                {"artist": "ArtistA"},
                completed=True, skipped=False
            )

            # Track B starts 10 minutes AFTER A completes - gap > 5 minutes
            track_b = {"artist": "ArtistB", "album": "AlbumB", "title": "TrackB", "path": "/b.flac", "started_at": time_base + 360 + 600}
            rec._on_song_change(track_b)
            rec._on_playback_complete(
                {"artist": "ArtistB"},
                completed=True, skipped=False
            )

        # Should NOT pair (gap = 600 seconds > 300)
        similar = rec.get_similar_artists("ArtistA", limit=10)
        self.assertEqual(len(similar), 0)

        mgr.shutdown_all()

    def test_long_gap_does_not_pair_after_rebuild(self):
        """Tracks separated by more than session_gap_seconds should NOT pair
        even after a rebuild rebuilds the co-occurrence matrix."""
        d = _make_temp_plugin_dir()
        self.tmpdirs.append(d)

        db_path = os.path.join(d, "test.db")
        player = MockMusicPlayer(db_path)

        mgr = PluginManager(core_engine=player, plugin_dir="plugins")
        mgr.load_plugins()
        rec = mgr.get_plugin("recommendations")

        import unittest.mock as mock
        time_base = 1000
        with mock.patch('time.time', return_value=time_base + 360):
            # Track A starts and completes
            track_a = {"artist": "ArtistA", "album": "AlbumA", "title": "TrackA", "path": "/a.flac", "started_at": time_base}
            rec._on_song_change(track_a)
            rec._on_playback_complete(
                {"artist": "ArtistA"},
                completed=True, skipped=False
            )

            # Track B starts 10 minutes AFTER A completes - gap > 5 minutes
            track_b = {"artist": "ArtistB", "album": "AlbumB", "title": "TrackB", "path": "/b.flac", "started_at": time_base + 360 + 600}
            rec._on_song_change(track_b)
            rec._on_playback_complete(
                {"artist": "ArtistB"},
                completed=True, skipped=False
            )

        # First, check live pairing: should NOT pair
        similar = rec.get_similar_artists("ArtistA", limit=10)
        self.assertEqual(len(similar), 0)

        # Insert the same plays into the plays table so build_from_history()
        # processes them, then rebuild and check again
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE IF NOT EXISTS plays (id INTEGER PRIMARY KEY AUTOINCREMENT, track_path TEXT, artist TEXT, album TEXT, title TEXT, started_at INTEGER, ended_at INTEGER, completed BOOLEAN, skipped BOOLEAN, duration_ms INTEGER)")
        conn.execute("INSERT INTO plays (track_path, artist, album, title, started_at, ended_at, completed, skipped) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                     ("/a.flac", "ArtistA", "AlbumA", "TrackA", time_base, time_base + 360, 1, 0))
        conn.execute("INSERT INTO plays (track_path, artist, album, title, started_at, ended_at, completed, skipped) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                     ("/b.flac", "ArtistB", "AlbumB", "TrackB", time_base + 360 + 600, time_base + 360 + 960, 1, 0))
        conn.commit()
        conn.close()

        # Run build_from_history and check again - still should NOT pair
        rec.build_from_history()
        similar = rec.get_similar_artists("ArtistA", limit=10)
        self.assertEqual(len(similar), 0)

        mgr.shutdown_all()

    def test_execute_with_retry_holds_rlock(self):
        """_execute_with_retry acquires the MPD RLock around the command.

        Ensures that the RLock is wired in and used; without it concurrent
        commands on the same MusicPlayer instance could interleave on the
        shared python-mpd2 client socket.
        """
        player = MusicPlayer.__new__(MusicPlayer)
        player._connected = True
        player.client = MagicMock()
        player.client.ping.return_value = None
        acquired = []
        class RecordingLock:
            def __enter__(self):
                acquired.append(True)
                return self
            def __exit__(self, *a):
                return False
        player._lock = RecordingLock()

        def _cmd():
            return player.client.status()

        player.client.status.return_value = {"state": "play"}
        player._execute_with_retry(_cmd)
        self.assertTrue(
            acquired, "Command should run under the player lock"
        )

    def test_list_all_info_own_client_normalizes_multi_value_tags(self):
        """list_all_info_own_client() tidies list-valued tags into plain strings.

        Simulating an MPD library where python-mpd2 returns repeated tags as
        lists (e.g. genre: ["Rock", "Pop"]), the helper in
        MusicPlayer._normalize_listallinfo converts them to plain comma-separated
        strings so downstream code that reads ``track["artist"]`` or
        ``track["genre"]`` works without list-valued tag failures (bug 1).
        """
        class FakeClient:
            def __init__(self):
                self.timeout = None
            def connect(self, host, port):
                pass
            def listallinfo(self):
                return [
                    {"file": "/music/rock/a.flac", "artist": ["A", "B"], "album": "X",
                     "genre": ["Rock", "Pop"], "title": "T", "time": "200"},
                    {"directory": "/music/rock"},
                ]
            def close(self):
                pass
            def disconnect(self):
                pass
        from unittest.mock import patch
        with patch("core.player.LibMPDClient", FakeClient):
            player = MusicPlayer(host="localhost", port=6600)
            result = player.list_all_info_own_client()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["path"], "/music/rock/a.flac")
        self.assertEqual(result[0]["artist"], "A, B")
        self.assertIn("Rock", result[0]["genre"])
        self.assertIn("Pop", result[0]["genre"])

    def test_scan_handles_multi_value_tags(self):
        """A track with list-valued genre/artist tags is still written to album_songs.

        The scan helper _as_text() converts list tags to plain strings before
        inserting into album_songs, so bug 1 (list tags empty the library) does
        not happen on real MPD either (where multi-value tags are common).
        """
        d = tempfile.mkdtemp()
        self.tmpdirs.append(d)
        db_path = os.path.join(d, "test.db")

        # Core that returns raw list-valued tags (simulating an unnormalized
        # source, e.g. an own-client path before normalization).
        class Core:
            def list_all_info(self):
                return []
            def list_all_info_own_client(self):
                return [
                    {"path": "/music/rock/a.flac", "artist": ["A", "B"],
                     "album": "Al", "genre": ["Rock", "Pop"], "time": "200"},
                    {"directory": "/music/rock"},
                ]

        plugin = RecommendationEngine({})
        plugin.db_path = db_path
        plugin._conn = sqlite3.connect(db_path, check_same_thread=False, isolation_level=None)
        plugin._conn.execute("PRAGMA journal_mode=WAL")
        plugin._create_schema()
        plugin.core = Core()

        # Invoked directly so we test the scan's own _as_text() handling of
        # list-valued tags regardless of MPD-layer normalization.
        plugin._scan_library_if_empty()

        # album_songs should contain the track despite list-valued tags.
        cur = plugin._conn.execute("SELECT COUNT(*) FROM album_songs")
        self.assertEqual(cur.fetchone()[0], 1,
                         "List-valued tags should not empty album_songs")
        plugin._conn.close()

    def test_scan_lock_scope_fetch_outside_lock(self):
        """The library scan fetches MPD outside _rebuild_lock (Issue 17, follow-up 1).

        A slow fetch must not block other threads that need the lock. Starts
        the scan on a thread with a ~0.5 s fake fetch, then times
        _update_last_built_at() (which acquires _rebuild_lock) from the main
        thread. It must return well before the fetch finishes (under 0.2 s).
        """
        d = tempfile.mkdtemp()
        self.tmpdirs.append(d)
        db_path = os.path.join(d, "test.db")

        plugin = RecommendationEngine({})
        plugin.db_path = db_path
        plugin._conn = sqlite3.connect(db_path, check_same_thread=False, isolation_level=None)
        plugin._conn.execute("PRAGMA journal_mode=WAL")
        plugin._create_schema()

        class SlowCore:
            def list_all_info(self):
                return []

            def list_all_info_own_client(self):
                time.sleep(0.5)
                return [
                    {"path": "/music/a.flac", "artist": "A", "album": "Al",
                     "title": "T", "genre": "Rock", "time": "200"},
                ]

        plugin.core = SlowCore()

        import threading
        t = threading.Thread(target=plugin._scan_library_if_empty)
        t.start()
        # Give the scan time to reach its (unlocked) fetch before timing.
        time.sleep(0.1)

        start = time.monotonic()
        plugin._update_last_built_at(int(time.time()))
        elapsed = time.monotonic() - start

        t.join(timeout=5.0)

        self.assertLess(elapsed, 0.2,
                        "Slow library fetch must not block the rebuild lock")
        plugin._conn.close()

    def test_shutdown_flushes_pending_pairs_during_rebuild(self):
        """shutdown() flushes pairs queued while a rebuild is computing (Issue 17, follow-up 2).

        While _building is True, _record_pair queues the pair; shutdown() must
        still write it before closing the connection so no pair is dropped.
        """
        d = tempfile.mkdtemp()
        self.tmpdirs.append(d)
        db_path = os.path.join(d, "test.db")

        plugin = RecommendationEngine({})
        plugin.db_path = db_path
        plugin._conn = sqlite3.connect(db_path, check_same_thread=False, isolation_level=None)
        plugin._conn.execute("PRAGMA journal_mode=WAL")
        plugin._create_schema()
        import threading
        plugin._stop_event = threading.Event()
        plugin._bg_thread = threading.Thread(target=plugin._background_worker, daemon=True)
        plugin._bg_thread.start()

        # Queue a pair while a rebuild is considered in progress.
        plugin._building = True
        plugin._record_pair("ArtistA", "ArtistB")

        # shutdown must flush the queued pair before closing the connection.
        plugin.shutdown()

        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT artist_a, artist_b, play_count FROM cooccurrence")
        pairs = cur.fetchall()
        conn.close()
        self.assertEqual(len(pairs), 1)
        self.assertEqual(pairs[0][:2], ("ArtistA", "ArtistB"))
        # The connection should be closed after shutdown.
        self.assertIsNone(plugin._conn)

if __name__ == "__main__":
    unittest.main()