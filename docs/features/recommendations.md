# Music Recommendations Guide

Local-only music recommendations based on your listening history.

> **Feature:** Phase 3 (Slice 3.1 — Recommendation Engine Core)
> **Algorithm:** Co-occurrence counting + genre expansion
> **Privacy:** All processing local — no network calls, no telemetry

---

## How It Works

The recommendation engine builds a local co-occurrence model from your play history:

### Session Definition

A "listening session" is a series of consecutive tracks played within `session_gap_seconds` (default 300s / 5 minutes) of each other:

```
Session: Track A → Track B (1:30 gap) → Track C (0:45 gap) → ... (3:20 gap to next session)
```

### Artist Affinity

For each session, record artists that appear together:

```
Artist A ↔ Artist B appeared in same session 23 times
Artist A ↔ Artist C appeared in same session 17 times
```

### Recommendation Generation

```python
def get_similar_artists(artist, limit=10):
    # Query co-occurrence matrix
    similar = query_cooccurrence(artist)
    return sorted(similar, key=lambda x: x['score'], reverse=True)[:limit]
```

### Session Rules

- A session is a run of completed plays where the gap between one track's `ended_at` and the next track's `started_at` is `< session_gap_seconds`.
- Any play that is not completed (skip or stop) ends the session — no pair across that boundary.
- Pairs are recorded once, in canonical order (`artist_a < artist_b`).
- Same-artist pairs and blank artists are never recorded.
- Pairing happens on track **completion** (not song change), so a track is never paired with itself.

---

## Dashboard Features

Recommendations surface through the dashboard plugin hooks:

### Play Similar
Queues tracks from artists you've listened to together. Based on artist co-occurrence from listening sessions.

### Genre Radio
Shuffles all tracks in a selected genre from the library scan (`album_songs` table).

### Revisit
Shows albums not played in `days` (default 30) — one track path per album.

### New to You
Shows artists in your library (`album_songs` from MPD `listallinfo`) that you've never played (absent from `plays`).

Access requires the Touch Toolkit (Slice 3.1a) for `ScrollList` lists, and Slice 3.2 for the Discover screen navigation.

---

## Configuration

### App-level config (`config.json`)

The recommendation engine reads the app-level database path from `stats.db_path`. The `MusicPlayer` instance has `player.config` attached by `main.py` so the plugin can resolve `stats.db_path` at initialize time.

```json
{
  "stats": {
    "db_path": "~/.local/share/pi-music-player/play_stats.db",
    "enabled": true,
    "max_size_mb": 10,
    "retention_days": 365
  }
}
```

| Setting | Description |
|---------|-------------|
| `stats.db_path` | Path to the SQLite play statistics database (shared by PlayStats and the recommendation engine) |
| `stats.enabled` | Whether statistics collection is enabled |

### Plugin manifest (`plugins/recommendations/config.json`)

The manifest separates **schema** (`settings_schema`, what values are valid) from **values** (`settings`, the actual current values). The engine reads `settings.recommendations.*` at initialize time.

```json
{
  "plugin_id": "recommendations",
  "name": "Recommendations",
  "type": "feature",
  "capabilities": ["recommendations"],
  "settings_schema": {
    "recommendations": {
      "type": "object",
      "properties": {
        "session_gap_seconds": {"type": "integer", "minimum": 60, "maximum": 3600, "default": 300},
        "scan_library_on_startup": {"type": "boolean", "default": true}
      },
      "required": ["session_gap_seconds", "scan_library_on_startup"]
    }
  },
  "settings": {
    "recommendations": {
      "session_gap_seconds": 300,
      "scan_library_on_startup": true
    }
  },
  "auto_load": true
}
```

| Setting | Description |
|---------|-------------|
| `recommendations.session_gap_seconds` | Max gap (seconds) between tracks in the same listening session (default 300) |
| `recommendations.scan_library_on_startup` | Whether to scan the MPD library at startup to populate `album_songs` (default true) |

Note: the manifest does **not** contain `stats.db_path` — that comes from the app-level config via `main.py` attaching `player.config = config`.

---

## Database Schema

Recommendations are stored in SQLite alongside play statistics:

```sql
CREATE TABLE IF NOT EXISTS cooccurrence (
    artist_a TEXT NOT NULL,
    artist_b TEXT NOT NULL,
    play_count INTEGER DEFAULT 1,
    PRIMARY KEY (artist_a, artist_b)
);  -- artist_a < artist_b (canonical order); same-artist pairs never stored

CREATE TABLE IF NOT EXISTS album_songs (
    path TEXT PRIMARY KEY,
    album TEXT,
    artist TEXT,
    genre TEXT
);  -- populated by MPD listallinfo library scan

CREATE TABLE IF NOT EXISTS cooccurrence_meta (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    last_built_at INTEGER NOT NULL  -- INTEGER Unix seconds (same type as plays.ended_at)
);
```

