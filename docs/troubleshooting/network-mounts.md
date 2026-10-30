# Troubleshooting: Network Mounts (SMB/NFS)

Issues related to mounting NAS music libraries via SMB/CIFS or NFS.

---

## Quick Diagnosis

```bash
# 1. Check mount point
ls /mnt/nas/music/

# 2. Check fstab
cat /etc/fstab | grep -E "cifs|nfs"

# 3. Check credentials
ls -la /etc/samba/credentials

# 4. Check network
ping nas-server-ip

# 5. Check mount status
mount | grep -E "cifs|nfs"
```

---

## SMB/CIFS Mount Issues

### "mount error(13): Permission denied"

**Cause:** Wrong credentials or NAS share permissions.

**Fix:**
1. Verify credentials file:
   ```bash
   cat /etc/samba/credentials
   # Should show: username=, password=
   ```

2. Test manual mount:
   ```bash
   sudo mount -t cifs //nas-ip/music /mnt/nas/music \
     -o credentials=/etc/samba/credentials,vers=3.0
   ```

3. Check NAS share permissions — ensure user has read access.

### "mount error(112): Host is down"

**Cause:** NAS unreachable or wrong IP.

**Fix:**
```bash
ping nas-ip
nmap -p 445 nas-ip  # Check SMB port open
```

### "mount error(115): Operation in progress" / Slow mount

**Cause:** Network timeout or DNS resolution.

**Fix:** Add to `/etc/fstab`:
```ini
//nas-ip/music /mnt/nas/music cifs credentials=/etc/samba/credentials,iocharset=utf8,vers=3.0,x-systemd.automount,timeout=10 0 0
```

### "mount.cifs: No such device"

**Cause:** CIFS kernel module not loaded.

**Fix:**
```bash
sudo modprobe cifs
# Then retry mount
sudo mount -a
```

### "mount: /mnt/nas/music: cannot allocate memory"

**Cause:** Large file operations on limited RAM.

**Fix:** Add to `/etc/fstab`:
```ini
//nas-ip/music /mnt/nas/music cifs credentials=/etc/samba/credentials,iocharset=utf8,vers=3.0,rsize=16384,wsize=16384 0 0
```

---

## NFS Mount Issues

### "mount.nfs: Connection refused"

**Cause:** NFS server not running or firewall blocking.

**Fix:**
```bash
# Check NFS server
showmount -e nas-ip

# On NAS, ensure:
# - NFS service running
# - /etc/exports has correct permissions
# - Firewall allows ports 111, 2049
```

### "mount.nfs: Access denied by server while mounting"

**Cause:** NFS export permissions mismatch.

**Fix:**
```bash
# Check exports on NAS
cat /etc/exports

# Should have something like:
# /music 192.168.1.0/24(rw,sync,no_subtree_check,no_root_squash)
```

### "mount.nfs: Stale NFS file handle"

**Cause:** NAS restarted, client has stale handle.

**Fix:**
```bash
sudo umount -f /mnt/nas/music
sudo mount -a
```

---

## Auto-Mount Not Working

### Problem: `x-systemd.automount` not working

**Fix:**
```bash
# Reload systemd
sudo systemctl daemon-reload

# Check mount unit
systemctl status mnt-nas-music.mount
systemctl status mnt-nas-music.automount

# Restart automount
sudo systemctl restart mnt-nas-music.automount

# Test by accessing
ls /mnt/nas/music/
```

### Problem: Mount happens before network is ready

**Fix:** Add network dependency in fstab:
```ini
//nas-ip/music /mnt/nas/music cifs credentials=/etc/samba/credentials,iocharset=utf8,vers=3.0,x-systemd.automount,_netdev 0 0
```

The `_netdev` flag tells systemd this is a network device.

---

## Credential File Issues

### "Permission denied" on credentials file

**Fix:**
```bash
# Must be root-owned, 600 permissions
sudo chown root:root /etc/samba/credentials
sudo chmod 600 /etc/samba/credentials
```

### Credentials not working after password change

**Fix:**
1. Update `/etc/samba/credentials` with new password
2. Remount:
   ```bash
   sudo umount /mnt/nas/music
   sudo mount -a
   ```

---

## Testing Mount Stability

### Simulate NAS Disconnect

```bash
# 1. Unplug NAS / power off
# 2. Try access
ls /mnt/nas/music/   # Should hang with automount, not fail immediately

# 3. Reconnect NAS
# 4. Wait a few seconds
sleep 5

# 5. Try access again
ls /mnt/nas/music/   # Should work
```

### Check Auto-Mount Recovery

```bash
# After NAS reconnect
systemctl status mnt-nas-music.automount
# Should show: active (waiting)

# Check mount
systemctl status mnt-nas-music.mount
# Should show: active (mounted)
```

---

## File Listing Issues

### "ls: reading directory '/mnt/nas/music': Input/output error"

**Cause:** Network dropped during directory read.

**Fix:**
```bash
# Remount
sudo umount -f /mnt/nas/music
sudo mount -a
```

### Missing files after mount

**Cause:** Mounted over existing files.

**Fix:**
```bash
# Check if mount point had files before mount
sudo umount /mnt/nas/music
ls /mnt/nas/music/  # Should be empty
# Then remount
sudo mount -a
```

---

## MPD Can't Find Music

### Problem: `mpc update` shows no new files

**Fix:**
1. Verify mount is accessible by `mpd` user:
   ```bash
   sudo -u player ls /mnt/nas/music/
   ```

2. Check MPD config:
   ```bash
   grep music_directory /etc/mpd.conf
   # Should be: music_directory "/mnt/nas/music"
   ```

3. Force database rebuild:
   ```bash
   sudo -u player mpc update --wait
   ```

---

## Performance Optimization

### Slow file browsing

Add to fstab:
```ini
# SMB
//nas-ip/music /mnt/nas/music cifs credentials=/etc/samba/credentials,iocharset=utf8,vers=3.0,rsize=16384,wsize=16384,cache=strict,actimeo=600 0 0

# NFS
nas-ip:/music /mnt/nas/music nfs vers=4.1,hard,intr,rsize=32768,wsize=32768,timeo=600 0 0
```

### High CPU during file listing

```bash
# Check if caching is enabled
grep actimeo /etc/fstab
```

---

## Getting Help

```bash
# For SMB
sudo mount -t cifs //nas-ip/music /mnt/nas/music -o credentials=/etc/samba/credentials,vers=3.0 -vvv

# For NFS
sudo mount -t nfs nas-ip:/music /mnt/nas/music -vvv
```

Check:
- `dmesg | tail -20` for kernel messages
- `journalctl -f` for systemd mount messages
- NAS logs for connection attempts