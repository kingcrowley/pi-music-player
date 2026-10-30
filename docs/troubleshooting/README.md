# Troubleshooting Index

Common issues and solutions for the Low-RAM Python Music Player.

---

## Quick Diagnosis

```bash
# 1. Check if MPD is running
sudo systemctl status mpd

# 2. Check MPD port
netstat -tlnp | grep 6600

# 3. Check app memory
python3 -c "import resource; print(f'RSS: {resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024:.1f} MB')"

# 4. Check network mount
ls /mnt/nas/music/

# 5. Check audio
aplay -l
```

---

## By Category

| Category | Common Issues | Guide |
|----------|---------------|-------|
| **Audio** | No sound, wrong device, PipeWire/ALSA confusion | [`audio-backend.md`](audio-backend.md) |
| **Network Mounts** | NAS not mounting, SMB/NFS failures | [`network-mounts.md`](network-mounts.md) |
| **Touch Screen** | Taps not working, calibration, Wayland issues | [`touch-screen.md`](touch-screen.md) |
| **MPD Connection** | Can't connect to MPD, connection drops | See below |
| **App Won't Start** | Tkinter errors, missing dependencies | See below |
| **Performance** | High memory, UI lag | See below |

---

## MPD Connection Issues

### MPD Not Running

```bash
# Start MPD
sudo systemctl start mpd

# Enable on boot
sudo systemctl enable mpd
```

### MPD Connection Refused

```bash
# Check port
netstat -tlnp | grep 6600

# If not listening, check config
grep -E "bind_to_address|port" /etc/mpd.conf
# Should be: bind_to_address "127.0.0.1", port "6600"
```

### MPD Restarts / Connection Drops

Add to `config.json`:

```json
{
  "mpd_reconnect_backoff": true,
  "mpd_reconnect_max_attempts": 10,
  "mpd_reconnect_base_delay": 1
}
```

---

## App Won't Start

### Tkinter Not Found

```bash
# Debian/Ubuntu
sudo apt install python3-tk

# Fedora
sudo dnf install python3-tkinter

# Arch
sudo pacman -S tk

# Alpine
apk add tk
```

### Wayland / XWayland Issues

Raspberry Pi OS Bookworm+ uses Wayland. Tkinter requires XWayland:

```bash
# Check if XWayland is installed
dpkg -l | grep xwayland

# Force X11 for the app
export GDK_BACKEND=x11
python3 main.py
```

### Import Errors

```bash
# Install dependencies
pip3 install --break-system-packages python-mpd2 mutagen requests

# Or in virtual environment
python3 -m venv venv
source venv/bin/activate
pip install python-mpd2 mutagen requests
python3 main.py
```

---

## Performance Issues

### High Memory Usage

```bash
# Check actual usage
free -h
ps aux | grep python3

# Expected:
# MPD: ~15 MB
# Python app: ~15-30 MB
# OS: ~150-200 MB
# Total: < 300 MB
```

If over 350 MB, check for:
- Memory leak in background threads
- Too many cached album art images
- Unclosed database connections

### UI Lag

```bash
# Run with reduced polling
python3 main.py --poll-interval 2.0  # 2 seconds instead of 1

# Or reduce cache size
# config.json: "art_cache_max_mb": 20
```

### Audio Stuttering

```bash
# Check MPD buffer settings
grep -A5 "audio_output" /etc/mpd.conf

# Increase buffer if needed
# In audio_output block: buffer_before_play "10%"
```

---

## Log Files

| Log | Location |
|-----|----------|
| MPD | `sudo journalctl -u mpd -f` |
| Systemd service | `sudo journalctl -u music-player -f` |
| App (stdout) | Console where you ran `python3 main.py` |
| Audio | `dmesg | grep -i audio` |

---

## Getting Help

1. **Check logs first** (see above)
2. **Search existing issues** on GitHub
3. **Open a new issue** with:
   - `uname -a` output
   - `python3 --version` and `pip list | grep -E "mpd|mutagen|requests"`
   - Relevant log snippets
   - Steps to reproduce