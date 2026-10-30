# Remote Control Guide

Control your music player remotely via a local web API.

> **Feature:** Phase 4
> **Server:** Lightweight Python HTTP server on `localhost:8080`
> **Auth:** Random token per session, printed to console + QR code

---

## Overview

The remote control feature lets you control playback from any device on your local network:

- **Phone:** Open `http://<pi-ip>:8080` in mobile Safari/Chrome
- **Tablet:** Same URL
- **Laptop:** Same URL
- **Terminal:** Use `curl` with bearer token

No app installation required — the web dashboard is served statically from the player.

---

## Getting Started

### Enable Remote Control

In `config.json`:

```json
{
  "remote_control": {
    "enabled": true,
    "port": 8080,
    "host": "0.0.0.0",
    "auth_required": true,
    "cors_enabled": true
  }
}
```

### Start the Server

```bash
python3 main.py --with-remote
```

Or set `remote_control.enabled=true` and run normally:

```bash
python3 main.py
```

Console output will show:

```
Remote server started on http://0.0.0.0:8080
Auth token: x7y9z2w4a1b3c5d6e7f8
QR Code:
████████████████████████████████████████████████
████ ▄▄▄▄▄ █▄ ▀▄ █ ▄▄▄ ▄ ▀▀████ ▄▄▄▄▄ █ ▄▄▄ ▄▄▄ █
...
Open http://<pi-ip>:8080 on your phone to control the player
```

### Access via Web Browser

Open on any device on the same network:

```
http://<pi-ip-address>:8080
```

Replace `<pi-ip-address>` with your Pi's local IP (e.g., `192.168.1.50`):

```
http://192.168.1.50:8080
```

Find your Pi's IP:

```bash
hostname -I
# or
ip addr show
```

---

## API Endpoints

All endpoints require the auth token (except `/api/status` which is read-only).

### Authentication

Include token in `Authorization` header:

```bash
curl -H "Authorization: Bearer x7y9z2w4a1b3c5d6e7f8" \
  http://192.168.1.50:8080/api/status
```

Or pass token as query parameter:

```bash
curl "http://192.168.1.50:8080/api/status?token=x7y9z2w4a1b3c5d6e7f8"
```

### Endpoints

| Endpoint | Method | Description | Auth Required |
|----------|--------|-------------|---------------|
| `/api/status` | GET | Current song, state, volume, position | No (read-only) |
| `/api/queue` | GET | Current playlist queue | Yes |
| `/api/control` | POST | Play/pause/next/prev/stop/volume/seek | Yes |
| `/api/art` | GET | Current album art image | Yes |
| `/api/library` | GET | Browse artists/albums (paginated) | Yes |
| `/api/queue/add` | POST | Add track/album to queue | Yes |

### Example: Get Status

```bash
curl http://192.168.1.50:8080/api/status
```

Response:

```json
{
  "state": "play",
  "song": {
    "file": "/mnt/nas/music/pink-floyd/dark-side/time.flac",
    "artist": "Pink Floyd",
    "album": "The Dark Side of the Moon",
    "title": "Time",
    "time": 412,
    "duration": 432
  },
  "volume": 75,
  "elapsed": 412,
  "duration": 432
}
```

### Example: Control Playback

```bash
# Play / Pause
curl -X POST -H "Authorization: Bearer x7y9z2w4a1b3c5d6e7f8" \
  -H "Content-Type: application/json" \
  -d '{"action": "toggle"}' \
  http://192.168.1.50:8080/api/control

# Next track
curl -X POST -H "Authorization: Bearer x7y9z2w4a1b3c5d6e7f8" \
  -H "Content-Type: application/json" \
  -d '{"action": "next"}' \
  http://192.168.1.50:8080/api/control

# Previous track
curl -X POST ... -d '{"action": "previous"}'

# Stop
curl -X POST ... -d '{"action": "stop"}'

# Volume
curl -X POST ... -d '{"action": "volume", "value": 50}'

# Seek to position (seconds)
curl -X POST ... -d '{"action": "seek", "seconds": 120}'
```

### Example: Get Queue

