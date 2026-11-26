# Phase Development Plan: Low-RAM Python Music Player

## Development Philosophy: Docs-First, Slice-Based Delivery

Each **slice** is a 1-2 week development cycle that produces:
- **Working, testable software** (not just "code complete")
- **Verifiable acceptance criteria** you can run manually
- **Documentation updated simultaneously** (docs are a deliverable, not afterthought)
- **Foundation for the next slice** (no throwaway prototypes)

> **Documentation Mandate:** Every slice must include documentation changes. Docs live in GitHub via Markdown files updated alongside code. No feature ships undocumented.

---

## GitHub Documentation Structure

```
docs/
├── README.md                         # Project overview, quickstart
├── installation/
│   ├── README.md                     # Installation overview
│   ├── raspberry-pi-setup.md         # Complete Raspberry Pi walkthrough (all models)
│   ├── cross-distro.md              # Debian, Ubuntu, Fedora, Arch, Alpine, NixOS
│   └── docker.md                     # Docker deployment (ARM64)
├── configuration/
│   ├── README.md                     # Config overview
│   ├── mpd-setup.md                  # MPD daemon configuration per backend
│   └── network-mounts.md             # SMB/NFS fstab templates
├── usage/
│   ├── dashboard-guide.md            # UI feature reference
│   ├── keyboard-shortcuts.md         # All keybindings
│   └── touch-gestures.md            # Touchscreen interaction guide
├── features/
│   ├── play-statistics.md            # Play statistics schema and usage
│   ├── recommendations.md            # Music recommendation algorithm
│   └── remote-control.md             # Web API and remote dashboard
├── development/
│   ├── README.md                     # Contributor guide
│   ├── slice-plan.md                 # This document
│   ├── plugin-api.md                 # Plugin API specification
│   ├── plugin-developer-guide.md     # Plugin development guide
│   ├── testing.md                    # How to run tests
│   └── release-process.md           # PyInstaller builds, GitHub release workflow
├── troubleshooting/
│   ├── README.md                     # Common issues index
│   ├── audio-backend.md              # ALSA/PipeWire/PulseAudio issues
│   ├── network-mounts.md             # SMB/NFS mount failures
│   └── touch-screen.md               # Touchscreen calibration and drivers
└── assets/
    ├── screenshots/                  # Full-res screenshots for README
    └── diagrams/                     # Architecture diagrams (ASCII + SVG)
```

### GitHub-Specific Documentation Workflow

- **`docs/` committed directly to repo** — rendered natively via GitHub's Markdown preview
- **`/docs` folder → GitHub Pages** enabled in repo settings (automatic HTTPS hosting)
- **Each slice updates relevant doc files** — tracked in the slice checklist
- **README.md updated at Phase 1, Phase 4 completion** for major feature milestones
- **GitHub releases tagged** with changelog for each phase
- **Plugin docs separate** in `docs/development/` for plugin developers

### Documentation Standards

| Doc Type | Target Audience | Format | Updated By |
|----------|----------------|--------|------------|
| README.md | Everyone | Markdown | Slice 1.5 / Phase 1 done |
| Installation guides | New users | Markdown + bash blocks | Slice 1.4 / B2 |
| Feature docs | Users | Markdown | Feature slice + owner |
| Troubleshooting | All users | Question/Answer (H2 headings) | As bugs are found |
| Contributor guide | Developers | Markdown | Slice B3 |
| Plugin API | Plugin developers | Markdown | Plugin core |

---

## Plugin Development Phases

The plugin system is integrated across multiple slices. Plugin development interleave with core features:

| Phase | Slice | What's Added |
|-------|-------|-------------|
| **P1** | 1.5 | Plugin system foundation — base class, PluginManager, core hooks |
| **P2** | 2.1 | First built-in plugins: ALSA audio backend, Statistics |
| **P3** | 3.1 | Plugin ecosystem: recommendations, remote control, more |
| **P4** | 4.1 | Plugin marketplace system — discovery, loading, configuration |
| **P5** | 5.x | Community plugins — sleep timer, equalizer, etc. |

### P1: Plugin System Foundation (Slice 1.5)
- MusicPlayerPlugin base class
- PluginManager discovery and loading
- Core event hooks (`on_song_change`, `on_playback_state`, etc.)
- Plugin manifest system (`config.json`)
- Plugin lifecycle (initialize, shutdown, get_capabilities)

**Deliverables:**
- `plugins/__init__.py` — PluginManager class
- `core/plugin_base.py` — MusicPlayerPlugin abstract base
- Minimal built-in plugin for testing

### P2: Built-in Plugins (Slices 2.1-2.3)
- ALSA audio backend plugin
- Statistics feature plugin
- Remote control feature plugin
- Configuration system integration

**Deliverables:**
- `plugins/audio-backends/alsa/alsa.py` — ALSA audio backend
- `core/stats.py` — Play statistics module
- Plugin settings integration

### P3: Plugin Ecosystem (Slices 3.1-3.3)
- Recommendations plugin
- Remote control web API plugin
- Equalizer plugin (basic)
- Plugin metadata browsing

**Deliverables:**
- `plugins/features/recommendations.py` — Co-occurrence model
- `plugins/remote.py` — Web API on localhost:8080
- `plugins/features/equalizer.py` — Basic equalizer

### P4: Plugin Marketplace (Slice 4.1)
- Plugin discovery system
- Plugin loading/unloading at runtime
- Plugin configuration persistence
- Plugin lifecycle management

**Deliverables:**
- Runtime plugin loader
- Plugin settings persistence in config.json
- Plugin enable/disable from UI

### P5: Community Plugins (Slices 5.x)
- Sleep timer plugin
- Equalizer plugin (advanced)
- Bluetooth control plugin
- Any community-contributed plugins

**Deliverables:**
- Sleep timer plugin
- Advanced equalizer
- Bluetooth integration
- Plugin README template

---

## Slice Template (Updated — Now Includes Docs)

Copy this for each slice:

```markdown
## Slice X.Y: [Name]

**Target Date:** YYYY-MM-DD
**Estimated Effort:** N days

### Code Deliverables
- [ ] File/module: description
- [ ] File/module: description

### Documentation Deliverables
- [ ] Docs: Feature explanation (GitHub `docs/features/[[name]].md`)
- [ ] Docs: Setup/guide (GitHub `docs/[[category]]/[[name]].md`)
- [ ] Docs: Testing/use examples (GitHub `docs/usage/[[name]].md`)
- [ ] README: Update section for completed slice (GitHub `README.md`)

### Test Plan
```bash
# Exact commands to verify
```

### Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2

### Dependencies
- Requires: Slice X.Y-1 complete
- Blocks: Slice X.Y+1

### Notes / Risks
- Risk: ...
- Mitigation: ...
```

---

## Phase 1: Core Player (Foundation) ✅ Complete

### Slice 1.1: MPD Connection & Basic Controls ✅ Merged (PR #1, `cdbbca8`)
**Goal:** Reliable MPD communication with automatic reconnection

#### Deliverables
- `core/player.py` — `MusicPlayer` class with:
  - `connect()` with exponential backoff (1s, 2s, 4s, max 30s) — retries internally without raising; gives up after ~30s and returns `False`
  - `get_current_song()` returning empty dict on failure (never raises)
  - `play()`, `pause()`, `toggle_play()`, `next()`, `previous()`, `stop()`
  - `get_status()` → dict with `state`, `volume`, `elapsed`, `duration`
  - `set_volume(0-100)`
  - `is_connected()` → bool flag set by connect

#### Technical Addendum (from review): Network & Error Handling
- **All MPD calls wrapped** in try/except — no exception should ever propagate to the Tkinter event loop
- **Reconnect logic**: on failed command, call `connect()` once and retry the command once
- **Status polling**: `get_status()` is called from background thread; safe because it never touches Tkinter
- **MPD socket lifecycle**: Ensure systemd service file declares `After=mpd.service network.target` so MPD socket is ready before UI starts
- **MPD runs as dedicated user**: Both MPD and the Python controller run as unprivileged `player` user

