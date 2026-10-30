# Low-Resource Linux Music Player: Project Plan

## Project Vision

A **modular, low-resource music player** for Linux systems — from Raspberry Pi Zero 2 W to desktops to servers. Built with Python 3 + Tkinter + a **plugin architecture** that lets anyone add audio backends, UI widgets, features, and integrations without modifying core code.

## Architecture Overview

```
┌────────────────────────────────────────────────────────┐
│                   Network Storage (NAS)                │
│                 (Mounted via SMB/NFS)                  │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│                 Linux System (any distro)               │
│                                                        │
│  ┌──────────────────────────────────────────────────┐  │
│  │ MPD Daemon (Background audio engine for FLAC)    │  │
│  └────────────────────────┬─────────────────────────┘  │
│                           │ Local Socket               │
│  ┌────────────────────────▼─────────────────────────┐  │
│  │ Python 3 Application (Core Engine)               │  │
│  │  ├── Plugin Manager (discovers, loads plugins)   │  │
│  │  ├── Tkinter GUI (Low memory UI)                 │  │
│  │  ├── python-mpd2 (Control commands)              │  │
│  │  ├── Mutagen + Requests (Album art handler)      │  │
│  │  └── Plugins/ (Audio backends, features, UI)     │  │
│  └──────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────┘

```

---

## Technical Stack Selection

* **Audio & Network Engine:** **MPD (Music Player Daemon)**
* Reads FLAC files natively from the OS-level network mount with minimal CPU usage.
* Consumes under **15 MB RAM**.
* **Plugin-based:** Audio backends (ALSA, PipeWire, PulseAudio) loaded as plugins.

* **Python Controller Library:** `python-mpd2`
* Lightweight IPC bridge to communicate locally with MPD.

* **Metadata & Web Pipeline:** `mutagen` + `requests`
* Primary: Local embedded artwork extraction via `mutagen`.
* Fallback: External art fetching via HTTPS requests with strict timeouts.

* **Touchscreen Framework:** `Tkinter`
* Runs directly over standard X11 framebuffers without the heavy memory overhead of browser-based kiosks.

* **Plugin System:** Core engine + plugin architecture
* Plugins: audio backends, features, UI widgets, data sources, integrations.
* Plugin API: `MusicPlayerPlugin` base class, capability registry, event hooks.



---

## Project Directory Structure

```text
pi-music-player/
│
├── main.py                # Application entry point (initializes UI and thread loops)
├── requirements.txt       # Dependencies (python-mpd2, mutagen, requests)
├── config.json            # Configuration settings (timeouts, cache paths)
│
├── core/
│   ├── __init__.py
│   ├── player.py          # MPD client wrapper (playback controls, status)
│   └── artwork.py         # Embedded art extraction and web service fallback
│
└── ui/
    ├── __init__.py
    ├── dashboard.py       # Tkinter touchscreen interface and touch handlers
    └── styles.py          # Themes, fonts, and touch-target sizing

```

---

## Core Code Implementation

### 1. MPD Backend Client (`core/player.py`)

```python
from mpd import MPDClient

class MusicPlayer:
    def __init__(self, host="localhost", port=6600):
        self.client = MPDClient()
        self.host = host
        self.port = port
        self.connect()

    def connect(self):
        try:
            self.client.connect(self.host, self.port)
        except Exception as e:
            print(f"MPD Connection Error: {e}")

    def get_current_song(self):
        try:
            return self.client.currentsong()
        except Exception:
            self.connect()
            return self.client.currentsong()

    def toggle_play(self):
        status = self.client.status()
        if status.get("state") == "play":
            self.client.pause(1)
        else:
            self.client.play()

```

### 2. Album Art Handler (`core/artwork.py`)

```python
import requests
from mutagen.flac import FLAC

def get_album_art(file_path, save_cache_path="/tmp/cover.jpg"):
    """Extracts embedded FLAC art; falls back to HTTPS web service."""
    try:
        # 1. Try extracting embedded art locally using Mutagen
        audio = FLAC(file_path)
        if audio.pictures:
            with open(save_cache_path, "wb") as img_file:
                img_file.write(audio.pictures[0].data)
            return save_cache_path
    except Exception as e:
        print(f"Local art extraction failed: {e}")

    # 2. Fallback: Query web service with explicit timeouts and headers
    try:
        headers = {"User-Agent": "PiMusicPlayer/1.0 (secure-diy-project)"}
        response = requests.get("https://coverartarchive.org/release/MBID-HERE", headers=headers, timeout=3.5)
        if response.status_code == 200:
            data = response.json()
            image_url = data['images'][0]['thumbnails']['small']
            img_data = requests.get(image_url, timeout=3.5).get_content()
            with open(save_cache_path, "wb") as f:
                f.write(img_data)
            return save_cache_path
    except requests.exceptions.RequestException as e:
        print(f"Web art fetch failed safely: {e}")
    
    return None

```

---

## Security & System Hardening Guidelines

1. **Storage Credentials Security:**
* Never store network share credentials in the Python application or repository.
* Mount network shares at boot via `/etc/fstab` using a root-owned credentials file (`/etc/samba/credentials` set to permissions `chmod 600`).


2. **Privilege Separation:**
* Execute both MPD and the Python process under a dedicated unprivileged system user account (e.g., `player`), avoiding `root` execution entirely.


3. **Network & Thread Safety:**
* Impose strict network timeouts (`timeout=3.5`) on all HTTP requests to prevent background thread lockups during network interruptions.
* Offload web API queries and artwork loading to Python background threads to keep the UI main loop responsive.

---

## Enhanced Compatibility Goal