```bash
curl -H "Authorization: Bearer x7y9z2w4a1b3c5d6e7f8" \
  http://192.168.1.50:8080/api/queue
```

Response:

```json
[
  {
    "position": 1,
    "file": "/mnt/nas/music/pink-floyd/dark-side/time.flac",
    "artist": "Pink Floyd",
    "title": "Time",
    "duration": 432
  },
  {
    "position": 2,
    "file": "/mnt/nas/music/pink-floyd/dark-side/the-great-gig-in-the-sky.flac",
    "artist": "Pink Floyd",
    "title": "The Great Gig in the Sky",
    "duration": 278
  }
]
```

### Example: Add to Queue

```bash
curl -X POST -H "Authorization: Bearer x7y9z2w4a1b3c5d6e7f8" \
  -H "Content-Type: application/json" \
  -d '{"path": "/mnt/nas/music/the-beatles/abbey-road/come-together.flac"}' \
  http://192.168.1.50:8080/api/queue/add
```

---

## Web Dashboard

A phone-friendly static web UI is served from `/web/`:

### Dashboard Screens

| Screen | Path | Description |
|--------|------|-------------|
| Now Playing | `/` | Playback controls + album art |
| Queue | `/queue` | Current playlist |
| Library | `/library` | Browse artists/albums |
| Settings | `/settings` | Audio, network, display |

### Responsive Design

Works on:
- Mobile Safari/Chrome (iOS/Android)
- Desktop browsers
- Tablets

### Features

- [ ] Now playing with album art
- [ ] Playback controls (play/pause, next, previous, stop)
- [ ] Volume slider
- [ ] Queue view with reordering
- [ ] Library browse (artists → albums → tracks)
- [ ] Search (artist/album/track name)

---

## Security

### Token Authentication

- **Token generated:** Random 32-character token per session
- **Token printed:** Console output on startup
- **QR code:** Displayed for easy mobile setup
- **Token lifetime:** Valid until server restart
- **Token rotation:** New token on each restart

### Network Security

- **Local network only:** Server binds to `0.0.0.0` but only reachable on LAN
- **No internet exposure:** Do not port-forward to the internet
- **CORS enabled:** Allows requests from browser on same network
- **No HTTPS:** Internal network only; use `http://` not `https://`

> **Warning:** Do not expose port 8080 to the public internet. This API has no rate limiting or password protection beyond the bearer token.

---

## Code Reference

### RemoteServer Class

Located in `plugins/remote.py`:

```python
from plugins.remote import RemoteServer

server = RemoteServer(
    host='0.0.0.0',
    port=8080,
    auth_token='x7y9z2w4a1b3c5d6e7f8',
    cors_enabled=True
)

server.start()

# Server handles:
# - /api/status → returns current MPD state
# - /api/control → forwards commands to MPD client
# - /api/art → serves cached album art image
# - /api/library → browses MPD library
```

### MPD Integration

Remote server commands translate to MPD calls:

```python
# Control commands
control_map = {
    'play': lambda: client.play(),
    'pause': lambda: client.pause(1),
    'toggle': lambda: toggle_play(),
    'next': lambda: client.next(),
    'previous': lambda: client.previous(),
    'stop': lambda: client.stop(),
    'volume': lambda v: client.setvol(v),
    'seek': lambda s: client.seekcur(s)
}
```

---

## Manual Testing

```bash
# Start server
python3 main.py --with-remote

# Get status
curl http://192.168.1.50:8080/api/status

# Control with token
curl -X POST -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"action": "toggle"}' \
  http://192.168.1.50:8080/api/control

# Open in browser
# http://192.168.1.50:8080
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Can't connect to `localhost:8080` | Check server started (`--with-remote` flag) |
| 401 Unauthorized | Include valid bearer token in request |
| CORS error | Set `cors_enabled: true` in config.json |
| Blank web page | Check `/web/` directory exists |
| Server won't start | Port 8080 already in use; change `port` in config |
| Token not recognized | Server restarted? Get new token from console |
| Phone can't see Pi | Same Wi-Fi network required |