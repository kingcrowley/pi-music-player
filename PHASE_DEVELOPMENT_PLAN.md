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

## Phase 1: Core Player (Foundation) ✅ Complete

### Slice 1.1: MPD Connection & Basic Controls ✅ Merged (PR #1)
**Goal:** Reliable MPD communication with automatic reconnection

**Merged commits:** `80adff5` feat(slice-2.1): Play Statistics Database Schema & Event Capture (rebased on main (#7)), `e8cf7a8` feat(slice-1.5): Tkinter Touch UI & Plugin System Foundation (#8), `2146ee4` Slice 1.4: System Detection & Config Management (#5), `415d248` feat(artwork): Album art extraction with LRU cache (#2), `6941474` docs: Correct Raspberry Pi setup guide

**Deliverables completed:**
- `core/player.py` — `MusicPlayer` class with `connect()` with exponential backoff, `get_current_song()`, `play()`, `pause()`, `toggle_play()`, `next()`, `previous()`, `stop()`, `set_volume(0-100)`, `is_connected()`
- `configs/mpd.conf.alsa`, `.pipewire`, `.pulse`, `.null` templates
- `core/system.py` — `SystemDetector` class with `detect_audio_backend()`, `detect_display_server()`, `detect_distro()`, `get_mpd_config_template()`, `generate_mpd_conf()`
- Plugin system: `plugins/__init__.py`, `core/plugin_base.py`
- Tkinter touch dashboard: `ui/dashboard.py`, `ui/styles.py`, `ui/widget.py`

**Test criteria:** The automated test runner collects tests from test_slice_1_4.py, test_slice_1_5.py, and test_slice_2_1.py. test_slice_1_1.py is a manual check script and is not included in the automated count. All MPD calls wrapped in try/except, reconnect logic works, no exceptions propagate to Tkinter event loop.

### Slice 1.2: Album Art — Local Extraction Only ✅ Merged (PR #2)
**Goal:** Extract embedded artwork from FLAC/MP3 files, cache to disk

**Merged commits:** `415d248` feat(artwork): Album art extraction with LRU cache (#2), `66dd8d4` test(slide-2.2): Add comprehensive slice 2.2 test suite

**Deliverables completed:**
- `core/artwork.py` — `ArtworkCache` class with `get_art(file_path)` → returns cached image path or `None`, LRU cache with configurable max size (default 50MB), thread-safe with `queue.Queue` + background worker, extracts from FLAC, MP3, M4A

**Test criteria:** Returns valid image paths for files with embedded art; returns `None` for files without; cache directory stays under size limit.

### Slice 1.3: Album Art — Web Fallback with MBID Resolution ✅ Merged (PR #3)
**Goal:** Fetch cover art from Cover Art Archive when no embedded art exists

**Merged commits:** `4b8cc7d` fix(artwork): Address remaining CodeRabbit review comments, `ac8b87b` docs: fix second pi-zero-setup reference in PHASE_DEVELOPMENT_PLAN.md

**Deliverables completed:**
- Enhanced `ArtworkCache.get_art()` with fallback chain: 1. Embedded art, 2. Local sidecar (`cover.jpg` / `folder.jpg`), 3. Cover Art Archive via MusicBrainz Release ID (MBID) — extract MBID from file tags, query `https://coverartarchive.org/release/{MBID}`, download `thumbnails.small` image
- All network calls: `timeout=3.5`, custom User-Agent, retry once

**Test criteria:** Successfully fetches and caches web art for MBID-tagged files without embedded art; fails gracefully (returns `None`, no exception) for untagged files or network errors.

### Slice 1.4: System Detection & Config Management ✅ Merged (PR #4)
**Goal:** Auto-detect runtime environment; generate appropriate MPD config

**Merged commits:** `2361bfd` docs: update installation guide to general Raspberry Pi walkthrough, `5a9dcf9` docs: update README references to new raspberry-pi-setup.md

**Deliverables completed:**
- `core/system.py` — `SystemDetector` class
- `configs/mpd.conf.alsa`, `.pipewire`, `.pulse`, `.null` templates
- `core/config.py` — `Config` class with schema, detected values + user overrides, load/save to `config.json`
- `system.py` detects audio backend, display server, distro; generates valid MPD config

**Test criteria:** Correctly identifies backend on Pi OS Bookworm (ALSA or PipeWire), Fedora (PipeWire), Ubuntu (PipeWire); generates valid MPD config that MPD accepts; handles Wayland vs X11 detection.

### Slice 1.5: Tkinter Touch UI — Core Dashboard ✅ Merged (PR #8)
**Goal:** Minimal touchscreen interface that controls playback

**Merged commits:** `5d57add` fix: address remaining review gaps - idle cleanup, quit test, export CSV, reset flag persistence, `8d9b4e7` fix: address remaining review gaps, `a07ea0e` fix(stats): check save() return value in reset-flag restore branch

**Deliverables completed:**
- `ui/styles.py` — Touch-friendly theme (48px minimum touch targets, high contrast)
- `ui/widget.py` — Reusable components: `TouchButton`, `ProgressBar`, `AlbumArtLabel`, `VolumeSlider`, `StatusLabel`
- `ui/dashboard.py` — Main window with album art, track info, playback controls, volume slider, progress bar, status indicator
- Background thread polls MPD every 1s, updates UI via `root.after()`
- Plugin system integration and loading

**Test criteria:** 98 unit tests pass across all test files. Tests cover: MPD connection/resilience, system detection, plugin lifecycle, dashboard `_update_ui` state machine (song start/stop/seek/repeat-one/track change/quitting mid-track/cleanup not called on idle polls), PlayStats SQLite operations (record/queries/retention/CSV export), skip rates, listening time heatmaps, top tracks, recent history.

**Integration test:** Full smoke test — music plays, UI responds, art shows, volume works; survives MPD restart; survives network mount temporary disconnect.

---

## Phase 2: Play Statistics ✅ Complete

### Slice 2.1: Database Schema & Event Capture ✅ Merged (PR #6)
**Goal:** Persistent local database tracking every play event

**Merged commits:** `c2b8ee5` fix: Apply timestamp and fallback fixes, `35bf482` fix(slide-2.2): Bind drag handlers on every stats label, add missing sections, fix retention, `6eacddb` feature(slide-2.2): Stats UI screen + query methods, `3af277d` ui: Add Slice 2.2 Statistics Screen, `9239269` stats: Add Slice 2.2 query methods (playcounts, skip rate, heatmap, history, CSV export)

**Deliverables completed:**
- `core/stats.py` — `PlayStats` class with SQLite backend
- Schema: `plays` table with `track_path`, `artist`, `album`, `title`, `started_at`, `ended_at`, `completed`, `skipped`, `duration_ms`; indexes on `artist`, `album`, `started_at`
- `record_play_start(track_info)` — called on track change
- `record_play_end(completed: bool)` — called on track end/skip
- Background thread flushes every 10s (survives power loss)
- Query methods: `get_total_plays()`, `get_artist_stats()`, `get_recent_plays()`, `get_artist_playcounts()`, `get_album_playcounts()`, `get_skip_rate()`, `get_listening_time_heatmap()`, `get_recent_history(limit=20)`, `export_csv()`

**Test criteria:** Records survive process restart; queries return correct aggregates; database < 1KB per 100 plays.

### Slice 2.2: Statistics UI & Insights ✅ Merged (PR #9)
**Goal:** Visualize play history in the dashboard

**Merged commits:** `8e16bdd` test(slide-2.2): add missing quit-mid-track and idle-cleanup tests, `5d57add` fix: address remaining review gaps - idle cleanup, quit test, export CSV, reset flag persistence, `a07ea0e` fix(stats): check save() return value in reset-flag restore branch

**Deliverables completed:**
- New "Stats" screen in dashboard (swipe or button to access)
- Top Artists (by play count, playtime)
- Top Albums
- Most Played Tracks
- Skip Rate per artist/album (skips / total plays)
- Listening Time by hour of day / day of week (heatmap)
- Recent History (last 20 plays with timestamps)
- Export to CSV button (for personal analysis)

**Test criteria:** 32 unit tests pass (test_slice_2_2.py). All stats views populate correctly; export creates valid CSV; retention cleanup only closes old open rows and prunes by size (not age).

**Integration test:** Play 20+ tracks naturally (mix of complete, skip, restart); check Stats screen — verify all numbers plausible; restart app — verify stats persist; check DB size: `ls -lh play_stats.db` should be < 100KB.

---

## Phase 3: Music Recommendations

### Slice 3.1: Recommendation Engine Core
**Goal:** Local-only "fans also played" suggestions — the first real plugin, exercising `PluginManager` end-to-end.

**Target Date:** 2026-12-15
**Estimated Effort:** 10 days

### Code Deliverables

- [ ] `plugins/features/recommendations/config.json` — Manifest for the first built-in plugin (`plugin_id: "recommendations"`, `type: "feature"`, capabilities: `["recommendations"]`, `auto_load: true`). Registers a co-occurrence model and hook handlers.
- [ ] `plugins/features/recommendations/recommendations.py` — `RecommendationEngine` class extending `MusicPlayerPlugin`.
- [ ] Co-occurrence SQLite schema (in `play_stats.db` or alongside it):
  ```sql
  CREATE TABLE IF NOT EXISTS cooccurrence (
      artist_a TEXT NOT NULL,
      artist_b TEXT NOT NULL,
      play_count INTEGER DEFAULT 1,
      PRIMARY KEY (artist_a, artist_b)
  );
  CREATE INDEX IF NOT EXISTS idx_cooc_a ON cooccurrence(artist_a);

  CREATE TABLE IF NOT EXISTS genres (
      genre TEXT PRIMARY KEY,
      artists TEXT  -- comma-separated artist names
  );

  CREATE TABLE IF NOT EXISTS album_songs (
      album TEXT,
      artist TEXT,
      path TEXT,
      genre TEXT,
      PRIMARY KEY (path)
  );
  ```
- [ ] `record_session_pair(prev_track, curr_track)` — called after `record_play_end(completed=True)` fires the `on_playback_complete` hook.
- [ ] `get_similar_artists(artist, limit=10)` — ranks co-occurring artists by `play_count DESC`.
- [ ] `get_recommendations_for_current()` — uses the current track's `artist` field.
- [ ] `get_genre_radio(genre)` — shuffles all tracks tagged with the given genre.
- [ ] `get_revisit_candidates(days=30)` — albums not played in the last N days.
- [ ] `get_new_to_you()` — artists present in MPD `list albumartist` but absent from `play_stats.db`.
- [ ] Hook registration in `initialize()`:
  - `on_song_change` → record current track info
  - `on_playback_complete` → call `record_session_pair` with previous track
  - `shutdown()` → clean up in-memory session state
- [ ] `build_from_history()` — rebuild the co-occurrence matrix from existing `plays` rows in `play_stats.db` (used on first run and for nightly rebuilds).
- [ ] Nightly rebuild stub (cron or `scheduler.register()` in `initialize()`) — runs `build_from_history()` + `VACUUM`.

### Documentation Deliverables

- [ ] Update `docs/features/recommendations.md` — add config defaults, test plan section, performance notes for Pi Zero 2 W
- [ ] Create `docs/development/plugin-api.md` section for `RecommendationEngine` (API reference already sketched in recommendations.md — expand it)
- [ ] Update `README.md` — mark Phase 3 as in progress, add `recommendations` to feature table
- [ ] Update `docs/development/testing.md` — add `test_slice_3_1.py` to test layout table

### Test Plan

```bash
# Run the new slice tests
python -m unittest tests.test_slice_3_1 -v

# Run full suite (should be green)
python -m unittest discover -s tests -p "test_*.py"

# Verify plugin loads and unloads cleanly via PluginManager
python3 -c "
import sys; sys.path.insert(0, '.')
from plugins import PluginManager
mgr = PluginManager(plugin_dir='plugins')
count = mgr.load_plugins()
print(f'Loaded {count} plugin(s)')
for p in mgr.get_all_plugins():
    print(f'  - {p.name} v{p.version}')
    print(f'    capabilities: {p.get_capabilities()}')
    print(f'    hooks: {mgr.get_registered_hooks()}')
mgr.shutdown_all()
print(f'After shutdown: {mgr.get_registered_hooks()}')
"
```

### Acceptance Criteria

- [ ] Plugin loads without error via `PluginManager.load_plugins()`
- [ ] `get_similar_artists('Radiohead')` returns ranked list after ≥50 plays recorded
- [ ] `get_genre_radio('Blues')` returns shuffled track list (empty list is valid if no genre tags)
- [ ] `get_revisit_candidates(days=30)` returns albums older than 30 days, excluding recent plays
- [ ] `get_new_to_you()` returns artists in MPD library not yet in `play_stats.db`
- [ ] No network calls made (verified by static analysis / no `requests` / `urllib` imports)
- [ ] Hook callbacks fire on `on_song_change` and `on_playback_complete` (plugin is enabled and receives events)
- [ ] `shutdown()` cleans up session state; `unload_plugin('recommendations')` returns `True`
- [ ] `trigger_hook` dispatches callbacks correctly after plugin load (exercises the `register_hook`→`trigger_hook` path end-to-end)
- [ ] All existing tests continue to pass

### Dependencies

- Requires: Slice 2.1 complete (play_stats.db schema), Slice 2.3 complete (plugin hardening, `trigger_hook` correctness)
- Blocks: Slice 3.2 (Discovery UI needs the engine to render recommendations)

### Notes / Risks

- **Risk:** `register_hook` / `trigger_hook` dispatch gap (deferred issue #1) — public `PluginManager.register_hook()` adds to `self.hooks` but `trigger_hook` only reads `_plugin_hooks`. Mitigation: this slice exercises the path via the plugin's `register_hook` → `PluginManager.trigger_hook` chain, surfacing any remaining dispatch bug. If found, fix `trigger_hook` to also walk `self.hooks` (small, safe change).
- **Risk:** `play_stats.db` and recommendation tables live in the same file — concurrent writes between `PlayStats.save()` and recommendation queries. Mitigation: use SQLite WAL mode (already enabled in `PlayStats.__init__`); add explicit `BEGIN`/`COMMIT` in `record_session_pair`.
- **Risk:** Co-occurrence matrix grows large with many artists. Mitigation: index on `(artist_a, artist_b)`; `build_from_history()` runs in batches.
- **Risk:** Pi Zero 2 W performance for `get_similar_artists` with 1000+ artists. Mitigation: limit query to top-N by `play_count` with `LIMIT`; benchmark in test.
- **Deferred:** Genre tagging requires genre data from mutagen (reads file tags) — can be a follow-up within this slice if time allows; if not, `get_genre_radio` returns empty and is marked "TODO: genre extraction" in the code.

### Slice 3.2: Discovery Features in UI
**Goal:** Surface recommendations in the dashboard

**Planned deliverables:**
- New "Discover" screen
- **"Play Similar"** button on Now Playing → queues similar tracks
- **"Genre Radio"** — pick genre, plays endless shuffle
- **"Revisit"** — albums you haven't played in 30+ days
- **"New to You"** — artists in library but never played (via MPD `list albumartist`)
- "Add to Queue" / "Play Next" actions

**Test criteria:** All features work; queue manipulation doesn't break playback.

---

## Phase 4: Remote Control

### Slice 4.1: Local Web API
**Goal:** REST API for remote control

**Planned deliverables:**
- `plugins/remote.py` — `RemoteServer` (runs on `localhost:8080`)
- Endpoints: `GET /api/status`, `GET /api/queue`, `POST /api/control`, `GET /api/art`, `GET /api/library`, `POST /api/queue/add`
- Token auth (random token on startup, printed to console + QR code)
- CORS enabled for LAN access

**Test criteria:** All endpoints respond < 100ms; controls actually affect playback; token required.

### Slice 4.2: Web Dashboard (Optional)
**Goal:** Phone-friendly web UI

**Planned deliverables:**
- Static HTML/JS served from `/web/` directory
- Now playing with album art
- Playback controls
- Queue view with drag-to-reorder
- Library browser
- Volume slider
- Works on mobile Safari/Chrome without app install

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