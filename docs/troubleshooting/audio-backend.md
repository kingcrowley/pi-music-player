# Troubleshooting: Audio Backend

Issues related to MPD audio output configuration across ALSA, PipeWire, PulseAudio, and Wayland.

---

## Quick Diagnosis

```bash
# Check audio devices
aplay -l
aplay -L

# Check PipeWire
pactl info
pactl list sinks short

# Check PulseAudio
pulseaudio --check -v
pactl list sinks

# Check MPD status
sudo systemctl status mpd
mpc status

# Check MPD audio config
grep -A 10 "audio_output" /etc/mpd.conf
```

---

## No Audio Output

### Step 1: Check MPD is Running

```bash
sudo systemctl status mpd
# If not running:
sudo systemctl start mpd
sudo systemctl enable mpd  # Enable on boot
```

### Step 2: Test Audio Device

```bash
# 3.5mm jack test
speaker-test -c2 -t wav
aplay -D hw:0,0 /usr/share/sounds/alsa/Front_Center.wav

# HDMI test (on Pi Zero 2W)
amixer cset numid=3 2  # Force HDMI
speaker-test -c2 -t wav
```

### Step 3: Check MPD Config

The critical part of `/etc/mpd.conf`:

```ini
audio_output {
    type "alsa"
    name "Pi Audio"
    device "hw:0,0"
    mixer_type "hardware"
    mixer_control "PCM"
}
```

| Device | Setting |
|--------|---------|
| 3.5mm Jack | `device "hw:0,0"` |
| HDMI | `device "hw:0,1"` |
| USB DAC | `device "hw:CARD=Device,DEV=0"` |
| Default | `device "default"` |

### Step 4: Restart MPD

```bash
sudo systemctl restart mpd
```

---

## Wrong Audio Device Playing

### Problem

MPD is playing to HDMI but you want 3.5mm jack (or vice-versa).

### Solution

1. Check available devices:
   ```bash
   aplay -L
   ```

2. Update `/etc/mpd.conf`:
   ```ini
   audio_output {
       type "alsa"
       name "Pi Audio"
       device "hw:0,0"           # 3.5mm jack
       # device "hw:0,1"        # HDMI  
       mixer_type "hardware"
   }
   ```

3. Restart MPD:
   ```bash
   sudo systemctl restart mpd
   ```

4. Test:
   ```bash
   mpc play
   ```

---

## ALSA vs PipeWire vs PulseAudio

### Auto-Detection

The player auto-detects audio backend via `core/system.py`:

```python
from core.system import SystemDetector
d = SystemDetector()
print('Backend:', d.detect_audio_backend())
print('MPD template:', d.get_mpd_config_template())
```

| Backend | Detected If | MPD Config Type |
|---------|-------------|-----------------|
| ALSA | `/dev/snd/pcm*` exists, no PipeWire socket | `type "alsa"` |
| PipeWire | `/run/user/1000/pipewire-0` exists | `type "pipewire"` |
| PulseAudio | `pactl info` succeeds | `type "pulse"` |
| Unknown | Fallback | `type "null"` |

### Manual Override

In `config.json`:

```json
{
  "mpd_audio_backend": "pipewire"
}
```

---

## Raspberry Pi OS Bookworm+ (Wayland)

### Problem

On Raspberry Pi OS Bookworm+, Wayland is the default display server. MPD + ALSA should work, but some users encounter issues with:

1. Audio switching to different device after Wayland login
2. Volume control not working
3. "Failed to open audio output" errors

### Solution

#### Option 1: Force ALSA (Recommended)

Ensure MPD config explicitly uses ALSA hardware device:

```ini
audio_output {
    type "alsa"
    name "Pi Audio"
    device "plughw:0,0"        # plughw handles sample rate conversion
    mixer_type "hardware"
    mixer_device "default"
    mixer_control "PCM"
}
```

#### Option 2: Use PipeWire Backend

If using desktop environment with PipeWire:

```bash
# Install required
sudo apt install pipewire-pulse pipewire-alsa

# MPD config
audio_output {
    type "pipewire"
    name "PipeWire Output"
}
```

Restart everything:

```bash
sudo systemctl restart pipewire pipewire-pulse
sudo systemctl restart mpd
```

---

## Volume Control Issues

### Problem: Volume slider does nothing

```ini
# In /etc/mpd.conf — use software mixer
audio_output {
    type "alsa"
    name "Pi Audio"
    device "hw:0,0"
    mixer_type "software"    # ← Changed from "hardware"
    # Remove mixer_device and mixer_control lines
}
```

### Problem: Volume steps too large

Add to `/etc/mpd.conf`:

```ini
volume_range_db "-20"  # Finer granularity
```

---

## Mixer Group Permission Denied

### Problem

```
ALSA lib pcm_mixer.c:8546:(snd_mixer_get_volume_ptr0) Volume pointer set
```

### Solution

Add MPD user to audio group:

```bash
sudo usermod -aG audio player
sudo systemctl restart mpd
```

---

## Buffer Underruns / Audio Stuttering

### Problem

Audio cuts out or stutters, especially during high CPU usage.

### Solution

Increase MPD buffer settings in `/etc/mpd.conf`:

```ini
# Inside audio_output block
audio_output {
    type "alsa"
    name "Pi Audio"
    device "hw:0,0"
    mixer_type "software"
    buffer_before_play "20%"    # Increase from default 20%
}

# Global audio settings
decoder {
    plugin "flac"
    enabled "yes"
    buffer_size "8192"
}
```

Also, ensure adequate RAM available:

```bash
free -h
# Should have >50MB free RAM when playing
```

---

## Audio Format Not Supported

### Problem

MPD won't play certain files.

### Solution

Check file format:

```bash
file /mnt/nas/music/song.flac
mediainfo /mnt/nas/music/song.flac
```

MPD native support:
- ✅ FLAC, MP3, OGG, WAV (native)
- Requires GStreamer plugins for: M4A/AAC, WMA, Opus

Install plugins if needed:

```bash
# Debian/Ubuntu
sudo apt install gstreamer1.0-plugins-good gstreamer1.0-plugins-bad

# For PipeWire users
sudo apt install pipewire-media-session
```

---

## Testing Checklist

```bash
# 1. MPD running
sudo systemctl status mpd

# 2. MPD can play a file
mpc clear
mpc add /mnt/nas/music/test.flac
mpc play
mpc volume 50

# 3. Audio device available
aplay -l | grep -v "card 0.*HDMI"  # Should show audio card

# 4. Correct MPD config
grep -A5 "audio_output" /etc/mpd.conf | head -10

# 5. Restart MPD after config changes
sudo systemctl restart mpd
```

---

## Getting Audio Device Names

If you need specific hardware device names:

```bash
# List all PCM devices
aplay -L

# List all cards
cat /proc/asound/cards

# Query specific device
amixer -c 0 contents
```

Common device names for Pi:
- `hw:0,0` — 3.5mm jack
- `hw:0,1` — HDMI
- `hw:1,0` — USB DAC
- `default` — System default