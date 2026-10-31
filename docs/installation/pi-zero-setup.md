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
| Audio | 3.5mm jack, HDMI, or USB DAC HAT |
| Network | Wi-Fi or Ethernet |
| Display | Touchscreen (capacitive/resistive via `/dev/input/eventX`) or headless |
| Storage | NAS or local music files (SMB/NFS) |

---

## Step 1: Flash Raspberry Pi OS

Download Raspberry Pi OS Bookworm from the official site and flash to microSD using Raspberry Pi Imager.

> **Note:** The Desktop version includes X11 + Tkinter pre-installed. The Lite version requires manual X11 setup.

Enable SSH during imaging (Raspberry Pi Imager → Advanced options → Enable SSH).

---

## Step 2: First Boot

```bash
ssh pi@raspberrypi.local
# Default password: raspberry
```

Update system:

```bash
sudo apt update && sudo apt upgrade -y
```

---

## Step 3: Install System Dependencies

```bash
# Install MPD + Python 3 + Tkinter + NAS tools
sudo apt install -y mpd python3 python3-pip python3-tk cifs-utils nfs-common

# Create the player user (the -d flag requires the directory to exist)
sudo useradd -r -s /bin/false player

# Create the MPD data directories
sudo mkdir -p /var/lib/mpd /var/lib/mpd/cache /var/lib/mpd/playlists

# Set ownership
sudo chown -R player:player /var/lib/mpd

# Set proper permissions
sudo chmod 755 /var/lib/mpd
sudo chmod 755 /var/lib/mpd/cache
sudo chmod 755 /var/lib/mpd/playlists
```

---

## Step 4: Configure MPD Audio Output

Edit `/etc/mpd.conf`:

```ini
# Audio output — ALSA on Raspberry Pi
audio_output {
    type "alsa"
    name "Pi Audio"
    device "hw:0,0"          # 3.5mm jack = hw:0,0, HDMI = hw:0,1
    mixer_type "hardware"
    mixer_device "PCM"
    mixer_control "PCM"
}

# Music library (adjust path)
music_directory "/mnt/nas/music"

database {
    path "/var/lib/mpd/mpd.db"
    auto_update "yes"
}

cache_directory "/var/lib/mpd/cache"
cache_size "1024"

bind_to_address "127.0.0.1"
port "6600"

user "player"
```

Start MPD:

```bash
sudo systemctl enable mpd
sudo systemctl start mpd
sudo systemctl status mpd
```

Verify audio:

```bash
mpc status
# Should show: volume: n/a, state: stopped, song: None
```

Test audio device:

```bash
aplay -l                    # List ALSA devices
aplay -D hw:0,0 /usr/share/sounds/alsa/Front_Center.wav  # Test 3.5mm jack
```

---

## Step 5: Mount Network Storage (NAS via SMB)

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
# SMB mount
//nas-ip/music /mnt/nas/music cifs credentials=/etc/samba/credentials,iocharset=utf8,vers=3.0,uid=player,gid=player,file_mode=0644,dir_mode=0755 0 0

# Or NFS
# nas-ip:/music /mnt/nas/music nfs defaults,vers=4.1 0 0
```

Test mount:

```bash
sudo mount -a
ls /mnt/nas/music/
```

> **Security:** Never store NAS credentials in the Python app or repository. The credentials file at `/etc/samba/credentials` is root-owned with `chmod 600`.

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

```bash
# Start MPD (if not already running)
sudo systemctl start mpd

# Run the Python application
python3 main.py
```

Expected behavior:
- Window opens fullscreen (touchscreen) or windowed (desktop)
- Album art displays (or placeholder)
- Track info updates when songs change
- Play/pause, next/previous controls work
- Volume slider controls MPD volume

---

## Step 9: Configure Auto-Start on Boot

Create a systemd service (`/etc/systemd/system/music-player.service`):

```ini
[Unit]
Description=Pi Music Player
After=network.target mpd.service
Wants=mpd.service

[Service]
Type=simple
User=player
WorkingDirectory=/home/pi/pi-music-player
ExecStart=/usr/bin/python3 /home/pi/pi-music-player/main.py
Restart=on-failure
RestartSec=5
Environment=DISPLAY=:0

[Install]
WantedBy=multi-user.target
```

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
grep audio_output /etc/mpd.conf
```

### MPD won't connect

```bash
# Check MPD is running
sudo systemctl status mpd

# Check port
netstat -tlnp | grep 6600

# Restart MPD
sudo systemctl restart mpd
```

### "chown: cannot access '/var/lib/mpd': No such file or directory"

```bash
# The MPD data directories may not exist yet. Create them:
sudo mkdir -p /var/lib/mpd /var/lib/mpd/cache /var/lib/mpd/playlists

# Then set ownership
sudo chown -R player:player /var/lib/mpd
```

### "useradd: user 'player' already exists"

```bash
# User already created — skip useradd and just set ownership
sudo mkdir -p /var/lib/mpd /var/lib/mpd/cache
sudo chown -R player:player /var/lib/mpd
```

### Tkinter won't start

```bash
# Desktop version (Bookworm with Wayland)
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

# Check MPD database update
mpc update
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
ps aux | grep python3
# Or
python3 -c "import resource; print(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)"
```