#### Test Criteria (Manual)
```bash
# 1. Start MPD with test music
mpd --stdout --no-daemon  # in separate terminal

# 2. Run test script
python3 -c "
from core.player import MusicPlayer
p = MusicPlayer()
print('Connected:', p.client is not None)
print('Status:', p.get_status())
print('Current song:', p.get_current_song())
p.toggle_play()
import time; time.sleep(2)
print('After play:', p.get_status()['state'])
p.next()
print('Next song:', p.get_current_song())
p.set_volume(50)
print('Volume:', p.get_status()['volume'])
"
```

**Pass if:** All commands execute without exception, state changes visible in MPD output.

**Additional pass criteria (from review):**
- [ ] If MPD socket is unavailable, `connect()` retries with backoff and `get_status()` returns a "disconnected" status gracefully
- [ ] If MPD restarts mid-session, next status poll triggers reconnect and playback resumes
- [ ] No uncaught exceptions reach the UI thread during any of the above

---

### Slice 1.2: Album Art — Local Extraction Only ✅ Merged (PR #2, `415d248`)
**Goal:** Extract embedded artwork from FLAC/MP3 files, cache to disk

#### Deliverables
- `core/artwork.py` — `ArtworkCache` class with:
  - `get_art(file_path)` → returns cached image path or `None`
  - LRU cache with configurable max size (default 50MB)
  - Thread-safe: uses `queue.Queue` + background worker
  - Extracts from: FLAC (VorbisComment pictures), MP3 (ID3v2 APIC), M4A (iTunes artwork)

#### Test Criteria
```bash
# 1. Prepare test files
mkdir -p ~/test_music
cp /path/to/some.flac ~/test_music/
cp /path/to/some.mp3 ~/test_music/

# 2. Run test
python3 -c "
from core.artwork import ArtworkCache
cache = ArtworkCache(max_size_mb=10)
for f in ['~/test_music/some.flac', '~/test_music/some.mp3']:
    path = cache.get_art(f)
    print(f'{f}: {path}')
    if path:
        import os; print(f'  Size: {os.path.getsize(path)} bytes')
"
```

**Pass if:** Returns valid image paths for files with embedded art; returns `None` for files without; cache directory stays under size limit.

---

### Slice 1.3: Album Art — Web Fallback with MBID Resolution ✅ Merged (PR #3, `4bd0970`)
**Goal:** Fetch cover art from Cover Art Archive when no embedded art exists

#### Deliverables
- Enhanced `ArtworkCache.get_art()` with fallback chain:
  1. Embedded art (Slice 1.2)
  2. Local sidecar (`cover.jpg` / `folder.jpg` in same directory)
  3. **Cover Art Archive** via MusicBrainz Release ID (MBID)
     - Extract MBID from file tags (`musicbrainz_releaseid`)
     - Query `https://coverartarchive.org/release/{MBID}`
     - Download `thumbnails.small` image
- All network calls: `timeout=3.5`, custom User-Agent, retry once

#### Test Criteria
```bash
# 1. Tag a test FLAC with MBID (using mutagen or Picard)
# 2. Remove embedded art from test file
# 3. Run test
python3 -c "
from core.artwork import ArtworkCache
cache = ArtworkCache(max_size_mb=10)
path = cache.get_art('~/test_music/no_art_but_tagged.flac')
print('Web fallback result:', path)
"
```

**Pass if:** Successfully fetches and caches web art for MBID-tagged files without embedded art; fails gracefully (returns `None`, no exception) for untagged files or network errors.

#### Known issues from CodeRabbit review
- Web lookups block the caller (~7s per track with no art) — deferred per developer request
- Art isn't restored after a restart — deferred per developer request
- The startup-scan check at line 174 of artwork.py can never be true because it compares a string to a Path
- CodeRabbit's PHASE_DEVELOPMENT_PLAN.md:266 service-user comment is unaddressed: update the "MPD runs as dedicated user" plan entry

#### Known issues from CodeRabbit review (fixed)
- Size-limit test now exercises eviction correctly (80KB cached with 40KB sidecar files, track 0 evicted)
- The online fallback has test coverage (the `test_web_fallback_mocked` smoke test in test_artwork.py)

#### Cleanup (non-blocking)
- `self._last_mbid` is set twice (lines 705 and 710 of artwork.py) and never read
- The docstring at line 689 says every redirect is validated, but the API request at line 713 still uses plain `urlopen`
- The `_resolve_mbid` docstring (lines 624-629) says Picard writes `musicbrainz_releaseid` for FLAC; it's actually `musicbrainz_albumid`
- No test for FLAC embedded art (VorbisComment pictures)
- No test for M4A embedded art (iTunes artwork atoms)
- No CI pipeline — would have caught the two parse failures and the failing test earlier in this PR
- The web fallback test still patches `_is_trusted_host` to always return True, so the allowlist isn't exercised
- CodeRabbit's service-user comment on line 266: update the "MPD runs as dedicated user" plan entry to match the installation guide's controller service user

---

### Slice 1.4: System Detection & Config Management ✅ Merged (PR #5, `2146ee4`)
**Goal:** Auto-detect runtime environment; generate appropriate MPD config

#### Deliverables
- `core/system.py` — `SystemDetector` class:
  - `detect_audio_backend()` → `'alsa' | 'pipewire' | 'pulse' | 'unknown'`
  - `detect_display_server()` → `'x11' | 'wayland' | 'unknown'`
    - **Wayland note**: Checks for `WAYLAND_DISPLAY` env var and presence of `XWayland`; Raspberry Pi OS Bookworm+ defaults to Wayland
  - `detect_distro()` → `'debian' | 'ubuntu' | 'fedora' | 'arch' | 'alpine' | 'nixos' | 'unknown'`
  - `get_mpd_config_template()` → path to appropriate `mpd.conf.*` template
  - `generate_mpd_conf(output_path='/etc/mpd.conf')` — writes MPD config with correct `audio_output` block for detected backend:
    - ALSA: `audio_output { type "alsa" ... }` with device selection (HDMI vs 3.5mm vs HAT DAC)
    - PipeWire: `audio_output { type "pipewire" ... }`
    - PulseAudio: `audio_output { type "pulse" ... }`
    - Null: `audio_output { type "null" ... }` (headless/testing)
- `configs/mpd.conf.alsa`, `.pipewire`, `.pulse`, `.null` templates
- `config.json` schema with detected values + user overrides

#### Technical Addendum (from review): MPD Config Generation
- **MPD talks to audio hardware directly** — Python never touches ALSA/PipeWire; `core/system.py` generates the `audio_output` block MPD uses
- Device selection: detect available ALSA devices (`aplay -L`), PipeWire nodes, or user-specified default
- Config file written to `/etc/mpd.conf` (root-owned), then MPD daemon restarted

#### Test Criteria (Manual)
```bash
# Run on target hardware (Pi Zero) and optionally in VMs
python3 -c "
from core.system import SystemDetector
d = SystemDetector()
print('Audio backend:', d.detect_audio_backend())
print('Display server:', d.detect_display_server())
print('Distro:', d.detect_distro())
print('MPD template:', d.get_mpd_config_template())
d.generate_mpd_conf('/tmp/test_mpd.conf')
# Verify: cat /tmp/test_mpd.conf | grep -q 'audio_output'  # should find valid block
"
```

**Pass if:** Correctly identifies backend on Pi OS Bookworm (ALSA or PipeWire depending on config), Fedora (PipeWire), Ubuntu (PipeWire); generates valid MPD config that MPD accepts; handles Wayland vs X11 detection for Pi OS Bookworm+ touchscreen edge cases

---

### Slice 1.5: Tkinter Touch UI — Core Dashboard ✅ Merged (PR #8, `e8cf7a8`)
**Goal:** Minimal touchscreen interface that controls playback

#### Deliverables
- `ui/styles.py` — Touch-friendly theme (48px minimum touch targets, high contrast)
- `ui/widget.py` — Reusable components: `TouchButton`, `ProgressBar`, `AlbumArtLabel`
- `ui/dashboard.py` — Main window with:
  - Large album art (center)
  - Track title / artist / album labels
  - Play/pause, next, previous, stop buttons
  - Volume slider
  - Progress bar (tap to seek)
  - Status indicator (playing/paused/stopped/connecting)
