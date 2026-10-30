# Cross-Distro Installation Guide

Instructions for installing the music player on various Linux distributions.

> **Compatibility:** Debian, Ubuntu, Fedora, Arch Linux, Alpine Linux, NixOS

---

## Debian / Ubuntu / Raspberry Pi OS

### 1. System Dependencies

```bash
sudo apt update
sudo apt install -y mpd python3 python3-pip python3-tk cifs-utils nfs-common
```

### 2. Python Dependencies

```bash
pip3 install python-mpd2 mutagen requests
# On Debian Bookworm / Ubuntu 23.04+, use --break-system-packages if not in virtualenv:
# pip3 install --break-system-packages python-mpd2 mutagen requests
```

### 3. Run

```bash
python3 main.py
```

---

## Fedora

### 1. System Dependencies

```bash
sudo dnf install -y mpd python3 python3-pip python3-tk cifs-utils nfs-utils
```

### 2. Python Dependencies

```bash
pip3 install --user python-mpd2 mutagen requests
```

### 3. PipeWire vs PulseAudio

Fedora 38+ uses PipeWire by default. Configure MPD for PipeWire in `/etc/mpd.conf`:

```ini
audio_output {
    type "pipewire"
    name "PipeWire Output"
}
```

### 4. Run

```bash
python3 main.py
```

---

## Arch Linux

### 1. System Dependencies

```bash
sudo pacman -Syu --noconfirm
sudo pacman -S --noconfirm mpd python python-pip tk cifs-utils nfs-utils
```

### 2. Python Dependencies

```bash
pip3 install --user python-mpd2 mutagen requests
```

### 3. PipeWire vs PulseAudio

Arch may use PipeWire or PulseAudio depending on your setup. The player auto-detects:

- **PipeWire:** `audio_output { type "pipewire" ... }` in `mpd.conf`
- **PulseAudio:** `audio_output { type "pulse" ... }` in `mpd.conf`

### 4. Run

```bash
python3 main.py
```

---

## Alpine Linux

### 1. System Dependencies

Alpine uses musl libc (not glibc) and OpenRC (not systemd).

```bash
sudo apk add mpd python3 py3-pip tk cifs-utils nfs-utils
```

### 2. Python Dependencies

```bash
pip3 install --user python-mpd2 mutagen requests
```

### 3. ALSA Backend (default on Alpine)

Configure MPD for ALSA in `/etc/mpd.conf`:

```ini
audio_output {
    type "alsa"
    name "Alpine Audio"
    device "hw:0,0"
}
```

### 4. Run

```bash
python3 main.py
```

---

## NixOS

NixOS requires declarative configuration via `/etc/nixos/configuration.nix`.

### 1. Enable Services

```nix
# /etc/nixos/configuration.nix
{
  services.mpd = {
    enable = true;
    musicDirectory = "/mnt/nas/music";
    extraConfig = ''
      audio_output {
        type "pipewire"
        name "PipeWire Output"
      }
    '';
  };

  environment.systemPackages = with pkgs; [
    python3 python3Packages.mpd2 python3Packages.mutagen python3Packages.requests
    cifs-utils nfs-utils
  ];

  # For X11
  services.xserver.enable = true;
  services.xserver.displayManager.lightdm.enable = true;
  services.xserver.windowManager.startxfce4.enable = true;
}
```

Apply:

```bash
sudo nixos-rebuild switch
```

### 2. Run

```bash
python3 main.py
```

---

## Universal Installation via Docker (ARM64)

For a consistent deployment across distributions, use Docker:

```bash
# Build
docker build -t pi-music-player .

# Run with host network and audio
docker run -d \
  --name=music-player \
  --restart=unless-stopped \
  --network=host \
  -v /mnt/nas/music:/mnt/nas/music:ro \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  -v /run/user/$(id -u)/pulse:/run/user/0/pulse \
  -e DISPLAY=$DISPLAY \
  pi-music-player
```

See [`docker.md`](docker.md) for full details.

---

## Audio Backend Detection

The player auto-detects the audio backend via `core/system.py` on startup:

```bash
python3 -c "
from core.system import SystemDetector
d = SystemDetector()
print('Audio backend:', d.detect_audio_backend())
print('Display server:', d.detect_display_server())
print('Distro:', d.detect_distro())
print('MPD template:', d.get_mpd_config_template())
"
```

If auto-detection fails, set the backend manually in `config.json`:

```json
{
  "mpd_audio_backend": "pipewire",
  "mpd_config_path": "/etc/mpd.conf"
}
```

---

## Network Mount Configuration

Mount your music library from NAS (SMB/NFS) via `/etc/fstab`:

### SMB Mount

```bash
# 1. Create credentials file
sudo nano /etc/samba/credentials
# username=
# password=
sudo chmod 600 /etc/samba/credentials

# 2. Add to /etc/fstab
//nas-ip/music /mnt/nas/music cifs credentials=/etc/samba/credentials,iocharset=utf8,vers=3.0,uid=mpd,gid=audio,file_mode=0644,dir_mode=0755 0 0
```

### NFS Mount

```bash
# Add to /etc/fstab
nas-ip:/music /mnt/nas/music nfs defaults,vers=4.1,hard,intr 0 0
```

Test:

```bash
sudo mount -a
ls /mnt/nas/music/
```

---

## Post-Installation

1. **Update MPD database:** `mpc update` after adding music
2. **Verify MPD is running:** `sudo systemctl status mpd`
3. **Run the player:** `python3 main.py`
4. **Check memory usage:** `free -h` (should stay under 64 MB for the app)

See [`docs/troubleshooting/audio-backend.md`](../troubleshooting/audio-backend.md) for audio issues.
