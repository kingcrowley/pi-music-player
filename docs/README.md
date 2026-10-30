# Low-Resource Linux Music Player - Start Here

## What Is This?

A modular, low-resource music player for Linux-based systems, designed to run efficiently on resource-constrained hardware like Raspberry Pi Zero 2 W, while remaining flexible enough for any Linux desktop or server.

Built with Python 3 + Tkinter + a **plugin architecture** that lets anyone add audio backends, UI widgets, features, and integrations without modifying core code.

| Property | Value |
|----------|-------|
| **Target platforms** | All Linux distros (Pi Zero, desktops, servers, ARM64/x86) |
| **RAM target** | App under 50 MB on Pi Zero 2 W |
| **Architecture** | Modular plugin system (audio backends, features, UI widgets) |
| **Core GUI** | Tkinter touchscreen interface |
| **Default audio engine** | MPD daemon via python-mpd2 (reads FLAC natively) |
| **Supported audio backends** | ALSA, PipeWire, PulseAudio (via plugins) |
| **Supported formats** | FLAC, MP3, M4A via mutagen |
| **Album art** | Mutagen local extraction → Cover Art Archive fallback |
| **Statistics** | SQLite play tracking (local, no telemetry) |
| **Recommendations** | Local co-occurrence model (artist/genre affinity) |
| **Remote control** | Local web API on `localhost:8080` (plugin) |
| **License** | MIT |

## Project Goals

1. **Low-resource music player for any Linux system** — from Pi Zero to desktop
2. **Modular plugin architecture** — community can add backends, features, UI elements
3. **Cross-distro support** — Debian, Ubuntu, Fedora, Arch, Alpine, NixOS
4. **Docs-first development** — every feature ships with documentation
5. **Privacy-safe** — all play stats and recommendations stored locally, no telemetry

## Document Map

| Document | Purpose |
|----------|---------|
| [`docs/README.md`](README.md) | This file — project overview and orientation |
| [`docs/installation/pi-zero-setup.md`](installation/pi-zero-setup.md) | Raspberry Pi Zero 2W complete walkthrough |
| [`docs/installation/cross-distro.md`](installation/cross-distro.md) | Installation on Debian, Ubuntu, Fedora, Arch, Alpine, NixOS |
| [`docs/installation/docker.md`](installation/docker.md) | Docker ARM64/amd64 deployment |
| [`docs/configuration/mpd-setup.md`](configuration/mpd-setup.md) | MPD daemon configuration per audio backend |
| [`docs/configuration/network-mounts.md`](configuration/network-mounts.md) | SMB/NAS mount via `/etc/fstab` |
| [`docs/development/plugin-api.md`](development/plugin-api.md) | Plugin API specification for developers |
| [`docs/development/plugin-developer-guide.md`](development/plugin-developer-guide.md) | Step-by-step guide to building plugins |
| [`docs/usage/dashboard-guide.md`](usage/dashboard-guide.md) | UI feature reference |
| [`docs/usage/touch-gestures.md`](usage/touch-gestures.md) | Touchscreen interaction guide |
| [`docs/features/play-statistics.md`](features/play-statistics.md) | Play statistics schema and usage |
| [`docs/features/recommendations.md`](features/recommendations.md) | Music recommendation algorithm |
| [`docs/features/remote-control.md`](features/remote-control.md) | Web API and remote dashboard |
| [`docs/troubleshooting/README.md`](troubleshooting/README.md) | Common issues index |
| [`docs/troubleshooting/audio-backend.md`](troubleshooting/audio-backend.md) | ALSA/PipeWire/PulseAudio issues |
| [`docs/troubleshooting/network-mounts.md`](troubleshooting/network-mounts.md) | SMB/NFS mount failures |
| [`docs/troubleshooting/touch-screen.md`](troubleshooting/touch-screen.md) | Touchscreen calibration and drivers |
| [`docs/development/testing.md`](development/testing.md) | How to run tests |
| [`docs/development/release-process.md`](development/release-process.md) | Builds, GitHub release workflow |
| [`PHASE_DEVELOPMENT_PLAN.md`](PHASE_DEVELOPMENT_PLAN.md) | Slice-based development plan with plugin system |

## Quick Reference

- **Engine:** Python 3 controller + MPD audio daemon
- **Architecture:** Plugin-based (audio backends, features, UI widgets)
- **Audio:** FLAC native (other formats via mutagen)
- **GUI:** Tkinter over X11/Wayland+XWayland
- **Network stats:** SQLite, all local, no telemetry
- **RAM target:** App under 50 MB
- **License:** MIT

## Getting Started

New to this project? Start with:

1. **`docs/installation/pi-zero-setup.md`** — if you're building on a Pi Zero 2 W
2. **`docs/installation/cross-distro.md`** — if you're using another Linux distro
3. **`docs/development/plugin-api.md`** — if you want to build a plugin
4. **`docs/development/plugin-developer-guide.md`** — step-by-step plugin tutorial
5. **`PHASE_DEVELOPMENT_PLAN.md`** — if you're contributing code