- Background thread polls MPD every 1s, updates UI via `root.after()`

#### Test Criteria
```bash
# On Pi Zero with touchscreen (or desktop with X11)
python3 main.py
```

**Manual verification checklist:**
- [ ] Window opens fullscreen (or configurable size)
- [ ] Album art displays (or placeholder)
- [ ] Track info updates when song changes
- [ ] Play/pause toggles playback
- [ ] Next/previous changes track
- [ ] Volume slider changes MPD volume
- [ ] Progress bar updates in real-time
- [ ] Tap progress bar seeks to position
- [ ] UI remains responsive during network hiccups
- [ ] Memory usage < 50 MB (check with `htop`)

---

### Phase 1 Integration Test
**Run after all slices complete:**
```bash
# Full smoke test
cd pi-music-player
python3 main.py &
sleep 5
# Verify: music plays, UI responds, art shows, volume works
# Kill and restart - should reconnect to MPD automatically
```
**Pass if:** All above work; survives MPD restart; survives network mount temporary disconnect.

---

## Phase 2: Play Statistics ✅ Complete

### Slice 2.1: Database Schema & Event Capture ✅ Merged (PR #7, `80adff5`)
**Goal:** Persistent local database tracking every play event

#### Deliverables
- `core/stats.py` — `PlayStats` class with SQLite backend:
  - Schema:
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
  - `record_play_start(track_info)` — called on track change
  - `record_play_end(completed: bool)` — called on track end/skip
  - Power-loss resilience *(as built: SQLite WAL mode with a commit per event; the planned 10s background flush thread was not needed)*

#### Test Criteria
```bash
python3 -c "
from core.stats import PlayStats
stats = PlayStats('/tmp/test_stats.db')
# Simulate playing a track
stats.record_play_start({
    'file': '/music/artist/album/track.flac',
    'artist': 'Test Artist',
    'album': 'Test Album',
    'title': 'Test Track',
    'duration': 180000
})
import time; time.sleep(0.1)
stats.record_play_end(completed=True)

# Query
for row in stats.get_recent_plays(limit=5):
    print(row)
print('Total plays:', stats.get_total_plays())
print('Artist stats:', stats.get_artist_stats('Test Artist'))
"
```

**Pass if:** Records survive process restart; queries return correct aggregates; database < 1KB per 100 plays.

---

### Slice 2.2: Statistics UI & Insights ✅ Merged (PR #9, `5835b74`)
**Goal:** Visualize play history in the dashboard

#### Deliverables
- New "Stats" screen in dashboard (swipe or button to access):
  - **Top Artists** (by play count, playtime)
  - **Top Albums**
  - **Most Played Tracks**
  - **Skip Rate** per artist/album (skips / total plays)
  - **Listening Time** by hour of day / day of week (heatmap)
  - **Recent History** (last 20 plays with timestamps)
- Export to CSV button (for personal analysis)

#### Test Criteria
```bash
# Manual: navigate to Stats screen
# Verify:
# - Numbers match actual plays
# - Charts render (text-based is fine for Pi)
# - Export creates valid CSV
```

**Pass if:** All stats views populate correctly; export opens in spreadsheet.

---

### Slice 2.3: Plugin System Hardening ✅ Merged (PR #10, `bdcab73`)
**Goal:** Make the plugin lifecycle reliable before more plugins are built on it

#### Deliverables
- `PluginManager.shutdown_all()` as an instance method (it was module-level, so `main.py` raised `AttributeError` on every exit)
- `unload_plugin()` removes the plugin's callbacks from the public hook registry, so reloads don't accumulate stale hooks
- `tests/test_slice_2_3.py` — load/initialize/shutdown, `shutdown_all`, enable/disable, reload from the recorded source directory, hook dispatch, capability/type queries, `auto_load: false`
- `docs/development/testing.md` — how to run the suites

#### Test Criteria
```bash
python3 tests/test_slice_2_3.py
python3 -m unittest discover -s tests -p "test_*.py"   # test_slice_1_1.py needs a running MPD
```

**Pass if:** All suites pass; quitting the app exits cleanly; reloading a plugin leaves exactly one copy of each hook.

---

### Phase 2 Integration Test
```bash
# 1. Play 20+ tracks naturally (mix of complete, skip, repeat)
# 2. Check Stats screen — verify all numbers plausible
# 3. Restart app — verify stats persist
# 4. Check DB size: ls -lh play_stats.db  # should be < 100KB
```

---

## Phase 3: Music Recommendations

### Slice 3.1: Recommendation Engine Core
**Goal:** Local-only "fans also played" suggestions — the first built-in plugin.
It exercises `PluginManager` load/unload and the `on_song_change` /
`on_playback_complete` hook dispatch end-to-end.

**Target Date:** 2026-12-15
**Estimated Effort:** 12 days

### Code Deliverables

- [ ] `plugins/recommendations/config.json` — Manifest for the first built-in
  plugin. Fields: `plugin_id: "recommendations"`, `name`, `version`,
  `type: "feature"`, `capabilities: ["recommendations"]`, `auto_load: true`,
  plus `settings` holding `recommendations.session_gap_seconds` (default 300)
  and `recommendations.scan_library_on_startup` (default `true`). The manifest's
  `settings_schema` describes the JSON-schema validation for these keys, while
  `settings` holds their actual values — these are separate concerns. The
  manifest deliberately does **not** hold a `stats.db_path`: the database path is
  app-level config, resolved in `initialize()` from the core engine (see below),
  so a user changing `stats.db_path` in `config.json` cannot leave the plugin
  pointed at a different, empty database. The loader only scans one level under
  `plugins/` (`plugins/__init__.py:81`), so the directory is
  `plugins/recommendations/`.

- [ ] `plugins/recommendations/recommendations.py` — `RecommendationEngine`
  extending `MusicPlayerPlugin`. Constructor is `__init__(self, config)` to
  match the base class and the manager's `plugin_class(manifest.data)` call
  (`plugins/__init__.py:161`); it reads `session_gap_seconds` from
  `config["settings"]["recommendations"]["session_gap_seconds"]` and
  `scan_library_on_startup` from
  `config["settings"]["recommendations"]["scan_library_on_startup"]`.

  In `initialize(self, core)` the engine resolves the database path from the
  **app** config, not its own manifest:
  `raw = core.config.get("stats.db_path", PlayStats.DEFAULT_DB_PATH)` then
  `self.db_path = os.path.expanduser(raw)`. `MusicPlayer` has no `config` of
  its own (its constructor takes only `host`, `port`, `timeout` —
  `core/player.py:21`), so `main.py` must attach it: `player.config = config`
  (see Dashboard wiring). If `core` or `core.config` is missing, fall back to
  `PlayStats.DEFAULT_DB_PATH` and log a warning, since in the real app that
  means the wiring is broken. Tests always give the core a config whose
  `stats.db_path` is a temporary file (see Test Plan), so they never touch the
  real `play_stats.db`.

  Public API:
  - `get_similar_artists(artist, limit=10)` — returns co-occurring artists
    ranked by `play_count DESC`. Pairs are stored in canonical order
    (`artist_a < artist_b`); the query checks **both** `artist_a` and
    `artist_b`, so direction of play does not matter. Same-artist pairs are
    never stored.
  - `get_recommendations_for_current()` — uses the currently playing track's
    `artist` (tracked by the engine) and the co-occurrence matrix.
  - `get_genre_radio(genre)` — returns a shuffled list of track paths from
    `album_songs` whose `genre` matches; `[]` when `album_songs` is empty.
  - `get_revisit_candidates(days=30)` — returns one track path per album that
    has not been played in the last `days` (one representative track path per
    album from `album_songs`), excluding recently played albums.
  - `get_new_to_you()` — artists from the library (`listallinfo`) absent from
    `play_stats.db`.
  - `initialize(self, core)` — stores `core`, registers hooks, resolves
    `self.db_path` from `core.config` (see above), opens the main-thread
    connection, and starts a background daemon thread for the library scan
    and/or rebuild. Returns `True`. The background thread opens its **own**
    SQLite connection **inside the thread** (see Notes/Risks); the main thread
    and the background thread never share a connection, so one thread's
    commit/rollback cannot include the other's partial writes.
  - `shutdown(self)` — signals the background thread to stop via a
    `threading.Event`, waits for it to finish (`thread.join()`), then closes its
    own connection. The background thread closes its own connection when it
    exits. It does **not** re-persist the matrix (it lives in SQLite) and does
    **not** unregister hooks (`unload_plugin()` already does that).

