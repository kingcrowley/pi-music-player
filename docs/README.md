# Low-RAM Python Music Player - Start Here

## What Is This?

A low-RAM music player designed for embedded hardware — Raspberry Pi Zero 2 W and similar resource-constrained devices. Built with Python 3 + Tkinter GUI + MPD (Music Player Daemon) audio backend, playing FLAC and other formats from network-mounted storage (NAS via SMB/NFS).

| Property | Value |
|----------|-------|
| **Target hardware** | Raspberry Pi Zero 2 W (512 MB RAM) |
| **RAM target** | App under 50 MB, total system under 64 MB |
| **Audio engine** | MPD daemon (reads FLAC natively, ~15 MB RAM) |
| **GUI** | Tkinter touchscreen interface |
| **Audio library** | FLAC, MP3, M4A via mutagen |
| **Audio playback** | Local socket IPC to MPD (python-mpd2) |
| **Album art** | Mutagen local extraction → Cover Art Archive fallback |
| **Statistics** | SQLite play tracking (local, no telemetry) |
| **Recommendations** | Local co-occurrence model (artist/genre affinity) |
| **Remote control** | Local web API on `localhost:8080` (optional) |
| **License** | TBD — see LICENSE |

## Project Goals

1. **Play music reliably on a Pi Zero 2 W** — 512 MB RAM, headless or touchscreen
2. **Cross-distro support** — works on Debian, Ubuntu, Fedora, Arch, Alpine, NixOS
3. **Docs-first development** — every feature ships with documentation
4. **No external dependencies beyond pip** — pure Python + MPD
5. **Privacy-safe** — all play stats and recommendations stored locally, no telemetry

## Document Map

| Document | Purpose |
|----------|---------|
| [`docs/README.md`](README.md) | This file — project overview and orientation |
| [`docs/installation/pi-zero-setup.md`](installation/pi-zero-setup.md) | Complete Raspberry Pi Zero 2W walkthrough |
| [`docs/installation/cross-distro.md`](installation/cross-distro.md) | Installation on Debian, Ubuntu, Fedora, Arch, Alpine, NixOS |
| [`docs/installation/docker.md`](installation/docker.md) | Docker ARM64 deployment |
| [`docs/configuration/mpd-setup.md`](configuration/mpd-setup.md) | MPD daemon configuration per audio backend |
| [`docs/configuration/network-mounts.md`](configuration/network-mounts.md) | SMB/NAS mount via `/etc/fstab` |
| [`docs/usage/dashboard-guide.md`](usage/dashboard-guide.md) | UI feature reference |
| [`docs/usage/touch-gestures.md`](usage/touch-gestures.md) | Touchscreen interaction guide |
| [`docs/features/play-statistics.md`](features/play-statistics.md) | Play statistics schema and usage |
| [`docs/features/recommendations.md`](features/recommendations.md) | Music recommendation algorithm |
| [`docs/features/remote-control.md`](features/remote-control.md) | Web API and remote dashboard |
| [`docs/troubleshooting/README.md`](troubleshooting/README.md) | Common issues index |
| [`docs/troubleshooting/audio-backend.md`](troubleshooting/audio-backend.md) | ALSA/PipeWire/PulseAudio issues |
| [`docs/troubleshooting/network-mounts.md`](troubleshooting/network-mounts.md) | SMB/NFS mount failures |
| [`docs/troubleshooting/touch-screen.md`](troubleshooting/touch-screen.md) | Touchscreen calibration and drivers |
| [`docs/development/README.md`](development/README.md) | Contributor guide |
| [`docs/development/testing.md`](development/testing.md) | How to run tests |
| [`docs/development/release-process.md`](development/release-process.md) | PyInstaller builds, GitHub release workflow |
| [`PHASE_DEVELOPMENT_PLAN.md`](PHASE_DEVELOPMENT_PLAN.md) | Slice-based development plan |

## Quick Reference

- **Engine:** MPD audio daemon + Python 3 controller
- **Audio:** FLAC native (other formats via mutagen)
- **GUI:** Tkinter over X11/Wayland+XWayland
- **Network stats:** SQLite, all local, no telemetry
- **RAM target:** App under 50 MB
- **MPD IPC:** Local socket on port 6600
- **License:** TBD

## Getting Started

New to this project? Start with:

1. **`docs/installation/pi-zero-setup.md`** — if you're building on a Pi Zero 2 W
2. **`docs/installation/cross-distro.md`** — if you're using another Linux distro
3. **`PHASE_DEVELOPMENT_PLAN.md`** — if you're contributing code
