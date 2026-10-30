# Slice 1.1: MPD Connection & Basic Controls

**Phase:** 1 (Core Player Foundation)
**Slice:** 1.1
**Branch:** `phase/1-slice1-mpd-connection`
**Commit:** `5e46253`

---

## Overview

Implements a reliable MPD (Music Player Daemon) client wrapper with automatic reconnection logic. This is the foundation for all subsequent slices — every playback control, status query, and playlist operation goes through this module.

---

## Files Added

| File | Purpose |
|------|---------|
| `core/player.py` | `MusicPlayer` class — MPD client wrapper with reconnection |
| `tests/test_slice_1_1.py` | Automated acceptance test suite |
| `main.py` | Minimal bootstrap for manual testing |
| `requirements.txt` | Python dependencies (python-mpd2, mutagen, requests) |

---

## Core API: `core.player.MusicPlayer`

### Connection Management

```python
player = MusicPlayer(host="localhost", port=6600, timeout=5.0)
```

| Method | Description |
|--------|-------------|
| `connect()` → `bool` | Connect with exponential backoff (1s, 2s, 4s... max 30s, 10 retries) |
| `is_connected()` → `bool` | Check if connected (pings MPD) |
| `_ensure_connected()` → `bool` | Internal: reconnect if needed |

### Playback Control

| Method | Description |
|--------|-------------|
| `play()` → `bool` | Start/resume playback |
| `pause()` → `bool` | Pause playback |
| `toggle_play()` → `bool` | Toggle between play/pause |
| `stop()` → `bool` | Stop playback |
| `next()` → `bool` | Next track in queue |
| `previous()` → `bool` | Previous track in queue |
| `set_volume(level: int)` → `bool` | Set volume 0-100 (clamped) |
| `seek(position: float)` → `bool` | Seek to position in seconds |

### Status Queries

| Method | Returns |
|--------|---------|
| `get_status()` → `dict` | `{state, volume, elapsed, duration}` |
| `get_current_song()` → `dict` | `{artist, title, album, file, time, track, genre, date}` |
| `get_playlist()` → `list[dict]` | Current playlist songs |

### Playlist Management

| Method | Description |
|--------|-------------|
| `add_to_playlist(path: str)` → `bool` | Add track/dir to queue |
| `clear_playlist()` → `bool` | Clear queue |

---

## Key Design Decisions

### 1. No Exceptions to UI

All MPD calls wrapped in `_execute_with_retry()`:
- Catches any exception
- Attempts one reconnect
- Retries command once
- Returns `None` on total failure
- **Never** propagates exception to caller

### 2. Exponential Backoff

```python
MAX_RETRIES = 10
BASE_DELAY = 1.0      # seconds
MAX_DELAY = 30.0      # seconds
```

Retry sequence: 1s → 2s → 4s → 8s → 16s → 30s → 30s...

### 3. Safe Defaults

```python
# get_status() on failure returns:
{
    "state": "unknown",
    "volume": "0",
    "elapsed": "0",
    "duration": "0",
}

# get_current_song() on failure returns:
{}
```

---

## Acceptance Criteria

Run on Raspberry Pi with MPD:

```bash
python3 tests/test_slice_1_1.py
```

### Tests

| Test | Pass Criteria |
|------|---------------|
| Connection succeeds | `connect()` returns `True` |
| `is_connected()` reflects state | Returns `True` after connect |
| `get_status()` returns valid dict | Has `state`, `volume` keys |
| `get_current_song()` returns dict | Returns dict (may be empty) |
| `toggle_play()` changes state | State changes or no exception |
| `next()` executes | No exception thrown |
| `set_volume(75)` applies | Volume reads back as "75" |
| No uncaught exceptions | All operations wrapped |

---

## Manual Test

```bash
# On Pi with MPD running
python3 main.py
```

Expected interaction:
```
==================================================
Low-Resource Linux Music Player
Slice 1.1: MPD Connection & Basic Controls
==================================================

Connection status: True

Current status: {'state': 'stop', 'volume': '50', 'elapsed': '0', 'duration': '0'}
Current song: {}

Press Enter to toggle play...
Status after toggle: play

Press Enter to go to next track...
Next song: {'artist': 'Pink Floyd', 'title': 'Comfortably Numb', ...}

Volume set to: 50

Press Enter to stop playback...
Final status: {'state': 'stop', 'volume': '50', 'elapsed': '0', 'duration': '0'}

✅ Slice 1.1 test complete!
```

---

## Prerequisites on Pi

```bash
# Install MPD + dependencies
sudo apt update
sudo apt install -y mpd python3-pip python3-tk cifs-utils nfs-common

# Create MPD user
sudo useradd -r -s /bin/false -d /var/lib/mpd player
sudo chown -R player:player /var/lib/mpd /var/lib/mpd/cache

# Start MPD
sudo systemctl enable mpd
sudo systemctl start mpd

# Verify
mpc status
mpc ping

# Install Python deps
pip3 install --break-system-packages python-mpd2 mutagen requests

# Add test music
mkdir -p /mnt/nas/music
cp /path/to/some.flac /mnt/nas/music/
```

---

## RAM Budget

| Component | Target |
|-----------|--------|
| MPD daemon | ~15 MB |
| Python app (this slice) | ~15 MB |
| **Total** | **~30 MB** |

Leaves headroom for OS on 512 MB Pi Zero 2 W.

---

## Next Slice

**Slice 1.4:** System Detection & Config Management
- Auto-detect audio backend (ALSA/PipeWire/PulseAudio)
- Generate appropriate `mpd.conf` template
- Runtime config via `config.json`

Branch: `phase/1-slice4-system-detection`