- [ ] Co-occurrence schema in `play_stats.db` (alongside `plays`):
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
  );

  CREATE TABLE IF NOT EXISTS cooccurrence_meta (
      id INTEGER PRIMARY KEY CHECK (id = 1),
      last_built_at INTEGER NOT NULL  -- Unix seconds, same type as plays.ended_at
  );
  ```
  `cooccurrence_meta` records when the matrix was last rebuilt so the startup
  staleness check can compare it with `MAX(plays.ended_at)` (a single-timestamp
  comparison, not two columns of `plays`). `last_built_at` is **INTEGER Unix
  seconds** — the same type as `plays.ended_at` (`core/stats.py:198`) — so the
  comparison is number-to-number, not text-to-number (SQLite sorts every
  number below every text value, so a TEXT stamp would always look newer than
  any play and the matrix would never be rebuilt). The rebuild
  writes into a temporary `cooccurrence_new` table and swaps it into place at the
  end (see below), so there is never a half-built matrix visible to lookups.
  The `genres` table is deliberately omitted — it duplicated `album_songs.genre`.
  The `idx_cooc_a` index is also omitted: the primary key already starts with
  `artist_a`.

- [ ] `MusicPlayer.list_all_info()` (in `core/player.py`) — new method calling
  MPD `listallinfo`. Returns a list of per-track dicts:
  `{"path", "artist", "album", "title", "genre", "time"}`. This is the source
  of library data; `get_genre_radio` and `get_new_to_you` both depend on it.

- [ ] Library scan: `fill_album_songs()` — reads `MusicPlayer.list_all_info()`
  and populates the `album_songs` table (`path`, `album`, `artist`, `genre`).
  This is a required deliverable, not optional: it is what gives
  `get_genre_radio` and `get_new_to_you` data to work with. `initialize()`
  calls it in a **background daemon thread** when the `album_songs` table is
  empty and `scan_library_on_startup` is `true`, so the dashboard is not
  blocked on a large library. While the scan runs, genre/revisit queries
  return empty lists until data is available.

- [ ] Dashboard wiring (required for hooks to fire in the real app):
  - [ ] `main.py` sets `player.config = config` right after creating the
    player and **before** `plugin_mgr.load_plugins()`, so the plugin can read
    the app-level `stats.db_path` in `initialize()`.
  - [ ] `main.py` passes `plugin_mgr` to `run_dashboard(...)`,
    and `run_dashboard` forwards it to the `Dashboard` class (it is `_update_ui`
    — a Dashboard method — that raises the hooks).
  - [ ] `ui/dashboard.run_dashboard()` calls
    `plugin_mgr.trigger_hook("on_song_change", track_info)` when `_update_ui`
    starts playing a new track, carrying
    `{artist, album, title, path, started_at}`.
  - [ ] `ui/dashboard.run_dashboard()` calls
    `plugin_mgr.trigger_hook("on_playback_complete", track_info, completed,
    skipped)` when `_update_ui` detects a track end/skip.

- [ ] Session rules (shared by live recording and `build_from_history`):
  - `track_info.started_at` and the engine's stamped `ended_at` are both
    **integer Unix seconds** (`int(time.time())`, as `plays` stores them —
    `core/stats.py:158`, `:198`), so the 5-minute gap check compares like with
    like.
  - A listening session is a run of completed plays where the gap between one
    track's `ended_at` and the next track's `started_at` is `< 5 minutes`
    (`session_gap_seconds`).
  - **Any play that is not completed ends the session** — a skip *and* a stop
    (Stop button / app close, `completed=False, skipped=False`) both end the
    current run; the next completed play starts a new run. This matches
    `build_from_history`, which treats any incomplete `plays` row as a session
    end.
  - Pairs are recorded once, in canonical order (`artist_a < artist_b`).
  - Same-artist pairs and blank artists are **not** recorded.
  - Consecutive completed plays with a gap `< session_gap_seconds` yield a
    pair; otherwise no pair.

- [ ] Live pairing with two slots (`self.last_finished`, `self.current`) —
  avoids pairing a track with itself:
  - `on_song_change(track_info)` — `track_info` carries
    `{artist, album, title, path, started_at}`. Stores `self.current = track_info`
    and updates `self._current_artist`; **no pairing happens here** — pairing is
    deferred to completion so that skipped/stopped tracks are never paired.
  - `on_playback_complete(track_info, completed, skipped)` — pairing happens
    here: if `completed` and both `self.current` and `self.last_finished` are set
    and `current.started_at - last_finished.ended_at < session_gap_seconds`,
    record the pair `(last_finished.artist, current.artist)` in canonical order.
    Then `self.last_finished = self.current.copy()` with `ended_at` stamped,
    and clear `self.current` (so a repeat-one completion does not pair a track
    with itself). `cooccurrence_meta.last_built_at` is set to that play's
    `ended_at` (not "now"), so live play does not make the matrix look stale
    next startup and the stamp can never be newer than the play it covers.
    If the play is **not completed** (whether a skip or a stop with
    `completed=False, skipped=False`), clear **both** slots
    (`last_finished` and `current`) — any non-completed play breaks the session,
    matching `build_from_history`. Because pairing happens on completion rather
    than at song change, a track is never paired with itself.

- [ ] `build_from_history()` — rebuilds the matrix from `plays` rows using the
  same session rules above (completed plays, `< session_gap_seconds` gaps,
  canonical order, no same-artist or blank pairs), writing into a temporary
  `cooccurrence_new` table; when complete it atomically swaps into
  `cooccurrence`, so lookups never see a half-built matrix. It stamps
  `cooccurrence_meta.last_built_at` with the `MAX(plays.ended_at)` it read **at
  the start** of the rebuild, so plays that finish while it runs are newer than
  the stamp and are picked up next time. Runs in a batch loop per segment so no
  single transaction blocks. While it runs, live pair recording **waits** on a
  `threading.Lock` (pairs are never dropped) and is written once the swap is
  done, so live writes cannot be wiped or counted twice.

- [ ] Startup rebuild (one-shot): `initialize()` compares
  `cooccurrence_meta.last_built_at` with `MAX(plays.ended_at)` (both INTEGER
  Unix seconds). If the meta row is missing or older than the latest play, it
  runs `build_from_history()` in the background thread (alongside the library
  scan) so the dashboard opens immediately. There is no scheduler; rebuild is
  startup-only and on demand. Live pair recording updates
  `cooccurrence_meta.last_built_at` too (to each play's `ended_at`), so a
  steady stream of live plays does not mark the matrix stale on the next
  startup.

### Documentation Deliverables

- [ ] Update `docs/features/recommendations.md` — add the config defaults
  (`stats.db_path`, `recommendations.session_gap_seconds`,
  `recommendations.scan_library_on_startup`), the session/pairing rules, the
  test plan section, and Pi Zero 2 W performance notes.
- [ ] Update `docs/development/plugin-api.md` (the file already exists) —
  expand the `RecommendationEngine` API reference: method signatures, the two
  hook events and the payload each carries, and the config schema.
- [ ] Update `docs/usage/dashboard-guide.md` — describe how the engine hooks
  into the dashboard (the dashboard raises the two events).
- [ ] Update `README.md` — mark Phase 3 as in progress, add `recommendations`
  to the feature table.
- [ ] Update `docs/development/testing.md` — add `tests/test_slice_3_1.py`
  to the Test Layout table.

### Test Plan

```bash
# Run the new slice tests
python -m unittest tests.test_slice_3_1 -v

# Run full suite (should be green)
python -m unittest discover -s tests -p "test_*.py"

