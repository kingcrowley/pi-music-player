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
from unittest.mock import MagicMock

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
        """Live on_song_change / on_playback_complete never pairs a track with itself."""
        d = _make_temp_plugin_dir()
        self.tmpdirs.append(d)

        db_path = os.path.join(d, "test.db")
        player = MockMusicPlayer(db_path)

        mgr = PluginManager(core_engine=player, plugin_dir="plugins")
        mgr.load_plugins()
        rec = mgr.get_plugin("recommendations")

        # Simulate on_song_change with Track A
        track_a = {"artist": "Radiohead", "album": "OK Computer", "title": "Paranoid Android", "path": "/a.flac", "started_at": 1000}
        rec._on_song_change(track_a)

        # Simulate on_playback_complete for Track A (completed)
        track_a_done = {"artist": "Radiohead", "album": "OK Computer", "title": "Paranoid Android", "path": "/a.flac"}
        rec._on_playback_complete(track_a_done, completed=True, skipped=False)

        # Now on_song_change with Track B
        track_b = {"artist": "Pink Floyd", "album": "Dark Side", "title": "Time", "path": "/b.flac", "started_at": 1500}
        rec._on_song_change(track_b)

        # Pair should be (Radiohead, Pink Floyd)
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
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module)
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


if __name__ == "__main__":
    unittest.main()