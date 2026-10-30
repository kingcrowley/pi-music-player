# Network Mount Configuration

Mounting your music library from NAS (SMB/CIFS or NFS) via `/etc/fstab`.

> **Security:** Never store network share credentials in the Python application or repository. Use root-owned credential files with restrictive permissions.

---

## Samba (SMB/CIFS) Mount

### 1. Install CIFS Utilities

```bash
# Debian/Ubuntu
sudo apt install cifs-utils

# Fedora
sudo dnf install cifs-utils

# Arch
sudo pacman -S cifs-utils

# Alpine
sudo apk add cifs-utils

# NixOS (declarative)
# services.samba.mountPoints."/mnt/nas/music" = { ... };
```

### 2. Create Credentials File

```bash
sudo nano /etc/samba/credentials
```

Contents:

```ini
username=your_nas_username
password=your_nas_password
domain=NASWORKGROUP         # (if required)
```

Set permissions:

```bash
sudo chmod 600 /etc/samba/credentials
```

### 3. Create Mount Point

```bash
sudo mkdir -p /mnt/nas/music
```

### 4. Edit `/etc/fstab`

```bash
sudo nano /etc/fstab
```

Add:

```ini
//nas-server-ip/music /mnt/nas/music cifs credentials=/etc/samba/credentials,iocharset=utf8,vers=3.0,uid=mpd,gid=audio,file_mode=0644,dir_mode=0755,x-systemd.automount 0 0
```

### Options Explained

| Option | Purpose |
|--------|---------|
| `credentials=/etc/samba/credentials` | Use credential file (never inline passwords) |
| `iocharset=utf8` | Proper Unicode handling |
| `vers=3.0` | SMB3 protocol (avoid insecure SMB1) |
| `uid=mpd,gid=audio` | Run MPD-owned for access |
| `file_mode=0644,dir_mode=0755` | Proper file permissions |
| `x-systemd.automount` | Lazy-mount: mount only when accessed (reduces boot delay, handles NAS offline) |

### 5. Test

```bash
sudo mount -a
ls /mnt/nas/music/
```

---

## NFS Mount

### 1. Install NFS Utilities

```bash
# Debian/Ubuntu
sudo apt install nfs-common

# Fedora
sudo dnf install nfs-utils

# Arch
sudo pacman -S nfs-utils

# Alpine
sudo apk add nfs-utils
```

### 2. Edit `/etc/fstab`

```bash
sudo nano /etc/fstab
```

Add:

```ini
nas-server-ip:/music /mnt/nas/music nfs vers=4.1,hard,intr,rw,exec,x-systemd.automount 0 0
```

### Options Explained

| Option | Purpose |
|--------|---------|
| `vers=4.1` | NFS v4.1 (or v4.0 if server doesn't support v4.1) |
| `hard` | Retry on server failure (not `soft` — can corrupt files) |
| `intr` | Allow Ctrl-C interrupt |
| `x-systemd.automount` | Lazy-mount on access |

### 5. Test

```bash
sudo mount -a
ls /mnt/nas/music/
```

---

## Troubleshooting Network Mounts

| Error | Cause | Fix |
|-------|-------|-----|
| "mount error(112): Cannot find server" | NAS unreachable | Check network, IP, power |
| "mount error(13): Permission denied" | Wrong credentials or permissions | Recreate credentials file, check NAS share permissions |
| "mount.nfs: Connection refused" | NFS server not running | Enable NFS service on NAS |
| "/bin/sh: 1: cannot create /etc/samba/credentials" | Read-only filesystem | Mount `/etc` read-write, or use systemd credential file |
| "mount.cifs: No such device" | CIFS module not loaded | `sudo modprobe cifs` then retry |
| Slow boot | Mount tried before network ready | Add `x-systemd.automount` option |

---

## Security Best Practices

1. **Never inline credentials in `/etc/fstab`** — always use `/etc/samba/credentials`
2. **Set `chmod 600` on credentials file** — only root can read it
3. **Use `vers=3.0` or `vers=4.1`** — avoid deprecated SMB1/CIFS
4. **Use `x-systemd.automount`** — mounts only when accessed, fails gracefully if NAS is off
5. **Never store credentials in the Python app** — the app reads music via MPD's `music_directory` mount
6. **Mount as `mpd` user** — least privilege for the audio service

---

## Testing Mount Stability

```bash
# Simulate NAS disconnect
# (Unplug NAS)

# Attempt read — should hang with x-systemd.automount, not fail
ls /mnt/nas/music/

# Reconnect NAS
# (Plug back in)
sleep 5

# Should auto-recover
ls /mnt/nas/music/  # should work

# Check systemd auto-recovery
systemctl status mnt-nas-music.mount
```