# Verify plugin loads/unloads with a real MusicPlayer + Config, wired the way
# main.py wires it, but pointed at a temp database and with the library scan off
# (the player is not connected to MPD), so it never touches the real play_stats.db.
python3 -c "
import sys, tempfile, os, shutil, json; sys.path.insert(0, '.')
from plugins import PluginManager
from core.player import MusicPlayer
from core.config import Config
d = tempfile.mkdtemp()
dst = os.path.join(d, 'recommendations')
shutil.copytree('plugins/recommendations', dst)
man = os.path.join(dst, 'config.json')
m = json.load(open(man))
m.setdefault('settings', {}).setdefault('recommendations', {})['scan_library_on_startup'] = False
json.dump(m, open(man, 'w'))
db = os.path.join(d, 'test_play_stats.db')
cfg_path = os.path.join(d, 'app_config.json')
json.dump({'stats': {'db_path': db}}, open(cfg_path, 'w'))
player = MusicPlayer(host='localhost', port=6600)
player.config = Config(cfg_path)   # as main.py does: player.config = config
mgr = PluginManager(core_engine=player, plugin_dir=d)
print('Loaded', mgr.load_plugins(), 'plugin(s) (expected 1)')
rec = mgr.get_plugin('recommendations')
print('db_path:', rec.db_path)
assert rec.db_path == db, 'plugin must use the app config path'
mgr.shutdown_all()
print('Shutdown complete')
"
```
Tests use a **temporary database** populated with prepared `plays` rows and
`listallinfo` fixtures, never a real listening history. Unit tests may use a
stub `MusicPlayer`; at least one test uses a real `MusicPlayer` with
`player.config = Config(<temp config>)` to prove the `main.py` wiring resolves
`stats.db_path` from the app config. `initialize()` must tolerate a core with no
`list_all_info` or no MPD connection (it skips the library scan) so it is
testable in isolation.

### Acceptance Criteria

- [ ] Plugin loads without error via `PluginManager.load_plugins()` from
  `plugins/recommendations/` (a plain `PluginManager(plugin_dir='plugins')`
  discovers it).
- [ ] `get_similar_artists('Radiohead')` returns a ranked list after ≥50
  completed plays are recorded in a temporary DB; returns `[]` with no data.
- [ ] Event timestamps `started_at` / `ended_at` are integer Unix seconds;
  the 5-minute gap check compares like with like.
- [ ] Similar-artist lookup is **bidirectional**: an artist that was always
  played *before* the queried artist is still returned (pair stored once in
  canonical order, queried against both columns).
- [ ] Same-artist pairs are never returned (a track never ranks itself).
- [ ] `get_genre_radio('Blues')` returns shuffled track paths from
  `album_songs` whose `genre` matches (empty when the table is empty).
- [ ] `get_revisit_candidates(days=30)` returns one track path per album that
  has not been played in the last 30 days; excludes recently played albums.
- [ ] `get_new_to_you()` returns library artists absent from `play_stats.db`
  (after a library scan).
- [ ] **Stops break the session**: a stopped track (`completed=False,
  skipped=False`) produces no pair across the boundary (both live and
  `build_from_history`).
- [ ] Skips break the session: a skipped track produces no pair across the
  boundary (both live and `build_from_history`).
- [ ] Live pairing never pairs a track with itself (two-slot logic).
- [ ] No network calls (no `requests` / `urllib` imports in the plugin).
- [ ] Hook callbacks fire on `on_song_change` and `on_playback_complete`
  raised by the dashboard; `unload_plugin('recommendations')` returns `True`.
- [ ] Speed target: `get_similar_artists` completes in **< 200 ms on a Pi Zero
  2 W** for a library with ~1,000 artists (measured **manually on the Pi**;
  desktop tests assert functional correctness plus a looser bound, e.g.
  < 500 ms, because CPU differs).
- [ ] Startup does not block: the dashboard opens immediately while the
  background library scan and rebuild run.
- [ ] All existing tests continue to pass.

### Dependencies

- Requires: Slice 2.1 complete (`play_stats.db` schema, `plays` table),
  Slice 2.3 complete (`PluginManager` lifecycle + hook cleanup).
- Blocks: Slice 3.2 (Discovery UI renders recommendations).

### Notes / Risks

- **Risk:** Background thread shares a connection with the main thread.
  Mitigation: the background thread opens its **own** SQLite connection inside
  the thread (not in `initialize()`). The main thread keeps its own connection
  for live queries; they never share a transaction, so one thread's
  commit/rollback cannot include the other's partial writes. The main thread
  opens with `check_same_thread=False` so it can be used from another thread
  if ever needed, but it is not shared.
- **Risk:** Staleness check compares `last_built_at` (TEXT) with
  `MAX(plays.ended_at)` (INTEGER) → SQLite sorts numbers below text, so the
  matrix would never look stale. Mitigation: `last_built_at` is **INTEGER Unix
  seconds** (same type as `plays.ended_at`), so the comparison is
  number-to-number.
- **Risk:** Shutdown during a scan: `shutdown()` signals a `threading.Event`
  for the thread to stop, waits (`thread.join()`), then closes its own
  connection; the background thread closes its own connection on exit.
- **Risk:** Co-occurrence matrix grows large with many artists. Mitigation:
  the canonical `(artist_a, artist_b)` primary key bounds growth; queries use
  `LIMIT 10`; `build_from_history()` writes in batches.
- **Risk:** `play_stats.db` and the recommendation tables share one file —
  concurrent writes between `PlayStats.record_play_start/end()` and the
  engine's queries. Mitigation: SQLite WAL mode (already enabled in
  `PlayStats.__init__`) and short transactions.
- **Risk:** Startup scan/rebuild on a large library is slow on a Pi Zero 2 W.
  Mitigation: both run in a background daemon thread so the dashboard opens
  immediately; queries degrade gracefully (empty lists) until data is ready.
- **Risk:** Genre data is missing until the library scan runs. Mitigation:
  `scan_library_on_startup` defaults to `true`; `get_genre_radio` returns `[]`
  when `album_songs` is empty.
- **Deferred:** Genre extraction from mutagen file tags (richer than
  `listallinfo.genre`) — later slice.
- **Deferred:** `trigger_hook()` currently dispatches only callbacks registered
  through `MusicPlayerPlugin.register_hook()` (stored in `_plugin_hooks`);
  callbacks added directly to `PluginManager.hooks` via the public
  `register_hook()` are not dispatched. This slice registers hooks the
  plugin-way, so it is unaffected; the gap is a separate hardening item.

---

### Slice 3.1a: Touch Toolkit
**Goal:** Gesture and scrolling widgets that any screen can reuse, so Slice 3.2 and later screens don't each build their own touch handling.

**Why now:**
- The Discover screen in Slice 3.2 needs scrollable lists of tracks, artists and albums.
- The only drag scrolling in the app today belongs to the Stats screen. The handlers are at `ui/dashboard.py:468–503`, with per-label bindings up to `:635`, and the wheel handler starts at `:460`.
- Slice 2.2 promised a swipe to open Stats, but it was never built.

**Already in place (keep):**
- `ui/styles.py` sets 48 px minimum touch targets.
- `TouchWidget._apply_visual_feedback` already highlights a widget while it is pressed, using `COLORS["accent"]`.

**Target Date:** TBD (after Slice 3.1)
**Estimated Effort:** 5 days

### Code Deliverables
- [ ] `ui/gestures.py` — `GestureRecognizer`, written as pure Python with no Tk imports, so it can be unit-tested without a display.
  - **Input:**
    - `press(x, y, t)`, `move(x, y, t)` and `release(x, y, t)`, with `t` in seconds from a monotonic clock that the caller supplies.
    - `GestureRecognizer(width_fn)`: `width_fn()` returns the current window width in pixels. The recognizer reads it at release time to work out the swipe threshold, so a resized window is handled. The adapter passes `lambda: root.winfo_width()`, and tests pass a constant.
    - `timeout(t)`, which the adapter calls when the long-press timer fires. The recognizer never schedules anything itself.
  - **Output contract, per press:**
    - first, zero or more `drag_move(dx, dy)` events;
    - then **exactly one** final event: `tap`, `long_press`, `drag_end(vx, vy)` or `swipe(direction, velocity)`.
  - **Slop boundary:** movement up to and including `TAP_SLOP` (10 px) counts as "not moved". A press becomes a drag only when movement is **greater than** `TAP_SLOP`.
  - **Long press:** `timeout(t)` arrives with `t - press_t >= LONG_PRESS_MS` (500 ms) and movement still ≤ `TAP_SLOP`. It fires while the finger is still down. The release that follows produces nothing more.
  - **Tap or late long press:** a release that is not part of a drag, and comes before any `long_press` has fired, is classified on release:
    - `long_press` if `t - press_t >= LONG_PRESS_MS`. This covers a timer that ran late because Tk was busy;
    - `tap` otherwise.

    So every non-drag release produces exactly one final event, and a late timer arriving after the release is ignored.
  - **Drag:** once movement is greater than `TAP_SLOP`, the press becomes a drag. After that, no tap or long press can fire.
  - **Swipe:** a drag that is released with all of the following:
    - horizontal movement of at least `max(SWIPE_MIN_PX, 0.10 × width_fn())`, where `SWIPE_MIN_PX` is 80 px;
    - a duration under `SWIPE_MAX_MS` (400 ms);
    - `|dx| > 2·|dy|`.

    Directions are `left` and `right`. Any other drag ends as `drag_end`.
  - All thresholds live in `ui/styles.py` as a `GESTURE` dict.
- [ ] `ui/gestures.py` — `bind_gestures(widget, recognizer, on_event, exclude=())`, a thin Tk adapter.
  - **Bindings:** it binds `<ButtonPress-1>`, `<B1-Motion>` and `<ButtonRelease-1>` with `add="+"`, on `widget` **and every descendant**.
    - X11 sends motion and release events only to the widget that was pressed (an implicit grab), so binding only the parent would miss presses that start on a child.
    - It never binds on the root window or on the `all` bindtag.
    - Widgets in `exclude` are skipped, along with their descendants. The `ProgressBar`, which seeks on `<Button-1>`, is always excluded.
  - **Coordinates:** converts each event to root coordinates (`event.x_root`, `event.y_root`). `Dashboard._canvas_coords` (added in PR #9, `5835b74`) converts to canvas-local coordinates instead, so it is not reused here.
  - **Timestamps:** uses `time.monotonic()` read inside each handler, not `event.time`. The `event.time` value is in milliseconds, wraps around at 32 bits (about every 49.7 days), and is 0 for `event_generate`, which the tests rely on.
  - **Long press:** on press it starts `widget.after(LONG_PRESS_MS, lambda: recognizer.timeout(time.monotonic()))`, and it cancels that timer on drag or release.
  - **Stopping the button firing.** As soon as the recognizer reports a drag or a long press, the adapter calls `set_pressed_state(False)` on any `TouchButton`/`TouchWidget` under the press.
    - Today, `TouchButton._on_release` runs its command whenever `_is_pressed` is still set, and only `_on_leave` clears it (`ui/widget.py:119–123`).
    - In a scrolling list the button moves with the finger, so the finger never "leaves" it. Without this step, the command would fire at the end of every drag.
- [ ] `ui/widget.py` — `ScrollList(tk.Frame)`, a vertical list with drag scrolling and momentum.
  - API: `set_items(items, render_row)`, `scroll_to_top()`, `on_select(callback)` (fires on `tap` only) and `on_swipe(callback)` (passes a horizontal swipe up to the screen).
  - Built on a `tk.Canvas` with `yscrollincrement=1`, holding an inner frame. Both dragging and momentum use `yview_scroll(n, "units")`, so one unit is one pixel. The fractional remainder is carried between frames, and rows are never redrawn.
  - **Momentum:**
    - On `drag_end`, scrolling carries on at the release speed, multiplied by `FRICTION` (0.90) each frame.
    - Frames run every `FRAME_MS` (33 ms) via `after()`. Scrolling stops below 0.5 px per frame, or when it reaches either end of the list.
    - A new press cancels momentum immediately.
    - The speed step is a pure function in `ui/gestures.py`, so it can be tested without a display.
  - **Mouse wheel:** keep `<MouseWheel>` for Windows and macOS, and add `<Button-4>` / `<Button-5>` for X11 (the Pi). Today only `<MouseWheel>` is bound (`ui/dashboard.py:470–471`), and it never fires on X11.
  - **Large lists:** fine up to about 200 rows. For bigger libraries, Slice 3.2 shows the first 200 plus a "More" row, rather than building thousands of widgets on a Pi Zero.
- [ ] `ui/dashboard.py` — move the Stats screen onto `ScrollList`.
  - Delete `_on_stats_drag_start` and `_on_stats_drag_move`, the per-label drag bindings and the old wheel handler.
  - Keep `_canvas_coords` only if something still uses it.
- [ ] `ui/dashboard.py` — swipe navigation.
  - **Where swipes are recognized:**
    - on Now Playing, through `bind_gestures` on the main content frame (the `ProgressBar` is excluded);
    - on list screens, through `ScrollList.on_swipe`. Vertical drags scroll the list, and only a drag that passes the swipe test navigates.
  - **Directions:**
    - swipe left goes from Now Playing to Stats (and to Discover, once Slice 3.2 adds it);
    - swipe right goes back.
  - The existing buttons stay, so every action still works without gestures.
- *Moved to Slice 3.2:* long press on Play/Pause to show the queue. That needs a new screen, and the queue is Slice 3.2's subject. This slice delivers long-press recognition and its tests, and the button suppression above, so 3.2 can use it safely.

### Documentation Deliverables
- [ ] Rewrite `docs/usage/touch-gestures.md` to match what is built.
  - Tkinter receives touch as single-pointer mouse events, so remove the multi-touch claims and the "swipe intensity" and edge-swipe sections.
  - Remove the settings at `:248–253`. None of them exist in `core/config.py`.
  - Keep tap, long press, drag scrolling with momentum, and left/right swipe. Mark anything still planned as *Planned*.
- [ ] New `docs/development/ui-widgets.md`, explaining how new screens use `ScrollList` and `bind_gestures`, including the `exclude` rule for widgets that handle their own presses.
- [ ] `docs/development/testing.md` — add `tests/test_slice_3_1a.py` to the Test Layout table.

### Test Plan
```bash
# Headless: gesture logic and momentum, no display needed
python -m unittest tests.test_slice_3_1a -v

