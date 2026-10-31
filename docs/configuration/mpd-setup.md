# MPD Configuration Reference

Configuration options for MPD (Music Player Daemon) by audio backend.

> **Important:** MPD talks to audio hardware directly. The Python app never touches ALSA/PipeWire/PulseAudio.

> **Warning:** Replace the entire `/etc/mpd.conf` — do not append to the stock config. Debian's default config already contains `music_directory`, `database {}`, `bind_to_address`, and other settings that will conflict.

---

## Audio Output Configuration

### ALSA — Raspberry Pi Zero 2 W (HDMI)

**Note:** Pi Zero 2 W has **no** 3.5mm jack. Use HDMI, I²S DAC HAT, or USB DAC.

```ini
audio_output {
    type        "alsa"
    name        "Pi HDMI"
    device      "hdmi:CARD=vc4hdmi,DEV=0"
    mixer_type  "software"
}
```

- `vc4hdmi` has no hardware mixer — use `mixer_type "software"`
- Plain `hw:` usually fails with a format error on `vc4hdmi`
- Use `hdmi:CARD=vc4hdmi,DEV=0` or `plughw:`

### ALSA — I²S DAC HAT

```ini
audio_output {
    type        "alsa"
    name        "DAC HAT"
    device      "hw:CARD=<cardname>,DEV=0"
    mixer_type  "hardware"
    mixer_control "<control name>"
}
```

Run `amixer -c <card> scontrols` to list the control names on your HAT.

### ALSA — USB DAC

```ini
audio_output {
    type        "alsa"
    name        "USB DAC"
    device      "hw:CARD=USB,DEV=0"
    mixer_type  "hardware"
}
```

### ALSA — Generic (Plughw)

```ini
audio_output {
    type        "alsa"
    name        "Generic"
    device      "plughw:0,0"
}
```

### PipeWire (Fedora 38+, Ubuntu 22.10+, Arch)

```ini
audio_output {
    type        "pipewire"
    name        "PipeWire Output"
}
```

### PulseAudio (Older Ubuntu, Debian)

```ini
audio_output {
    type        "pulse"
    name        "PulseAudio Output"
}
```

### Null Output (Headless / Testing)

```ini
audio_output {
    type        "null"
    name        "Null Output"
}
```

---

## Complete MPD Config Template

### Raspberry Pi Zero 2 W (HDMI)

```ini
music_directory    "/mnt/nas/music"
playlist_directory "/var/lib/mpd/playlists"
state_file         "/var/lib/mpd/state"
sticker_file       "/var/lib/mpd/sticker.sql"
log_file           "syslog"
user               "player"
bind_to_address    "127.0.0.1"
port               "6600"

# inotify does NOT work on SMB/NFS mounts — set to "no"
# Use `mpc update` manually instead
auto_update        "no"

database {
    plugin          "simple"
    path            "/var/lib/mpd/mpd.db"
    cache_directory "/var/lib/mpd/cache"
}

audio_output {
    type        "alsa"
    name        "Pi HDMI"
    device      "hdmi:CARD=vc4hdmi,DEV=0"
    mixer_type  "software"
}
```

### Raspberry Pi Zero 2 W (I²S DAC HAT)

```ini
music_directory    "/mnt/nas/music"
playlist_directory "/var/lib/mpd/playlists"
state_file         "/var/lib/mpd/state"
sticker_file       "/var/lib/mpd/sticker.sql"
log_file           "syslog"
user               "player"
bind_to_address    "127.0.0.1"
port               "6600"
auto_update        "no"

database {
    plugin          "simple"
    path            "/var/lib/mpd/mpd.db"
    cache_directory "/var/lib/mpd/cache"
}

audio_output {
    type        "alsa"
    name        "DAC HAT"
    device      "hw:CARD=<cardname>,DEV=0"
    mixer_type  "hardware"
    mixer_control "<control name>"
}
```

---

## Testing MPD Configuration

```bash
# Check MPD config syntax (mpd --stdout is deprecated, use --stderr)
mpd --stderr --no-daemon --verbose

# Check MPD is listening
ss -tlnp | grep 6600

# Test connection
mpc ping

# Check status
mpc status

# Add test music (use relative path from music_directory)
mpc update
mpc add artist/album/track.flac
mpc play
```

---

## Common Issues

### "Failed to open audio output"

- Verify `aplay -l` lists your device
- Check user `player` has audio group membership: `sudo usermod -aG audio player`
- Try `mixer_type "software"` instead of `"hardware"`
- Use `hdmi:CARD=vc4hdmi,DEV=0` or `plughw:` instead of `hw:0,0`

### "Permission denied" on music directory

```bash
# On CIFS mounts, ownership comes from uid=/gid= mount options, not chown
# Edit /etc/fstab: uid=player,gid=player
sudo mount -a
```

### "Address already in use" (port 6600)

```bash
# MPD's systemd socket binds port 6600 — disable it
sudo systemctl disable --now mpd.socket
sudo systemctl restart mpd
```

### MPD won't start

```bash
sudo systemctl status mpd
sudo journalctl -u mpd -f
```

### "unrecognised parameter cache_directory"

This MPD version does not support `cache_directory`. Remove it from your config.

### "unrecognised parameter cache_size"

`cache_size` requires `cache_directory`. Remove both.

### "auto_update is in the wrong place"

`auto_update` is a top-level setting, not inside `database {}`.

### "database {} block conflicts with db_file"

Replace the entire `/etc/mpd.conf` — do not append to the stock config.