`cooccurrence_meta.last_built_at` records when the matrix was last rebuilt so the startup staleness check can compare it with `MAX(plays.ended_at)`. The comparison is number-to-number (both INTEGER Unix seconds), so a TEXT timestamp would never appear newer.

---

## Building the Model

### Initial Build (Startup)

On first run, `initialize()` compares `cooccurrence_meta.last_built_at` with `MAX(plays.ended_at)` in the background thread. If the matrix is missing or older than the latest play, it runs `build_from_history()` — which writes into a temp `cooccurrence_new` table and atomically swaps into place — so lookups never see a half-built matrix.

### Ongoing Updates

During playback, `_on_playback_complete` records co-occurrence pairs for completed tracks within `session_gap_seconds`. If a rebuild is computing the matrix at the same time, pairs are queued (`_pending_pairs`) and flushed after the atomic swap so they are never lost.

---

## API Reference

### RecommendationEngine class

Located in `plugins/recommendations/recommendations.py`. The class is named `MusicPlayerPlugin` (so the plugin loader discovers it) but is imported in tests as `RecommendationEngine`.

| Method | Description |
|--------|-------------|
| `get_similar_artists(artist, limit=10)` | Returns co-occurring artists ranked by `play_count` DESC. Bidirectional: queries both `artist_a` and `artist_b`. Same-artist pairs excluded. |
| `get_recommendations_for_current(limit=10)` | Recommendations based on the currently playing track's artist (via `_current_artist`). |
| `get_genre_radio(genre)` | Shuffled track paths from `album_songs` matching genre. Delimited whole-tag match (case-insensitive). Returns `[]` when table is empty. |
| `get_revisit_candidates(days=30)` | One track path per album not played in the last `days`. Excludes recently played albums. |
| `get_new_to_you()` | Library artists (`album_songs`) absent from `plays`. Requires library scan first. |
| `initialize(core)` | Resolves `stats.db_path` from app config, opens connection, registers hooks, starts background thread for library scan + rebuild. |
| `shutdown()` | Signals background thread to stop, waits for it, flushes queued pairs, closes connection. |

### Hooks

The engine registers for two events raised by `ui/dashboard.py`:

| Hook | Payload | When fired |
|------|---------|------------|
| `on_song_change` | `{artist, album, title, path, started_at}` | When `_update_ui` opens a play row (stop→replay and genuine song changes) |
| `on_playback_complete` | `{artist, album, title, path, started_at}`, `completed`, `skipped` | When a track ends/stops/skips |

`main.py` sets `player.config = config` before loading plugins, and passes `plugin_mgr` to `run_dashboard()`.

---

## Privacy

| Data Type | Stored | Shared | Telemetry |
|-----------|--------|--------|-----------|
| Co-occurrence counts | Local SQLite | Never | None |
| Artist preferences | Local SQLite | Never | None |
| Genre tags | Local SQLite | Never | None |
| Play history | Local SQLite | Never | None |
| IP address | Never | Never | None |
| Device ID | Never | Never | None |

**No external API calls** — MusicBrainz queries (for MBID resolution) happen only during album art fallback, not recommendations.

---

## Manual Testing

```bash
# After building co-occurrence model
python3 -c "
import sys; sys.path.insert(0, '.')
from plugins import PluginManager
from core.config import Config
d = tempfile.mkdtemp()  # copy plugins/recommendations into d
shutil.copytree('plugins/recommendations', os.path.join(d, 'recommendations'))
mgr = PluginManager(plugin_dir=d)
mgr.load_plugins()
rec = mgr.get_plugin('recommendations')
print('Similar to Radiohead:', rec.get_similar_artists('Radiohead'))
print('Genre Radio Blues:', rec.get_genre_radio('Blues')[:5])
mgr.shutdown_all()
"
```

---

## Performance

| Operation | Target Time |
|-----------|-------------|
| Get similar artists | < 200 ms on Pi Zero 2 W |
| Get genre radio | < 200 ms on Pi Zero 2 W |
| Get similar artists (desktop) | < 500 ms |

Memory stays within the Phase 3 budget (40 MB). The background library scan and rebuild run on a daemon thread so the dashboard opens immediately; queries degrade gracefully (empty lists) until data is ready.

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| No recommendations | Build model: check play history exists; run `build_from_history()` after startup staleness check |
| All artists "similar" | Low play count; need more listening sessions |
| Genre radio empty | Library scan hasn't run yet or `album_songs` is empty; check `scan_library_on_startup` |
| New to You empty | All library artists have been played at least once |
| Plugin fails to load on fresh install | Plugin creates the DB parent directory on initialize (Issue 15 fix #1) |