# Full suite (the dashboard tests need a display; see testing.md)
xvfb-run -a python -m unittest discover -s tests -p "test_*.py"

# Manual on the Pi touchscreen:
# - Flick the Stats list: it keeps scrolling briefly, then slows to a stop
# - Touch while it is scrolling: it stops at once
# - Drag starting on a row button: the list scrolls and the button does NOT fire
# - Tap a row: it fires once
# - Swipe left on Now Playing: Stats opens; swipe right: back
# - Drag along the progress bar: it seeks and does NOT navigate
# - A slow sideways drag (> 400 ms) does NOT count as a swipe
# - Mouse wheel scrolls the Stats list under X11
```

**Headless gesture tests.** `tests/test_slice_3_1a.py` feeds synthetic `(x, y, t)` sequences, plus `timeout(t)` calls, into `GestureRecognizer`. It needs no display. It covers:
- a press that stays under the slop distance;
- a 520 ms hold, with the timeout delivered while the finger is down;
- a 520 ms hold released **before** the timeout is delivered (late timer), which gives `long_press` on release, and a timeout that arrives after the release, which gives nothing;
- movement of exactly 10 px (`tap`), and of 11 px (drag);
- the same 100 px horizontal flick with `width_fn` returning 800 (`swipe`) and 1200 (`drag_end`, since the threshold is 120 px);
- a drag past the slop distance;
- fast and slow horizontal moves;
- diagonal moves that fail the `|dx| > 2·|dy|` test.

For every sequence it asserts the contract: zero or more `drag_move` events, then exactly one final event.

**Momentum tests** treat the speed step as a pure function. They check the speed after N frames, the stopping point, the clamping at the list ends, and that a new press cancels the scroll.

**Tk adapter test.** One test drives the adapter with `event_generate` on a `ScrollList` whose row is a `TouchButton`. It asserts that a press, motion and release sequence scrolls the list and does **not** call the button's command. Like the existing dashboard tests, it needs a display.

### Acceptance Criteria
- [ ] All gesture unit tests pass, and the existing suites stay green.
- [ ] **Momentum smoothness on the Pi.** With a debug frame-timing log enabled, a flick on the Stats list with 200 rows meets both targets:
  - median frame interval ≤ 40 ms;
  - 95th percentile ≤ 70 ms.
- [ ] No tap fires at the end of a drag, on rows or on buttons.
- [ ] Swipe navigation works in both directions and never fires from the progress bar. Every gesture action still has a button.
- [ ] **Memory check:** the app's memory use stays within the Phase 3 budget (40 MB) with a 200-row `ScrollList` open.

### Dependencies
- Requires: Slice 1.5 (dashboard and `TouchWidget`), Slice 2.2 (Stats screen being migrated).
- Blocks: Slice 3.2 (Discover lists use `ScrollList`; long press opens the queue).

### Notes / Risks
- Risk: X11's implicit grab means a binding on a parent never sees a drag that starts on a child.
  - Mitigation: `bind_gestures` binds every descendant with `add="+"`, and the Tk adapter test covers a drag that starts on a button.
- Risk: building a widget per row is too slow for large libraries on a Pi Zero.
  - Mitigation: the 200-row cap with a "More" row. If the frame targets fail at 200 rows, switch to drawing rows as canvas items.
- Risk: the swipe and vertical-scroll tests disagree near the diagonal.
  - Mitigation: the `|dx| > 2·|dy|` test leaves a dead zone, so a diagonal move scrolls and never navigates.

---

### Slice 3.2: Discovery Features in UI
**Goal:** Surface recommendations in the dashboard

**Requires:** Slice 3.1, Slice 3.1a

#### Deliverables
- New "Discover" screen:
  - **"Play Similar"** button on Now Playing → queues similar tracks
  - **"Genre Radio"** — pick genre, plays endless shuffle
  - **"Revisit"** — albums you haven't played in 30+ days
  - **"New to You"** — artists in library but never played (via the library scan from Slice 3.1, MPD `listallinfo`)
- "Add to Queue" / "Play Next" actions
- Discover lists use `ScrollList`, and Discover is reachable by swiping (Slice 3.1a)
- Long press on Play/Pause opens the queue view, using the `long_press` recognition from
  Slice 3.1a. Releasing after a long press must not toggle playback.

#### Test Criteria
```bash
# Manual on device:
# - Play a track
# - Tap "Play Similar" → queue populates with related tracks
# - Tap "Genre Radio" → plays continuous genre shuffle
# - "Revisit" shows stale albums
```

**Pass if:** All features work; queue manipulation doesn't break playback.

---

### Phase 3 Integration Test
```bash
# 1. Build library with 500+ tracks across genres
# 2. Listen naturally for a week
# 3. Verify recommendations feel relevant
# 4. Check CPU/memory during recommendation refresh (should be negligible)
```

---

## Phase 4: Remote Control

### Slice 4.1: Local Web API
**Goal:** REST API for remote control

#### Deliverables
- `plugins/remote.py` — `RemoteServer` (runs on `localhost:8080`):
  - Endpoints:
    - `GET /api/status` — current song, position, volume, state
    - `GET /api/queue` — current playlist
    - `POST /api/control` — `{action: play|pause|next|prev|stop|volume|seek}`
    - `GET /api/art` — current album art (serves cached image)
    - `GET /api/library` — browse artists/albums (paginated)
    - `POST /api/queue/add` — add track/album to queue
  - Token auth (random token on startup, printed to console + QR code)
  - CORS enabled for LAN access

#### Test Criteria
```bash
# Start app, note token from console
curl -H "Authorization: Bearer <token>" http://localhost:8080/api/status
curl -X POST -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"action": "next"}' \
  http://localhost:8080/api/control
