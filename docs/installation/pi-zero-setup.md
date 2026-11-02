# Raspberry Pi Zero 2W Setup Guide

Complete walkthrough for getting the music player running on a fresh Raspberry Pi Zero 2 W with Raspberry Pi OS.

> **Target:** Raspberry Pi Zero 2 W (512 MB RAM)
> **OS:** Raspberry Pi OS Bookworm (Lite or Desktop)
> **RAM:** App under 50 MB, total system under 64 MB

---

## Prerequisites

| Item | Requirement |
|------|-------------|
| Hardware | Raspberry Pi Zero 2 W |
| Storage | microSD card (8 GB minimum, 16 GB recommended) |
| Power | 5V / 2.5A power supply |
| Audio | HDMI, I²S DAC HAT, or USB DAC (Pi Zero 2 W has **no** 3.5mm jack) |
| Network | Wi-Fi or Ethernet |
| Display | Touchscreen (capacitive/resistive via `/dev/input/eventX`) or headless |
| Storage | NAS or local music files (SMB/NFS) |

---

## Step 1: Flash Raspberry Pi OS

Download Raspberry Pi OS Bookworm from the official site and flash to microSD using Raspberry Pi Imager.

> **Note:** The Desktop version includes X11 + Tkinter pre-installed. The Lite version requires manual X11 setup.

Enable SSH during imaging (Raspberry Pi Imager → Advanced options → Enable SSH). Set a username and password during imaging — Bookworm does not default to `pi` / `raspberry`.

---

## Step 2: First Boot

```bash
ssh <username>@<pi-ip>
```

Update system:

```bash
sudo apt update && sudo apt upgrade -y
```

---

## Step 3: Install System Dependencies

```bash
# Install MPD + mpc + Python 3 + Tkinter + NAS tools
sudo apt install -y mpd mpc python3 python3-pip python3-tk cifs-utils nfs-common

# Create the player user
sudo useradd -r -s /bin/false player

# Add player to audio group for sound device access
sudo usermod -aG audio player

# Create the MPD data directories
sudo mkdir -p /var/lib/mpd /var/lib/mpd/cache /var/lib/mpd/playlists /var/log/mpd

# Set ownership
sudo chown -R player:player /var/lib/mpd /var/log/mpd

# Set proper permissions
sudo chmod 755 /var/lib/mpd /var/lib/mpd/cache /var/lib/mpd/playlists /var/log/mpd
```

---

## Step 4: Configure MPD Audio Output

**Important:** Replace the entire `/etc/mpd.conf`. Do not append to the stock config — Debian's default already contains `music_directory`, `database {}`, `bind_to_address`, and other settings that will conflict.

```ini
# MPD config for Raspberry Pi Zero 2 W
# Audio output — HDMI (Pi Zero 2 W has no 3.5mm jack)
# I²S DAC HAT users: change device to "hw:CARD=<cardname>,DEV=0"
#   Use amixer -c <card> scontrols to find the control name

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
}

audio_output {
    type        "alsa"
    name        "Pi HDMI"
    device      "hdmi:CARD=vc4hdmi,DEV=0"
    mixer_type  "software"
}

# For I²S DAC HAT, replace the audio_output block with:
# audio_output {
#     type        "alsa"
#     name        "DAC HAT"
#     device      "hw:CARD=<cardname>,DEV=0"
#     mixer_type  "hardware"
#     mixer_control "<control name>"
# }
# Run: amixer -c <card> scontrols  to list control names
```

Disable MPD's systemd socket (it binds port 6600 on all interfaces regardless of `bind_to_address`):

```bash
sudo systemctl disable --now mpd.socket
```

---

## Step 5: Mount Network Storage (NAS via SMB)

Mount **before** starting MPD so it can find music files:

Create mount point:

```bash
sudo mkdir -p /mnt/nas/music
```

Create credentials file (`/etc/samba/credentials`):

```ini
username=your_nas_username
password=your_nas_password
```

```bash
sudo chmod 600 /etc/samba/credentials
```

Edit `/etc/fstab`:

```ini
# SMB mount (use _netdev and x-systemd.automount for NAS reliability)
//nas-ip/music /mnt/nas/music cifs credentials=/etc/samba/credentials,iocharset=utf8,vers=3.0,uid=player,gid=player,file_mode=0644,dir_mode=0755,_netdev,x-systemd.automount 0 0

# Or NFS
# nas-ip:/music /mnt/nas/music nfs defaults,vers=4.1,_netdev,x-systemd.automount 0 0
```

Test mount (unmount first if already mounted, then remount with new options):

```bash
sudo umount /mnt/nas/music 2>/dev/null || true
sudo mount /mnt/nas/music
ls /mnt/nas/music/
```

