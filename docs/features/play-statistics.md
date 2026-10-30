# Play Statistics Guide

Complete guide to the play statistics feature — local SQLite tracking of every play event, with insights dashboard.

> **Feature:** Phase 2
> **Storage:** SQLite database (`play_stats.db`)
> **Privacy:** All data stored locally — no telemetry, no cloud uploads

---

## Overview

The play statistics feature tracks every play event on your music player:

| Tracked Metric | Description |
|----------------|-------------|
| **Play count** | Total number of times each track/artist/album was played |
| **Playtime** | Cumulative minutes spent listening |
| **Skip rate** | Percentage of plays where track was skipped before completion |
| **Completion rate** | Percentage of plays where track was played to completion |
| **Last played** | Timestamp of most recent play |
| **First played** | Timestamp of first play |
| **Play frequency** | How often a track/artist/album is played over time |

## Database Schema

The statistics database (`play_stats.db`) uses SQLite:

```sql
CREATE TABLE plays (
    id INTEGER PRIMARY KEY,
    track_path TEXT NOT NULL,
    artist TEXT,
    album TEXT,
    title TEXT,
    started_at INTEGER NOT NULL,      -- unix timestamp
    ended_at INTEGER,                 -- null if currently playing
    completed BOOLEAN DEFAULT 0,      -- 1 = played to end
    skipped BOOLEAN DEFAULT 0,        -- 1 = user pressed next
    duration_ms INTEGER               -- track length
);

CREATE INDEX idx_artist ON plays(artist);
CREATE INDEX idx_album ON plays(album);
CREATE INDEX idx_started ON plays(started_at);
```

Database size: **~1KB per 100 plays** — negligible storage impact.

## Enabling Statistics

Statistics are enabled by default. To disable:

```json
// config.json
{
  "stats_enabled": false
}
```

To clear all statistics:

```json
// config.json
{
  "stats_reset": true    // Set once, app will reset on startup
}
```

## Insights Dashboard

Access from the main UI by swiping left from Now Playing:

### Top Artists
Ranked by total play count and cumulative playtime.

### Top Albums
Ranked by total play count.

### Most Played Tracks
Ranked by play count.

### Skip Rate
Shows which artists/albums you most frequently skip.

### Listening Time
Heatmap by hour of day / day of week — when you listen most.

### Recent History
Last 20 plays with timestamps and duration.

### Export CSV

Download all statistics as a CSV file for personal analysis:

```csv
track_path,artist,album,title,started_at,ended_at,completed,skipped,duration_ms
/mnt/nas/music/artist/album/track.flac,"Artist","Album","Title",1739203200,1739203380,1,0,180000
```

Open in any spreadsheet application (Excel, LibreOffice Calc, Google Sheets).

## Storage Management

### Database Location

- **Default:** `~/.local/share/pi-music-player/play_stats.db`
- **Custom:** Set `stats_db_path` in `config.json`

### Max Size

The database is automatically capped:

```json
{
  "stats_max_size_mb": 10,
  "stats_vacuum_interval_days": 30
}
```

### Automatic Cleanup

When stats exceed max size, oldest records are pruned:

```json
{
  "stats_retention_days": 365   // Keep 1 year of play history
}
```

## Privacy

| Data Type | Stored | Shared | Telemetry |
|-----------|--------|--------|-----------|
| Play counts | Local SQLite | Never | None |
| Track titles/artists | Local SQLite | Never | None |
| Timestamps | Local SQLite | Never | None |
| IP address | Never | Never | None |
| Device ID | Never | Never | None |
| Location | Never | Never | None |

**No external calls are made for statistics.** All processing happens locally on your device.

---

## Code Reference

### PlayStats Class

Located in `core/stats.py`:

```python
from core.stats import PlayStats

stats = PlayStats(db_path='play_stats.db')

# Record a play start
stats.record_play_start({
    'file': '/music/artist/album/track.flac',
    'artist': 'Test Artist',
    'album': 'Test Album',
    'title': 'Test Track',
    'duration': 180000  # ms
})

# Record a play end
stats.record_play_end(completed=True, skipped=False)

# Query statistics
stats.get_top_artists(limit=10)
stats.get_top_albums(limit=10)
stats.get_most_played_tracks(limit=10)
stats.get_skip_rate(artist='Test Artist')
stats.get_recent_plays(limit=20)
stats.get_total_plays()
stats.get_listening_time_by_hour()
```

### Integration with Player

Statistics are automatically recorded when:

1. **Track starts playing** → `record_play_start()` called
2. **Track ends normally** → `record_play_end(completed=True)`
3. **User skips track** → `record_play_end(completed=False, skipped=True)`
4. **User stops playback** → `record_play_end(completed=False)`

---

## Example Insights

After a week of listening, you might see:

```
TOP ARTISTS:
1. Pink Floyd - 147 plays, 1,845 min
2. The Beatles - 123 plays, 1,450 min
3. Miles Davis - 89 plays, 1,120 min

SKIP RATE BY ARTIST:
1. Pink Floyd - 8% skip rate (you almost never skip)
2. The Beatles - 12% skip rate
3. Miles Davis - 24% skip rate

LISTENING PEAKS:
- Weekdays: 7 PM - 10 PM (heaviest listening)
- Weekends: 11 AM - 2 PM
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Database locked | Close other app instances; only one should access at a time |
| Stats not recording | Check `stats_enabled` in config.json |
| Database too large | Increase `stats_max_size_mb` or reduce `stats_retention_days` |
| Wrong track attributed | Ensure MPD `currentsong()` returns correct metadata |