**Target:** Make this project work seamlessly on any mainstream Linux distribution while maintaining <15 MB RAM footprint.

### Cross-Distro Support Requirements

| Component | Approach |
|-----------|----------|
| **Audio Backend Detection** | Detect ALSA/ PipeWire/ PulseAudio at runtime; auto-select `mpd.conf` template |
| **Display Server** | Document XWayland requirement; add Wayland-native fallback using pipewire widgets |
| **Distribution Setup** | Provide package-lists and setup scripts for: Debian, Ubuntu, Fedora, Arch, Alpine, NixOS |
| **Installation Modes** | Support: native install, Docker (ARM64), NixOS declarative config |
| **Hardware Abstraction** | Detect touchscreen type (resistive/capacitive/forced) and adjust touch calibration |

### New Directory Structure

```text
pi-music-player/
├── main.py                           # Application entry point
├── requirements.txt                    # Core dependencies
├── config.json                         # Configuration (timeouts, cache, detected backend)
│
├── configs/                           # Distribution-specific configs
│   ├── mpd.conf.alsa                 # ALSA audio backend
│   ├── mpd.conf.pipewire             # PipeWire audio backend  
│   ├── mpd.conf.pulse                # PulseAudio backend
│   └── mpd.conf.null                 # Null backend (headless/testing)
│
├── scripts/                           # Cross-distro setup scripts
│   ├── install-debian-ubuntu.sh      # apt-based
│   ├── install-fedora.sh             # dnf-based
│   ├── install-arch.sh               # pacman-based
│   ├── install-alpine.sh             # apk-based
│   └── docker-setup.sh               # Docker ARM64 build
│
├── plugins/                            # Optional feature extensions
│   ├── recommendations.py            # Play stats & music suggestions
│   └── remote.py                     # Web/remote control API
│
├── core/
│   ├── __init__.py
│   ├── player.py                     # MPD client wrapper (enhanced error handling)
│   ├── artwork.py                      # Album art handler
│   ├── system.py                     # Distro/hardware detection
│   └── cache.py                      # Enhanced cache manager with LRU eviction
│
└── ui/
    ├── __init__.py
    ├── dashboard.py                  # Tkinter touch interface
    ├── widget.py                     # Reusable UI components (play button, progress bar)
    └── styles.py                     # Theme & font configuration
```

---

## Additional Feature Roadmap

### Phase 1: Core Stability (Required)
- [x] MPD backend with reconnect logic
- [x] Album art extraction + web fallback with MBID resolution
- [ ] Cross-distro setup scripts  
- [ ] Runtime detection of audio backend/display server

### Phase 2: Play Statistics (Recommended)
- **Usage tracking:**
  - Total playtime per artist/album/track
  - Skip rate (how often tracks are skipped vs completed)
  - Replay count with timestamps
- **SQLite storage:** Lightweight `play_stats.db` (<1MB for years of data)
- **Privacy-safe:** All data stored locally, no telemetry

### Phase 3: Music Recommendations
- **Collaborative filtering-lite:**
  - "Fans also played" style suggestions based on similar playlists
  - Artist similarity via Last.fm API (optional web fetch)
  - Genre-based "radio" mode (shuffle within same genre)
- **Discovery features:**
  - "Play similar" button
  - "Recently added" queue
  - "Highly rated" auto-queue (for when user rates tracks)
- **Algorithm approach:** Simple co-occurrence counting (artist/genre pairs) + genre expansion

### Phase 4: Remote Control & Multi-Screen
- **Local web UI on `localhost:8080`:**
  - Full remote control from phone/tablet
  - Album art gallery view
  - Queue modification
- **Bluetooth remote support:** Control via any Bluetooth HID device
- **Multi-room queue sharing:** Export queue as M3U for other devices

### Phase 5: Niche Enhancement Features
- **Sleep timer** with fade-out
- **Voice assistant bridge** (simple keyword wake-word for "play", "pause", "next")
- **Car mode:** Simplified UI for driving (bigger touch targets, minimized swipes)
- **Battery indicator API:** For portable Pi setups (detect via sysfs)

---

## Additional Technical Goals

### Dependency Footprint Optimization
- **Frozen Python executable** (`pyinstaller --onefile` or `Nuitka`) for zero-dependency deployment
- **Optional imports:** `import mpd` wrapped in `try/except` to warn if MPD not running
- **Lazy loading:** Album art and metadata loaded only when displayed

### Testing & Validation
- **CI matrix:** Test on multiple distros using QEMU/GitHub Actions
  - Debian Bookworm, Ubuntu 24.04, Fedora 40, Arch latest, Alpine latest
- **Memory profiling:** Add `memory-profiler` to CI to catch regressions
- **MPD connection resilience tests:** Simulate network drops

### Documentation Improvements
- **Quickstart guide:** "From fresh Pi Zero to playing music" (under 10 minutes)
- **Troubleshooting page:** Common audio backend issues, touchscreen calibration
- **Developer guide:** How to add new UI widgets, how to extend artwork fetchers

---

## Updated Technical Stack Selection

| Layer | Technology | Notes |
|-------|------------|-------|
| **Audio Engine** | MPD | With auto-configured audio backend |
| **IPC** | python-mpd2 | Timeout-aware, reconnect logic |
| **Metadata** | mutagen | FLAC/AAC/MP3 support |
| **Web Assets** | requests + Cover Art Archive | MBID-resolved |
| **Cache** | Disk cache with LRU | Max size configurable |
| **Stats DB** | SQLite | Co-occurring with cache |
| **GUI** | Tkinter | XWayland compatible |
| **Background Tasks** | threading + queue | Never blocks main loop |
| **Deployment** | pyinstaller or system packages | Distro-specific packaging |