# MPD Configuration Reference

Configuration options for MPD (Music Player Daemon) by audio backend.

> **Important:** MPD talks to audio hardware directly. The Python app never touches ALSA/PipeWire/PulseAudio. `core/system.py` generates the correct `audio_output` block for your detected backend.

---

## Audio Output Configuration

### ALSA (Default on Raspberry Pi OS, Alpine, Debian)

`/etc/mpd.conf`:

```ini
audio_output {
    type "alsa"
    name "Pi Audio"
    device "hw:0,0"          # 3.5mm jack
    # device "hw:0,1"        # HDMI
    # device "hw:CARD=HAT,DEV=0"  # USB DAC HAT
    mixer_type "hardware"
    mixer_device "PCM"
    mixer_control "PCM"
}
```

Available ALSA devices:

```bash
aplay -l
aplay -L
```

### PipeWire (Default on Fedora, Ubuntu 22.10+, Arch)

`/etc/mpd.conf`:

```ini
audio_output {
    type "pipewire"
    name "PipeWire Output"
}
```

### PulseAudio (Older Ubuntu, Debian)

`/etc/mpd.conf`:

```ini
audio_output {
    type "pulse"
    name "PulseAudio Output"
}
```

### Null Output (Headless / Testing)

`/etc/mpd.conf`:

```ini
audio_output {
    type "null"
    name "Null Output"
}
```

---

## General MPD Configuration

### Minimal Working Config

```ini
# Audio output
audio_output {
    type "alsa"
    name "Music Player"
    device "hw:0,0"
    mixer_type "hardware"
    mixer_control "PCM"
}

# Music library
music_directory "/mnt/nas/music"
database {
    path "/var/lib/mpd/mpd.db"
    auto_update "yes"
}

# Cache
cache_directory "/var/lib/mpd/cache"
cache_size "1024"

# Network
bind_to_address "127.0.0.1"
port "6600"

# Security
user "player"
```

### Security Hardening

```ini
# Bind only to localhost (no network access to MPD port)
bind_to_address "127.0.0.1"
port "6600"

# Run as unprivileged user
user "player"

# File permissions
directory_mode "0755"
default_permissions "read"
```

### Performance Tuning

```ini
# Larger cache for faster library operations
cache_size "2048"

# Auto-update database when files change
auto_update "yes"

# Follow symlinks
follow_symlinks "yes"
```

---

## Complete Template Examples

### Raspberry Pi OS (ALSA, 3.5mm Jack)

```ini
audio_output {
    type "alsa"
    name "Pi Audio"
    device "hw:0,0"
    mixer_type "hardware"
    mixer_device "PCM"
    mixer_control "PCM"
}

music_directory "/mnt/nas/music"
database { path "/var/lib/mpd/mpd.db"; auto_update "yes"; }
cache_directory "/var/lib/mpd/cache"
cache_size "1024"

bind_to_address "127.0.0.1"
port "6600"
user "player"
```

### Raspberry Pi OS (HDMI Audio)

```ini
audio_output {
    type "alsa"
    name "Pi HDMI"
    device "hw:0,1"
    mixer_type "software"
}
```

### Fedora (PipeWire)

```ini
audio_output {
    type "pipewire"
    name "PipeWire Output"
}

music_directory "/mnt/nas/music"
database { path "/var/lib/mpd/mpd.db"; auto_update "yes"; }
cache_directory "/var/lib/mpd/cache"
cache_size "1024"

bind_to_address "127.0.0.1"
port "6600"
user "player"
```

---

## Testing MPD Configuration

```bash
# Check MPD config syntax
mpd --stdout --no-daemon --verbose

# Check MPD is listening
netstat -tlnp | grep 6600

# Test connection
mpc ping

# Check status
mpc status

# Add test music
mpc add /mnt/nas/music/test.flac
mpc play
```

---

## Common Issues

### "Failed to open audio output"

- Verify `aplay -l` lists your device
- Check user `player` has audio group membership: `sudo usermod -aG audio player`
- Try `mixer_type "software"` instead of `"hardware"`

### "Permission denied" on music directory

```bash
sudo chown -R player:player /mnt/nas/music
sudo chmod -R 755 /mnt/nas/music
```

### MPD won't start

```bash
sudo systemctl status mpd
sudo journalctl -u mpd -f
```