> **Security:** Never store NAS credentials in the Python app or repository. The credentials file at `/etc/samba/credentials` is root-owned with `chmod 600`.

> **Note:** Ownership on CIFS mounts comes from the `uid=`/`gid=` mount options, not `chown`. Running `chown` on a CIFS mount will appear to succeed but will not actually change ownership.

---

## Step 6: Install Python Dependencies

```bash
pip3 install --break-system-packages python-mpd2 mutagen requests
```

> **Note:** On Raspberry Pi OS Bookworm, `--break-system-packages` is required for pip-installed packages in the system Python. Alternatively, use a virtual environment.

---

## Step 7: Deploy the Application

Clone the repository:

```bash
git clone <your-repo-url> pi-music-player
cd pi-music-player
```

Install:

```bash
pip3 install --break-system-packages -r requirements.txt
```

Or install dependencies manually:

```bash
pip3 install --break-system-packages python-mpd2 mutagen requests
```

---

## Step 8: Run the Player

Start MPD first (if not already running):

```bash
sudo systemctl start mpd
```

Run the Python application:

```bash
python3 main.py
```

Expected behavior:
- Window opens fullscreen (touchscreen) or windowed (desktop)
- Album art displays (or placeholder)
- Track info updates when songs change
- Play/pause, next/previous controls work
- Volume slider controls MPD volume

**Note:** To add music to the MPD queue, use relative paths from `music_directory`:

```bash
# Add a track from /mnt/nas/music/
mpc update
mpc add artist/album/track.flac
mpc play
```

---

## Step 9: Configure Auto-Start on Boot

**Important:** Run as the desktop user, not `player`. The `player` user cannot access the X11/Wayland display or read `~/.local` Python packages installed as `pi`.

Create a systemd service (`/etc/systemd/system/music-player.service`):

```ini
[Unit]
Description=Pi Music Player
After=network.target mpd.service
Wants=mpd.service

[Service]
Type=simple
User=<your-username>
WorkingDirectory=/home/<your-username>/pi-music-player
ExecStart=/usr/bin/python3 /home/<your-username>/pi-music-player/main.py
Restart=on-failure
RestartSec=5
Environment=DISPLAY=:0

[Install]
WantedBy=multi-user.target
```

Replace `<your-username>` with your actual username (e.g., `pi`, `david`, etc.).

Enable:

```bash
sudo systemctl enable music-player.service
sudo systemctl start music-player.service
```

---

## Troubleshooting

### No audio output

```bash
# Check ALSA devices
aplay -l

# Test speaker
speaker-test -c2

# Check MPD audio config
grep -A 10 audio_output /etc/mpd.conf
```

### MPD won't connect

```bash
# Check MPD is running
sudo systemctl status mpd

# Check port (ss replaces netstat on Bookworm)
ss -tlnp | grep 6600

# If address is already in use, stop MPD first
sudo systemctl stop mpd
sudo systemctl start mpd

# Check logs
sudo journalctl -u mpd -f
```

### "chown: cannot access '/var/lib/mpd': No such file or directory"

```bash
# The MPD data directories may not exist yet
sudo mkdir -p /var/lib/mpd /var/lib/mpd/cache /var/lib/mpd/playlists /var/log/mpd
sudo chown -R player:player /var/lib/mpd /var/log/mpd
```

### "useradd: user 'player' already exists"

```bash
# User already created — skip useradd and just set ownership
sudo mkdir -p /var/lib/mpd /var/lib/mpd/cache
sudo chown -R player:player /var/lib/mpd
```

### MPD "Address already in use"

```bash
# MPD socket binds port 6600 — disable it
sudo systemctl disable --now mpd.socket
sudo systemctl restart mpd
```

### Tkinter won't start (Bookworm Wayland)

```bash
# Set XWayland for Tkinter
export DISPLAY=:0
python3 main.py

# Or check if Tkinter is installed
python3 -c "import tkinter; print(tkinter.TkVersion)"
```

### Music files not found

```bash
# Check mount
ls /mnt/nas/music/

# Check MPD database update (mpd doesn't auto-update SMB/NFS)
sudo systemctl start mpd
sudo -u player mpc update
mpc add artist/album/track.flac
mpc play
```

---

## RAM Budget Check

After boot and before running the player:

```bash
free -h
```

Expected Pi Zero 2 W idle: ~200-250 MB used by OS/MPD. Player should add <50 MB. Total under 300 MB to avoid swap.

Check player memory:

```bash
# Run player in one terminal, check in another
ps -o rss= -C python3
```

The `ps -o rss=` command measures the actual resident set size (memory actually in RAM).

---
