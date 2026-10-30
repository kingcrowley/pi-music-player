# Dashboard UI Reference

Complete guide to the touchscreen dashboard interface.

> **Target:** Raspberry Pi Zero 2 W with touchscreen (capacitive/resistive)
> **Resolution:** 480x320 or 800x480 (auto-scales)

---

## Main Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│  [Album Art - Large Center]                                 │
│                                                             │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Track Title                                         │   │
│  │ Artist Name • Album Name                            │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ ████████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░   │   │
│  │ 2:45 / 5:32                                           │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────┐  ┌─────┐  ┌─────┐  ┌─────┐  ┌─────┐              │
│  │ ⏮   │  │ ⏸   │  │ ⏹   │  │ ⏭   │  │ 🔊   │              │
│  │ Prev │  │Play/Pause│ Stop│ Next │  │Vol  │              │
│  └─────┘  └─────┘  └─────┘  └─────┘  └─────┘              │
└─────────────────────────────────────────────────────────────┘
```

---

## Touch Controls

| Control | Action |
|---------|--------|
| **Album Art (tap)** | Show album info / art gallery |
| **Progress bar (tap)** | Seek to position |
| **Play/Pause (tap)** | Toggle playback |
| **Next (tap)** | Next track |
| **Previous (tap)** | Previous track |
| **Stop (tap)** | Stop playback |
| **Volume (drag)** | Adjust volume (0-100%) |
| **Swipe left** | Next screen (Stats / Discover / Settings) |
| **Swipe right** | Previous screen |

---

## Button Details

### Play/Pause Button
- **States:** ▶ (play), ⏸ (pause), ◐ (buffering), ✗ (error)
- **Long press:** Show current queue

### Volume Control
- **Range:** 0-100%
- **Default:** 50%
- **Drag horizontally** to adjust
- **Tap** to mute/unmute

### Progress Bar
- **Shows:** Current position / total duration
- **Tap anywhere** to seek
- **Drag** for fine control

---

## Secondary Screens

Swipe left/right to navigate between screens:

### 1. Now Playing (Default)
Main playback controls

### 2. Statistics
- **Top Artists** (by play count)
- **Top Albums**
- **Most Played Tracks**
- **Skip Rate** (skips / plays)
- **Listening Time** (heatmap by hour/day)
- **Recent History** (last 20 plays)
- **Export CSV** button

### 3. Discover
- **Play Similar** (co-occurrence recommendations)
- **Genre Radio** (shuffle by genre)
- **Revisit** (albums not played in 30+ days)
- **New to You** (artists in library, never played)

### 4. Settings
- **Audio Output** (ALSA/PipeWire/Pulse selection)
- **Display** (brightness, timeout)
- **Network** (NAS mount status)
- **Cache** (size, clear)
- **About** (version, license)

---

## Status Indicators

| Icon | Meaning |
|------|---------|
| 🟢 | Connected to MPD |
| 🔴 | MPD disconnected |
| 🎵 | Playing |
| ⏸ | Paused |
| ⏹ | Stopped |
| 🔊 | Volume level (4 bars) |
| 📶 | Network mount status |
| 🔋 | Battery (if portable) |

---

## Keyboard Shortcuts (for testing on desktop)

| Key | Action |
|-----|--------|
| `Space` | Play/Pause |
| `Right` | Next track |
| `Left` | Previous track |
| `Up` | Volume +5% |
| `Down` | Volume -5% |
| `s` | Stop |
| `q` | Quit |
| `1-4` | Switch screen (1=Now Playing, 2=Stats, 3=Discover, 4=Settings) |
| `f` | Toggle fullscreen |

---

## Accessibility

- **Minimum touch targets:** 48x48 px (WCAG AA)
- **High contrast mode:** Available in Settings
- **Color-blind safe:** No color-only state indicators
- **Keyboard navigation:** All functions accessible via keyboard
- **Screen reader:** Labels on all controls

---

## Memory Usage

Expected RAM on Pi Zero 2 W:
- Dashboard UI: ~15 MB
- Background threads: ~5 MB
- MPD daemon: ~15 MB
- **Total: ~35 MB** (leaves headroom for OS)

Check with:
```bash
python3 -c "
import resource
print(f'RSS: {resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024:.1f} MB')
"
```