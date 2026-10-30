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
│   ├── pi-zero-setup.md              # Complete Pi Zero 2W walkthrough
│   ├── cross-distro.md              # Debian, Fedora, Arch, Alpine, NixOS
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
│   ├── play-statistics.md            # How stats work, schema reference
│   ├── recommendations.md            # Algorithm explanation
│   └── remote-control.md            # Web API + web dashboard docs
├── troubleshooting/
│   ├── README.md                     # Common issues
│   ├── audio-backend.md              # ALSA/PipeWire/Pulse issues
│   ├── network-mounts.md             # SMB/NFS mount failures
│   └── touch-screen.md               # Calibration, driver issues
├── development/
│   ├── README.md                     # Contributor guide
│   ├── slice-plan.md                 # This document
│   ├── testing.md                    # How to run tests
│   └── release-process.md           # PyInstaller builds, GitHub release workflow
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

### Plugin Phases Overview

| Phase | Slice | What's Added |
|-------|-------|-------------|
| **P1** | 1.5 | Plugin system foundation — base class, PluginManager, core hooks |
| **P2** | 2.1 | First built-in plugins: ALSA audio backend, Statistics |
| **P3** | 3.1 | Plugin ecosystem: recommendations, remote control, more |
| **P4** | 4.1 | Plugin marketplace system — discovery, loading, configuration |
| **P5** | 5.x | Community plugins — sleep timer, equalizer, etc. |

### Plugin Phase Details

#### P1: Plugin System Foundation (Slice 1.5)
- MusicPlayerPlugin base class
- PluginManager discovery and loading
- Core event hooks (`on_song_change`, `on_playback_state`, etc.)
- Plugin manifest system (`config.json`)
- Plugin lifecycle (initialize, shutdown, get_capabilities)

**Deliverables:**
- `plugins/__init__.py` — PluginManager class
- `core/plugin_base.py` — MusicPlayerPlugin abstract base
- Minimal built-in plugin for testing

#### P2: Built-in Plugins (Slices 2.1-2.3)
- ALSA audio backend plugin
- Statistics feature plugin
- Remote control feature plugin
- Configuration system integration

**Deliverables:**
- `plugins/audio-backends/alsa/alsa.py` — ALSA audio backend
- `core/stats.py` — Play statistics module
- Plugin settings integration

#### P3: Plugin Ecosystem (Slices 3.1-3.3)
- Recommendations plugin
- Remote control web API plugin
- Equalizer plugin (basic)
- Plugin metadata browsing

**Deliverables:**
- `plugins/features/recommendations.py` — Co-occurrence model
- `plugins/remote.py` — Web API on localhost:8080
- `plugins/features/equalizer.py` — Basic equalizer

#### P4: Plugin Marketplace (Slice 4.1)
- Plugin discovery system
- Plugin loading/unloading at runtime
- Plugin configuration persistence
- Plugin lifecycle management

**Deliverables:**
- Runtime plugin loader
- Plugin settings persistence in config.json
- Plugin enable/disable from UI

#### P5: Community Plugins (Slices 5.x)
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

## GitHub Documentation Structure

```
docs/
├── README.md                         # Project overview, quickstart
├── installation/
│   ├── README.md                     # Installation overview
│   ├── pi-zero-setup.md              # Complete Pi Zero 2W walkthrough
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

## Slice Template (Updated — Now Includes Docs)

Copy this for each slice:

```markdown
## Slice X.Y: [Name]

**Target Date:** YYYY-MM-DD
**Estimated Effort:** N days

### Code Deliverables
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

## Phase 1: Core Player (Foundation)

---

## Phase 1: Core Player (Foundation)

### Slice 1.1: MPD Connection & Basic Controls
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

---

### Slice 1.2: Album Art — Local Extraction Only
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

### Slice 1.3: Album Art — Web Fallback with MBID Resolution
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

---

### Slice 1.4: System Detection & Config Management
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

#### Test Criteria
```bash
# Run on target hardware (Pi Zero) and optionally in VMs
python3 -c "
from core.system import SystemDetector
d = SystemDetector()
print('Audio backend:', d.detect_audio_backend())
print('Display server:', d.detect_display_server())
print('Distro:', d.detect_distro())
print('MPD template:', d.get_mpd_config_template())
"
```

**Pass if:** Correctly identifies backend on Pi OS (ALSA), Fedora (PipeWire), Ubuntu (PipeWire); generates valid MPD config that MPD accepts.

---

### Slice 1.5: Tkinter Touch UI — Core Dashboard
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

## Phase 2: Play Statistics

### Slice 2.1: Database Schema & Event Capture
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
  - Background thread flushes every 10s (survives power loss)

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

### Slice 2.2: Statistics UI & Insights
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
**Goal:** Local-only "fans also played" suggestions

#### Deliverables
- `plugins/recommendations.py` — `RecommendationEngine` class:
  - **Co-occurrence model:** For each artist, which other artists appear in same listening sessions?
  - Session = continuous playback with < 5 min gaps
  - Build artist→artist affinity matrix (SQLite table)
  - `get_similar_artists(artist, limit=10)` → ranked list
  - `get_recommendations_for_current()` → based on current track's artist
  - `get_genre_radio(genre)` → shuffle tracks from same genre
- Runs in background, updates model nightly or on demand

#### Test Criteria
```bash
python3 -c "
from core.stats import PlayStats
from plugins.recommendations import RecommendationEngine
stats = PlayStats('play_stats.db')
engine = RecommendationEngine(stats)
# After some listening history exists
print('Similar to Radiohead:', engine.get_similar_artists('Radiohead'))
print('Recommendations now:', engine.get_recommendations_for_current())
"
```

**Pass if:** Returns plausible suggestions after ~50 plays; runs in < 200ms on Pi Zero; no network calls.

---

### Slice 3.2: Discovery Features in UI
**Goal:** Surface recommendations in the dashboard

#### Deliverables
- New "Discover" screen:
  - **"Play Similar"** button on Now Playing → queues similar tracks
  - **"Genre Radio"** — pick genre, plays endless shuffle
  - **"Revisit"** — albums you haven't played in 30+ days
  - **"New to You"** — artists in library but never played (via MPD `list albumartist`)
- "Add to Queue" / "Play Next" actions

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
- Night mode (red tint) after sunset

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

## Slice Tracking Template (Docs-Heavy)

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
| 9 | 3.1 | Recommendations need stats |
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