# Music Recommendations Guide

Local-only music recommendations based on your listening history.

> **Feature:** Phase 3
> **Algorithm:** Co-occurrence counting + genre expansion
> **Privacy:** All processing local — no network calls, no telemetry

---

## How It Works

The recommendation engine builds a local co-occurrence model from your play history:

### Session Definition

A "listening session" is a series of consecutive tracks played within 5 minutes of each other:

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

### Genre Expansion

Tracks are also linked by genre tags (from mutagen file metadata or MusicBrainz tags):

```
Genre: "Progressive Rock" → [Pink Floyd, King Crimson, Tool, Radiohead, ...]
```

Recommendations can expand beyond co-occurrence to include genre-similar artists.

---

## Features in the Dashboard

Access from the UI by swiping left twice (Now Playing → Stats → Discover):

### Play Similar

Button on the "Now Playing" screen:

- **Action:** Queues 10 tracks from artists you've listened to together
- **When to use:** When you want to discover more music like what you're hearing
- **Basis:** Artist co-occurrence from listening sessions

### Genre Radio

From Discover screen:

- **Action:** Shuffles all tracks in a selected genre
- **When to use:** "I want to hear all my blues music in random order"
- **Genres available:** All genres present in your library

### Revisit

- **Action:** Shows albums not played in 30+ days
- **When to use:** "What did I forget about?"
- **Smart:** Excludes recently played, shows hidden gems from your collection

### New to You

- **Action:** Shows artists in your library that you've never played
- **When to use:** "What else does my collection have?"
- **Requires:** MPD database up-to-date (`mpc update` after adding new music)

---

## Configuration

Enable/disable recommendation features in `config.json`:

```json
{
  "recommendations": {
    "enabled": true,
    "use_genre_expansion": true,
    "session_gap_seconds": 300,
    "min_session_plays": 3,
    "max_suggestions": 20
  }
}
```

| Setting | Description |
|---------|-------------|
| `enabled` | Turn on/off recommendation engine |
| `use_genre_expansion` | Include genre-similar tracks in suggestions |
| `session_gap_seconds` | Gap threshold for session boundaries (default: 300) |
| `min_session_plays` | Minimum plays to count toward co-occurrence |
| `max_suggestions` | Maximum results per recommendation query |

---

## Database Schema

Recommendations are stored in SQLite alongside play statistics:

```sql
CREATE TABLE cooccurrence (
    artist_a TEXT,
    artist_b TEXT,
    play_count INTEGER DEFAULT 1,
    PRIMARY KEY (artist_a, artist_b)
);

CREATE TABLE genres (
    genre TEXT PRIMARY KEY,
    artists TEXT  -- comma-separated list
);

CREATE TABLE album_songs (
    album TEXT,
    artist TEXT,
    path TEXT,
    genre TEXT,
    PRIMARY KEY (path)
);
```

### Schema Update

The co-occurrence matrix is updated:

1. **Per-track:** On each play completion, record with previous/next track in session
2. **Nightly:** At ~3 AM local time, run vacuum and optimize indices

---

## Building the Model

### Initial Build

On first run after Phase 3 is enabled:

```python
# Build co-occurrence from existing history
builder = RecommendationBuilder(stats_db_path)
builder.build_from_history()
```

Time estimate: ~1 minute per 1,000 tracked plays on Pi Zero 2 W.

### Ongoing Updates

During playback:

```python
# After track completion
if stats.is_completed():
    cooc = CooccurrenceModel()
    cooc.record_session_pair(prev_track, curr_track)
```

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

## Example Output

```python
# What to expect after some listening
>>> get_similar_artists('Radiohead')
[{'artist': 'Pink Floyd', 'score': 89},
 {'artist': 'Tool', 'score': 76},
 {'artist': 'King Crimson', 'score': 64},
 {'artist': 'Muse', 'score': 51},
 {'artist': 'Muse', 'score': 51}]

>>> get_genre_radio('Progressive Rock')
# Returns shuffled queue of all blues tracks in library
```

---

## API Reference

### RecommendationEngine Class

Located in `plugins/recommendations.py`:

```python
from plugins.recommendations import RecommendationEngine

engine = RecommendationEngine(
    stats_db_path='play_stats.db',
    music_db_path='/var/lib/mpd/mpd.db'
)

# Get similar artists
similar = engine.get_similar_artists('Radiohead', limit=10)

# Get recommendations for current track
recommendations = engine.get_recommendations_for_current({
    'artist': 'Radiohead',
    'album': 'OK Computer',
    'title': 'Paranoid Android'
})

# Get genre-based radio queue
queue = engine.get_genre_radio('Progressive Rock')

# Get "Revisit" candidates
revisit_albums = engine.get_revisit_candidates(days=30)

# Get "New to You" artists
new_artists = engine.get_new_to_you()
```

### MPD Integration

Recommendations queue tracks via MPD:

```python
# Play similar tracks
for track in similar_tracks:
    mpd_client.add(track['path'])

# Or play immediate queue
mpd_client.playid(0)  # Start from beginning
```

---

## Manual Testing

```bash
# After building co-occurrence model
python3 -c "
from plugins.recommendations import RecommendationEngine
engine = RecommendationEngine('play_stats.db')
print('Similar to Radiohead:', engine.get_similar_artists('Radiohead'))
print('Genre Radio:', engine.get_genre_radio('Blues')[:5])
"
```

---

## Performance

| Operation | Target Time | Pi Zero 2 W |
|-----------|-------------|-------------|
| Build model from 1,000 plays | < 60 seconds | ~45 seconds |
| Get similar artists | < 100 ms | ~60 ms |
| Get genre radio | < 200 ms | ~150 ms |
| Memory usage | N/A | ~5 MB |

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| No recommendations | Build model: check play history exists, run `build_from_history()` |
| All artists "similar" | Low play count; need more listening sessions |
| Genre radio empty | MPD database outdated; run `mpc update` |
| Slow queries | Check SQLite indices, consider vacuum |