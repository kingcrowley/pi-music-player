# Docker Deployment Guide

Run the music player in Docker for consistent deployment across distributions.

> **Target:** ARM64 (Raspberry Pi), x86_64 (for development/testing)

---

## Prerequisites

- Docker installed on host
- Network-mounted music library accessible inside container
- Audio device access (ALSA/PipeWire/PulseAudio)

---

## Dockerfile

```dockerfile
FROM python:3.11-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    mpd \
    alsa-utils \
    cifs-utils \
    nfs-common \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir python-mpd2 mutagen requests

WORKDIR /app
COPY . /app

EXPOSE 8080

CMD ["python3", "main.py"]
```

---

## Build

```bash
docker build -t pi-music-player .
```

---

## Run

```bash
docker run -d \
  --name=music-player \
  --restart=unless-stopped \
  --network=host \
  -v /mnt/nas/music:/mnt/nas/music:ro \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  -v /run/user/$(id -u)/pulse:/run/user/0/pulse \
  -v /etc/samba/credentials:/etc/samba/credentials:ro \
  -e DISPLAY=$DISPLAY \
  -e USER=mpd \
  pi-music-player
```

### Mount Options Explained

| Mount | Purpose |
|-------|---------|
| `/mnt/nas/music:/mnt/nas/music:ro` | Read-only music library access |
| `/tmp/.X11-unix:/tmp/.X11-unix` | X11 socket for GUI display |
| `/run/user/$(id -u)/pulse:/run/user/0/pulse` | PipeWire/PulseAudio socket |
| `/etc/samba/credentials:/etc/samba/credentials:ro` | NAS credentials (read-only) |
| `--network=host` | Use host network stack (MPD socket access) |
| `-e DISPLAY=$DISPLAY` | Pass display environment |

---

## Headless Mode

For headless deployments (no GUI), run without X11 mounts:

```bash
docker run -d \
  --name=music-player \
  --restart=unless-stopped \
  --network=host \
  -v /mnt/nas/music:/mnt/nas/music:ro \
  pi-music-player
```

Control via the web API at `http://<container-ip>:8080`.

---

## ARM64 Build

For Raspberry Pi (ARM64):

```bash
# Build for ARM64
docker buildx build --platform linux/arm64 -t pi-music-player:arm64 .
```

---

## Troubleshooting

### Audio not working

```bash
# Check audio devices inside container
docker exec -it music-player aplay -l

# Check PulseAudio/PipeWire socket
docker exec -it music-player ls /run/user/0/pulse/
```

### GUI not displaying

```bash
# Check X11 socket
docker exec -it music-player ls /tmp/.X11-unix/

# Verify DISPLAY env
docker exec -it music-player echo $DISPLAY
```

### Network mount not accessible

```bash
# Check mount inside container
docker exec -it music-player ls /mnt/nas/music/
```