```

**Pass if:** All endpoints respond < 100ms; controls actually affect playback; token required.

---

### Slice 4.2: Web Dashboard (Optional)
**Goal:** Phone-friendly web UI

#### Deliverables
- Static HTML/JS served from `/web/` directory:
  - Now playing with album art
  - Playback controls
  - Queue view with drag-to-reorder
  - Library browser
  - Volume slider
- Works on mobile Safari/Chrome without app install

#### Test Criteria
```bash
# On phone browser: http://<pi-ip>:8080
# Verify: all controls work, art loads, queue reordering persists
```

---

### Phase 4 Integration Test
```bash
# 1. Start player on Pi
# 2. Open web UI on phone
# 3. Control playback entirely from phone for 30 min
# 4. Verify: no UI lag, art loads, queue edits work
```

---

## Phase 5: Polish & Niche Features

### Slice 5.0: Config-Driven Themes
**Goal:** Colours and text sizes come from `config.json` instead of constants, with three built-in themes. Car Mode's night mode reuses a theme instead of having its own tint.

**Current state:**
- `ui/styles.py` hard-codes `COLORS`, `FONTS` and `TOUCH_TARGET_SIZE` (an int).
- `core/config.py:32` already has `ui.theme: "dark"`, but nothing reads it. `Config` deep-merges user values over defaults and does **no** validation.
- **Colour defaults are fixed when the module is imported.** `TouchButton.__init__` takes `bg: str = COLORS["card_bg"]` and similar defaults (`ui/widget.py:82–85`), and Python evaluates them once, at import. Changing `COLORS` afterwards never reaches those defaults.
- **The touch size can't change in place either.** `TOUCH_TARGET_SIZE` is an int, and each importing module holds its own copy (`ui/widget.py:22, 23, 98, 99, 349, 350`).
- **Fixed sizes block bigger text.** `ui/dashboard.py:164`, `:178` and `:203` hard-code sizes (album art and others), so `large_text` would clip at 800×480 unless those scale too.
- **The dashboard can't be rebuilt in place.** `Dashboard` *is* the Tk root (`class Dashboard(tk.Tk)`, `ui/dashboard.py:77`), and its widgets are gridded straight onto it, with no inner frame that could be destroyed and rebuilt.

**Target Date:** TBD (Phase 5)
**Estimated Effort:** 4 days

### Code Deliverables
- [ ] `ui/styles.py` — a `THEMES` dict with three themes:
  - `dark` holds today's values and is the default, matching the existing `ui.theme: "dark"`. `default` is accepted as an alias.
  - `night` is a dim, red-shifted palette for dark rooms and cars.
  - `large_text` uses the dark colours, fonts about 1.4× larger, and a touch target of 64.
- [ ] `ui/styles.py` — replace the int `TOUCH_TARGET_SIZE` with a `TOUCH` dict (`{"target": 48, …}`), and update its six uses in `ui/widget.py`.
- [ ] `ui/styles.py` — a `SIZES` dict for the fixed sizes at `ui/dashboard.py:164`, `:178` and `:203`. `apply_theme()` works them out **once at startup** from the theme and `font_scale`. Widgets read them only when they are built, so they keep those values until the next start.
- [ ] `ui/widget.py` — no colour or size defaults evaluated at import.
  - Change the `TouchButton` (and any similar) parameters to `bg=None, fg=None, active_bg=None, active_fg=None`, and look them up in the body: `bg = COLORS["card_bg"] if bg is None else bg`.
- [ ] `ui/styles.py` — `apply_theme(name, overrides=None, font_scale=1.0)`.
  - **Updates in place:** it updates `COLORS`, `SIZES` and `TOUCH` with `.clear()` and `.update()`, so existing `from ui.styles import COLORS` imports stay valid.
  - **Validation:** this is the only place theme settings are checked, because `Config` does none.
    - An unknown theme name logs a warning and falls back to `dark`.
    - `font_scale` is clamped to 0.75–2.0, with a warning.
    - A colour override that isn't `#rrggbb`, or names an unknown key, is ignored with a warning.
  - Must be called before any widget is created.
