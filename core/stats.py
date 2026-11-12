"""Play Statistics — Slice 2.1

Persistent local SQLite database tracking every play event.

Designed for low-RAM Linux systems (Pi Zero 2 W).

Features:
- SQLite backend with WAL journal mode (power-loss resilient)
- Synchronous=NORMAL for durability without heavy fsync cost
- Play event tracking: start/end/completed/skipped/stopped
- Aggregates: total plays, recent plays, artist stats, listening time
- Config-driven enable/disable and storage location
- Automatic cleanup of open plays on start

Module Structure:
- PlayStats class: Main interface for play statistics
"""

import logging
import sqlite3
import time
import os
from pathlib import Path
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


class PlayStats:
    """SQLite-backed play statistics manager.

    Tracks play events with start/end/completed/skipped states.

    Attributes:
        db_path: Path to SQLite database file
        enabled: Whether statistics collection is enabled
        _conn: SQLite connection
    """

    DEFAULT_DB_PATH = "~/.local/share/pi-music-player/play_stats.db"

    def __init__(self, db_path: Optional[str] = None, enabled: bool = True):
        """Initialize PlayStats with SQLite database.

        When disabled, no database file is created and all methods
        silently no-op.

        Args:
            db_path: Path to SQLite database file. Defaults to
                     ~/.local/share/pi-music-player/play_stats.db
            enabled: Whether statistics collection is enabled (default: True)
        """
        self.enabled = enabled

        if not self.enabled:
            self.db_path = os.path.expanduser(db_path or self.DEFAULT_DB_PATH)
            self._conn = None
            return

        if db_path is None:
            db_path = self.DEFAULT_DB_PATH
        # Expand ~ to home directory
        self.db_path = os.path.expanduser(str(db_path))

        # Ensure parent directory exists
        db_dir = Path(self.db_path).parent
        try:
            db_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

        self._retention_seconds = 365 * 24 * 3600  # default 1 year
        self._max_size_mb = 10  # default 10 MB

        self._conn = sqlite3.connect(
            self.db_path,
            check_same_thread=False,
            isolation_level=None,  # Autocommit mode
        )
        # WAL mode for power-loss resilience
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")

        # Create schema
        self._create_schema()

    # --- Schema ---

    def _create_schema(self) -> None:
        """Create the plays table and indexes if they don't exist."""
        self._conn.execute("""
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
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_artist ON plays(artist)"
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_album ON plays(album)"
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_started ON plays(started_at)"
        )
        self._conn.commit()

    # --- Event Recording ---

    @staticmethod
    def _parse_duration(duration: Any) -> int:
        """Parse an MPD duration value into integer seconds.

        MPD reports duration as text, e.g. "245.123" or "245".
        Returns seconds as an integer, or 0 if unparseable.

        Args:
            duration: MPD duration value (string, int, float, or None)

        Returns:
            int: Duration in whole seconds, or 0 if unparseable
        """
        if duration is None:
            return 0
        try:
            return int(float(str(duration)))
        except (ValueError, TypeError):
            logger.warning("Could not parse duration: %r", duration)
            return 0

    def record_play_start(self, track_info: Dict[str, Any]) -> bool:
        """Record a play event start.

        Before inserting, closes any open play events (started without end)
        so they don't stay unfinished forever.

        Args:
            track_info: Dict with keys: file, artist, album, title, duration

        Returns:
            bool: True if recorded, False if disabled or failed
        """
        if not self.enabled:
            return False

        try:
            # Close any open play from a previous start without end
            self._close_open_plays()

            started_at = int(time.time())
            duration_ms = self._parse_duration(track_info.get("duration")) * 1000
            self._conn.execute(
                """
                INSERT INTO plays
                (track_path, artist, album, title, started_at, ended_at, completed, skipped, duration_ms)
                VALUES (?, ?, ?, ?, ?, NULL, 0, 0, ?)
                """,
                (
                    str(track_info.get("file", "")),
                    track_info.get("artist") or "",
                    track_info.get("album") or "",
                    track_info.get("title") or "",
                    started_at,
                    duration_ms,
                ),
            )
            return True
        except Exception as e:
            logger.warning("record_play_start failed: %s", e)
            return False

    def record_play_end(self, completed: bool = False, skipped: bool = False) -> bool:
        """Record play end (completed, skipped, or stopped).

        Exactly one of completed/skipped should be True. If neither is True,
        the play is marked as stopped (ended but neither completed nor skipped).

        Args:
            completed: True if played to end
            skipped: True if skipped

        Returns:
            bool: True if a play was ended, False if disabled, no open play,
                  or failed
        """
        if not self.enabled:
            return False

        try:
            ended_at = int(time.time())
            # Find the most recent open play
            cursor = self._conn.execute(
                """
                SELECT id FROM plays
                WHERE ended_at IS NULL
                ORDER BY id DESC
                LIMIT 1
                """
            )
            row = cursor.fetchone()
            if row is None:
                # No open play to end
                return False

            play_id = row[0]
            self._conn.execute(
                """
                UPDATE plays
                SET ended_at = ?, completed = ?, skipped = ?
                WHERE id = ?
                """,
                (ended_at, 1 if completed else 0, 1 if skipped else 0, play_id),
            )
            return True
        except Exception as e:
            logger.warning("record_play_end failed: %s", e)
            return False

    def _close_open_plays(self) -> None:
        """Close any open play events without an end timestamp.

        Called at the start of record_play_start so that two consecutive
        starts without an intervening end don't leave an unfinished row.
        """
        try:
            self._conn.execute(
                """
                UPDATE plays
                SET ended_at = started_at, completed = 0, skipped = 0
                WHERE ended_at IS NULL
                """
            )
        except Exception as e:
            logger.warning("_close_open_plays failed: %s", e)

    # --- Queries ---

    def get_recent_plays(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recently completed play events.

        Args:
            limit: Maximum number of rows to return (default: 20)

        Returns:
            List of play event dicts
        """
        if not self.enabled:
            return []
        try:
            cursor = self._conn.execute(
                """
                SELECT id, track_path, artist, album, title, started_at, ended_at, completed, skipped, duration_ms
                FROM plays
                WHERE completed = 1
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            )
            rows = cursor.fetchall()
            return [
                {
                    "id": row[0],
                    "file": row[1],
                    "artist": row[2],
                    "album": row[3],
                    "title": row[4],
                    "started_at": row[5],
                    "ended_at": row[6],
                    "completed": bool(row[7]),
                    "skipped": bool(row[8]),
                    "duration_ms": row[9],
                }
                for row in rows
            ]
        except Exception as e:
            logger.warning("get_recent_plays failed: %s", e)
            return []

    def get_total_plays(self) -> int:
        """Get total number of completed play events.

        Returns:
            int: Count of completed plays
        """
        if not self.enabled:
            return 0
        try:
            cursor = self._conn.execute(
                "SELECT COUNT(*) FROM plays WHERE completed = 1"
            )
            return cursor.fetchone()[0]
        except Exception as e:
            logger.warning("get_total_plays failed: %s", e)
            return 0

    def get_artist_stats(self, artist: str) -> Dict[str, Any]:
        """Get play statistics for a specific artist.

        Uses exact match only (no LIKE wildcard matching).

        Args:
            artist: Artist name to filter by

        Returns:
            Dict with plays, playtime_ms (sum of duration for completed plays)
        """
        if not self.enabled:
            return {"plays": 0, "playtime_ms": 0}
        try:
            cursor = self._conn.execute(
                """
                SELECT COUNT(*), COALESCE(SUM(duration_ms), 0)
                FROM plays
                WHERE completed = 1 AND artist = ?
                """,
                (artist,),
            )
            row = cursor.fetchone()
            plays = row[0] if row else 0
            playtime_ms = row[1] if row else 0
            return {
                "plays": plays,
                "playtime_ms": playtime_ms or 0,
            }
        except Exception as e:
            logger.warning("get_artist_stats failed: %s", e)
            return {"plays": 0, "playtime_ms": 0}

    # --- Statistics UI Queries (Slice 2.2) ---

    def get_artist_playcounts(self) -> Dict[str, int]:
        """Get total completed play counts per artist.

        Returns:
            Dict mapping artist name to completed play count.
            Empty dict if disabled or error.
        """
        if not self.enabled:
            return {}
        try:
            cursor = self._conn.execute(
                """
                SELECT artist, COUNT(*) as cnt
                FROM plays
                WHERE completed = 1 AND artist IS NOT NULL AND artist != ''
                GROUP BY artist
                ORDER BY cnt DESC
                """
            )
            return {row[0]: row[1] for row in cursor.fetchall()}
        except Exception as e:
            logger.warning("get_artist_playcounts failed: %s", e)
            return {}

    def get_album_playcounts(self) -> Dict[str, int]:
        """Get total completed play counts per album.

        Returns:
            Dict mapping "Artist - Album" to completed play count.
            Empty dict if disabled or error.
        """
        if not self.enabled:
            return {}
        try:
            cursor = self._conn.execute(
                """
                SELECT artist, album, COUNT(*) as cnt
                FROM plays
                WHERE completed = 1 AND album IS NOT NULL AND album != ''
                GROUP BY artist, album
                ORDER BY cnt DESC
                """
            )
            return {f"{row[0]} - {row[1]}": row[2] for row in cursor.fetchall()}
        except Exception as e:
            logger.warning("get_album_playcounts failed: %s", e)
            return {}

    def get_skip_rate(self, artist: Optional[str] = None) -> Dict[str, float]:
        """Get skip rate (skips / total plays) for all artists, or a specific artist.

        Args:
            artist: Optional artist name to filter by. If None, returns all.

        Returns:
            Dict mapping artist (or "Artist - Album") to skip percentage (0.0-100.0).
            Empty dict if disabled or error.
        """
        if not self.enabled:
            return {}
        try:
            if artist is not None:
                cursor = self._conn.execute(
                    """
                    SELECT album,
                           SUM(CASE WHEN skipped = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as pct
                    FROM plays
                    WHERE completed = 1 AND artist = ?
                    GROUP BY album
                    ORDER BY pct DESC
                    """,
                    (artist,),
                )
                return {f"{artist} - {row[0]}": row[1] for row in cursor.fetchall()}
            else:
                cursor = self._conn.execute(
                    """
                    SELECT artist,
                           SUM(CASE WHEN skipped = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as pct
                    FROM plays
                    WHERE completed = 1
                    GROUP BY artist
                    ORDER BY pct DESC
                    """
                )
                return {row[0]: row[1] for row in cursor.fetchall()}
        except Exception as e:
            logger.warning("get_skip_rate failed: %s", e)
            return {}

    def get_listening_time_heatmap(self) -> Dict[str, Dict[int, int]]:
        """Get listening time heatmap by hour of day and day of week.

        Returns:
            Dict mapping day-of-week (0=Mon..6=Sun) to hour->minutes mapping.
            Empty dict if disabled or error.

        Example:
            {0: {8: 120, 9: 45, ...}, 1: {9: 30, ...}, ...}
        """
        if not self.enabled:
            return {}
        try:
            cursor = self._conn.execute(
                """
                SELECT started_at, duration_ms
                FROM plays
                WHERE completed = 1 AND duration_ms IS NOT NULL
                """
            )
            rows = cursor.fetchall()
            heatmap: Dict[int, Dict[int, int]] = {d: {} for d in range(7)}
            for started_at, duration_ms in rows:
                dt = time.localtime(started_at)
                day = dt.tm_wday  # 0=Mon
                hour = dt.tm_hour
                minutes = duration_ms // 60000
                if minutes > 0:
                    heatmap[day][hour] = heatmap[day].get(hour, 0) + minutes
            return heatmap
        except Exception as e:
            logger.warning("get_listening_time_heatmap failed: %s", e)
            return {}

    def get_recent_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent play history (completed plays only).

        Args:
            limit: Maximum number of entries to return (default: 20).

        Returns:
            List of play dicts with full metadata, most recent first.
        """
        if not self.enabled:
            return []
        try:
            cursor = self._conn.execute(
                """
                SELECT id, track_path, artist, album, title,
                       started_at, ended_at, completed, skipped, duration_ms
                FROM plays
                WHERE completed = 1
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            )
            rows = cursor.fetchall()
            return [
                {
                    "id": row[0],
                    "file": row[1],
                    "artist": row[2],
                    "album": row[3],
                    "title": row[4],
                    "started_at": row[5],
                    "ended_at": row[6],
                    "completed": bool(row[7]),
                    "skipped": bool(row[8]),
                    "duration_ms": row[9],
                }
                for row in rows
            ]
        except Exception as e:
            logger.warning("get_recent_history failed: %s", e)
            return []

    def export_csv(self, csv_path: Optional[str] = None) -> Optional[str]:
        """Export all completed plays to a CSV file.

        Args:
            csv_path: Optional path for output CSV. If None, uses
                      play_stats.csv in the same directory as the database.

        Returns:
            Path to written CSV file, or None if disabled or error.
        """
        if not self.enabled:
            return None
        try:
            import csv as csv_module
            if csv_path is None:
                csv_path = str(Path(self.db_path).with_name("play_stats.csv"))

            cursor = self._conn.execute(
                """
                SELECT id, track_path, artist, album, title,
                       started_at, ended_at, completed, skipped, duration_ms
                FROM plays
                WHERE completed = 1
                ORDER BY id ASC
                """
            )
            rows = cursor.fetchall()

            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv_module.writer(f)
                writer.writerow([
                    "id", "file", "artist", "album", "title",
                    "started_at", "ended_at", "completed", "skipped", "duration_ms"
                ])
                for row in rows:
                    writer.writerow([
                        row[0], row[1], row[2], row[3], row[4],
                        row[5], row[6], int(row[7]), int(row[8]), row[9]
                    ])
            logger.info("Exported %d plays to %s", len(rows), csv_path)
            return csv_path
        except Exception as e:
            logger.warning("export_csv failed: %s", e)
            return None

    # --- Cleanup / retention ---

    def _cleanup_open_plays(self) -> None:
        """Close any open play events older than retention_seconds."""
        if not self.enabled:
            return
        try:
            # Use <= to close plays that reached the retention boundary
            # exactly, so the boundary test doesn't miss a play.
            self._conn.execute(
                """
                UPDATE plays
                SET ended_at = started_at, completed = 0, skipped = 0
                WHERE ended_at IS NULL
                  AND started_at <= ?
                """,
                (int(time.time()) - self._retention_seconds,),
            )
        except Exception as e:
            logger.warning("_cleanup_open_plays failed: %s", e)

    def _enforce_max_size(self) -> None:
        """Prune oldest plays if database exceeds max_size_mb."""
        if not self.enabled:
            return
        try:
            db_size_bytes = Path(self.db_path).stat().st_size
            max_bytes = self._max_size_mb * 1024 * 1024
            if db_size_bytes <= max_bytes:
                return

            # Count total plays and delete oldest 10% to get under limit
            cursor = self._conn.execute("SELECT COUNT(*) FROM plays")
            total = cursor.fetchone()[0]
            if total == 0:
                return
            delete_count = max(1, total // 10)
            self._conn.execute(
                """
                DELETE FROM plays
                WHERE id IN (
                    SELECT id FROM plays
                    ORDER BY id ASC
                    LIMIT ?
                )
                """,
                (delete_count,),
            )
            logger.info("Pruned %d oldest plays to enforce max_size_mb=%d", delete_count, self._max_size_mb)
        except Exception as e:
            logger.warning("_enforce_max_size failed: %s", e)

    def cleanup(self) -> None:
        """Run cleanup: close old open plays and enforce max size."""
        if not self.enabled:
            return
        self._cleanup_open_plays()
        self._enforce_max_size()

    def close(self) -> None:
        """Close the SQLite connection and perform WAL checkpoint.

        Returns immediately — no background thread to wait for.
        """
        if self._conn is None:
            return
        try:
            self._conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            self._conn.close()
        except Exception as e:
            logger.warning("close failed: %s", e)
        finally:
            self._conn = None

    # --- Config integration ---

    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> "PlayStats":
        """Create a PlayStats instance from a config dict.

        Reads stats.enabled, stats.db_path from config.

        Args:
            config: Configuration dict with stats section

        Returns:
            PlayStats instance (disabled if stats.enabled is False)
        """
        stats_cfg = config.get("stats", {}) if isinstance(config, dict) else {}
        enabled = stats_cfg.get("enabled", True)
        db_path = stats_cfg.get("db_path", cls.DEFAULT_DB_PATH)
        return cls(db_path=db_path, enabled=enabled)