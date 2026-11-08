# Slice 1.4: System Detection & Config Management - Implementation Plan

## Goal
Auto-detect runtime environment; generate appropriate MPD config with correct audio backend configuration.

## Implementation Steps

### 1. Create `core/system.py` — SystemDetector Class
- `detect_audio_backend()` → `'alsa' | 'pipewire' | 'pulse' | 'unknown'`
  - Check for PipeWire: `pipewire --version`, check `PIPEWIRE_SOCKET` env, check `pipewire` process
  - Check for PulseAudio: `pulseaudio --version`, check `PULSE_SERVER` env, check `pulseaudio` process
  - Default to ALSA on Linux
- `detect_display_server()` → `'x11' | 'wayland' | 'unknown'`
  - Check `WAYLAND_DISPLAY` env var
  - Check `DISPLAY` env var for X11
  - Check for XWayland: `XWAYLAND_DISPLAY` or check if XWayland process running
- `detect_distro()` → `'debian' | 'ubuntu' | 'fedora' | 'arch' | 'alpine' | 'nixos' | 'unknown'`
  - Read `/etc/os-release` for `ID` and `ID_LIKE`
- `get_mpd_config_template()` → path to appropriate `mpd.conf.*` template
- `generate_mpd_conf(output_path='/etc/mpd.conf')` — writes MPD config with correct `audio_output` block:
  - ALSA: `audio_output { type "alsa" ... }` with device selection (HDMI vs 3.5mm vs HAT DAC)
  - PipeWire: `audio_output { type "pipewire" ... }`
  - PulseAudio: `audio_output { type "pulse" ... }`
  - Null: `audio_output { type "null" ... }` (headless/testing)

### 2. Create MPD Config Templates
- `configs/mpd.conf.alsa` - ALSA audio_output block with device placeholder
- `configs/mpd.conf.pipewire` - PipeWire audio_output block
- `configs/mpd.conf.pulse` - PulseAudio audio_output block
- `configs/mpd.conf.null` - Null audio_output for headless/testing

### 3. Create `core/config.py` - Configuration Management
- `Config` class with:
  - Schema with detected values + user overrides
  - Load/save to `config.json`
  - Defaults for all settings
  - Validation of config values

### 4. Test Script
- `tests/test_slice_1_4.py` - Test system detection and config generation

## File Structure After Implementation
```
core/
  ├── system.py          # SystemDetector class
  ├── config.py          # Config management
  ├── player.py          # Existing
  ├── artwork.py         # Existing
configs/
  ├── mpd.conf.alsa
  ├── mpd.conf.pipewire
  ├── mpd.conf.pulse
  ├── mpd.conf.null
tests/
  ├── test_slice_1_4.py  # New test script
  ├── test_artwork.py    # Existing
  ├── test_slice_1_1.py  # Existing
  └── __pycache__/
```

## Test Criteria
```bash
python3 -c "
from core.system import SystemDetector
d = SystemDetector()
print('Audio backend:', d.detect_audio_backend())
print('Display server:', d.detect_display_server())
print('Distro:', d.detect_distro())
print('MPD template:', d.get_mpd_config_template())
d.generate_mpd_conf('/tmp/test_mpd.conf')
# Verify: cat /tmp/test_mpd.conf | grep -q 'audio_output'
"
```

**Pass if:** Correctly identifies backend on Pi OS Bookworm (ALSA or PipeWire), Fedora (PipeWire), Ubuntu (PipeWire); generates valid MPD config MPD accepts; handles Wayland vs X11 detection for Pi OS Bookworm+ touchscreen edge cases.