- [ ] `ui/styles.py` — fonts become named `tkinter.font.Font` objects.
  - `init_fonts(root)` creates them once the Tk root exists, and `FONTS` maps names to those objects.
  - `set_font_scale(scale)` calls `font.configure(size=…)` on each one, and Tk redraws every widget that uses them **while the app runs**, with no rebuild needed.
  - **Text only:** a live change resizes text, but not the layout sizes in `SIZES`. It also writes `ui.font_scale` to the config, so the layout sizes catch up on the next start.
  - **Clipping:** at 800×480, text can clip between a live increase and that restart. The Settings screen says "Layout adjusts after restart". Re-laying out existing widgets live is out of scope.
- [ ] `core/config.py` — new defaults next to the existing `ui.theme: "dark"`:
  - `ui.colors: {}`, for per-colour overrides such as `{"accent": "#ff8800"}`;
  - `ui.font_scale: 1.0`.
- [ ] `main.py` — call `apply_theme(config.get("ui.theme"), config.get("ui.colors"), config.get("ui.font_scale"))` **before** `run_dashboard()`. `Dashboard.__init__` then calls `init_fonts(self)`.
- [ ] **Switching themes:**
  - The Settings screen writes `ui.theme` to the config, and the new colours take effect after a restart, with a "Restart to apply" prompt.
  - Text size (`font_scale`) applies live through the named fonts. Layout sizes (`SIZES`) follow on the next restart.
  - Live colour switching is **out of scope**. It would need every widget recoloured or the screen rebuilt, which the current `Dashboard` structure doesn't support.

### Documentation Deliverables
- [ ] `docs/usage/dashboard-guide.md` — a themes section covering the config keys, the three themes, which settings apply live (text size) and which after a restart (theme, colours, layout sizes).
- [ ] README feature table — add "Themes".

### Test Plan
```bash
python -m unittest tests.test_slice_5_0 -v      # Tk tests skip without a display
xvfb-run -a python -m unittest discover -s tests -p "test_*.py"
```

**Tests that need no display:**
- `apply_theme("night")` changes the `COLORS` object that `ui.widget` imported: the same object, with new values.
- `TOUCH["target"]` is 64 after `apply_theme("large_text")`.
- An unknown theme name falls back to `dark`, and `default` is treated as `dark`.
- `font_scale` 3.0 is clamped to 2.0, and a bad colour override is ignored. Each logs a warning.

**Tests that need Tk.** These are decorated with `unittest.skipUnless(_tk_available(), …)`, where `_tk_available()` tries `tk.Tk()`. That way the single-file command passes headless, and `xvfb-run` runs them in full.
- After `apply_theme("night")`, a newly created `TouchButton` has `cget("bg") == COLORS["card_bg"]`, using night's value.
- `set_font_scale(1.5)` changes the size of every named font, and a label using one of them reports the new size.

### Acceptance Criteria
- [ ] All three themes render on the Pi at 800×480 without clipped text, including `large_text`.
- [ ] Changing the text size in Settings resizes text immediately, without interrupting playback. After a restart, every `font_scale` from 0.75 to 2.0 renders at 800×480 without clipped text.
- [ ] Changing the theme applies after a restart, and the restart closes the current play row cleanly through the normal shutdown.
- [ ] An existing `config.json` with `ui.theme: "dark"` behaves exactly as before.
- [ ] **Memory check:** usage stays within the Phase 5 budget (50 MB).

### Dependencies
- Requires: Slice 1.4 (config defaults), Slice 1.5 (dashboard and widgets).
- Blocks: Slice 5.3 (Car Mode uses the `night` theme).

### Notes / Risks
- Risk: a widget added later uses a colour as a default argument again, so themes stop reaching it.
  - Mitigation: the `cget("bg")` test, plus a note in `docs/development/ui-widgets.md`.
- Risk: users expect the theme to change immediately.
  - Mitigation: the Settings screen says "Restart to apply". Live recolouring can be its own slice if it's wanted.

---

### Slice 5.1: Sleep Timer & Fade-Out
- Background thread: after N minutes, fade volume over 60s then pause
- UI: timer picker (15/30/45/60/90/120 min)

### Slice 5.2: Voice Wake-Word (Optional)
- Uses `pvporcupine` or `vosk` for offline "Hey Player" detection
- Commands: play, pause, next, volume up/down
- Runs in background thread; minimal CPU

### Slice 5.3: Car Mode
- Simplified UI: 4 giant buttons (Play/Pause, Next, Prev, Home)
- Auto-enable when Bluetooth device "CarKit" connects
- Night theme (Slice 5.0) after sunset. Themes apply at startup (Slice 5.0), so this slice:
  - selects `night` at launch if the app starts after sunset;
  - shows a "Switch to night theme? (restarts the app)" prompt at sunset while the app is running.
    Accepting saves `ui.theme` and restarts; playback state is not kept across the restart.
  - Switching live, without a restart, is an optional stretch goal that needs a live-recolouring
    pass; it is not required for this slice.

### Slice 5.4: Battery/Power Monitoring
- Read `/sys/class/power_supply/*/capacity` for battery %
- Display in status bar
- Low-battery warning at 20%, auto-pause at 10%

---

## Dependency & Build Pipeline (Cross-Cutting)

### Slice B1: Frozen Executable
```bash
# Goal: Single binary that runs without Python installed
pyinstaller --onefile --name pi-music-player main.py
# Test: copy binary to fresh Pi OS lite, run
```

### Slice B2: Distro Install Scripts
```bash
# scripts/install-debian-ubuntu.sh
# - Installs mpd, python3-tk, python3-pip, cifs-utils
# - Creates player user, sets up fstab template
# - Deploys systemd service
# Test: fresh Pi OS → run script → reboot → music plays
```

### Slice B3: CI Pipeline
- GitHub Actions matrix: Debian, Ubuntu, Fedora, Arch, Alpine (via QEMU)
- Steps: install deps → run unit tests → memory profile → build binary

---

## Recommended Order of Execution

| Order | Slice | Why |
|-------|-------|-----|
| 1 | 1.1 | Everything depends on MPD connection |
| 2 | 1.4 | Need config before UI can start reliably |
| 3 | 1.2 | Art is visual feedback for "it works" |
| 4 | 1.5 | First playable UI — huge morale boost |
| 5 | 1.3 | Polish art fallback |
| 6 | B1 | Get binary working early |
| 7 | 2.1 | Stats need real usage data |
| 8 | 2.2 | See your data |
| 8a | 2.3 | Harden plugins before building more on them |
| 9 | 3.1 | Recommendations need stats |
| 9a | 3.1a | Touch toolkit before building more screens |
| 10 | 3.2 | Surface recommendations |
| 11 | 4.1 | Remote is force multiplier for testing |
| 12 | 5.x | Polish features as desired |

---

## Risk Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| MPD config differs on target distro | High | High | Slice 1.4 detects + templates |
| Tkinter touch events flaky on Wayland | Medium | High | Document XWayland requirement; test early |
| Album art web API changes | Low | Medium | Graceful degradation; local-only works |
| SQLite corruption on power loss | Low | Medium | WAL mode + periodic vacuum |
| Pi Zero thermal throttling | Medium | Low | Profile memory/CPU; avoid heavy libs |
| Tkinter has no multi-touch or gesture support | Certain | Medium | Single-pointer gestures in ui/gestures.py (Slice 3.1a); docs promise only what is built; revisit Pygame/SDL only if dropping X11 |

---

## Definition of Done (Per Slice)

A slice is **done** when:
1. ✅ All deliverables implemented
2. ✅ Test plan passes on target hardware (Pi Zero 2W)
3. ✅ No regressions in previous slices (run Phase 1 integration test)
4. ✅ Code committed with clear message
5. ✅ `config.json` updated if new settings added
6. ✅ Memory usage verified (< target for that phase)

---

## Memory Budget Tracking

| Phase | Target Max RAM | Notes |
|-------|----------------|-------|
| Phase 1 (Core) | 30 MB | MPD ~15MB, Python ~15MB |
| Phase 2 (Stats) | 35 MB | +SQLite cache |
| Phase 3 (Recs) | 40 MB | +affinity matrix in memory |
| Phase 4 (Remote) | 45 MB | +HTTP server |
| Phase 5 (Polish) | 50 MB | +voice/battery libs |

**Hard limit:** 64 MB (leave room for OS + MPD buffer)