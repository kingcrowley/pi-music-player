# Troubleshooting: Touch Screen

Issues related to touchscreen calibration, driver problems, touch event handling, and gesture input.

> **Feature:** Phase 1.5 (UI)
> **Target:** Raspberry Pi Zero 2 W with touchscreen (capacitive/resistive)

---

## Quick Diagnosis

```bash
# 1. Check touch device is visible
xinput --list

# 2. Check device node exists
ls /dev/input/event*

# 3. Calibrate touch (Debian/Ubuntu)
sudo apt install -y xinput-calibration
calibrate

# 4. Check touch in console (press touch screen)
cat /dev/input/eventX | xxd
```

---

## Touch Device Not Detected

### Step 1: Check Kernel Drivers

```bash
# Check all input devices
cat /proc/bus/input/devices

# Look for your touchscreen driver (e.g., ft5406, stmpe, ads7846)
# Example: touchscreen input at /dev/input/event2
```

### Step 2: Check Driver Loading

```bash
# Check dmesg for touchscreen drivers
dmesg | grep -i touch
dmesg | grep -i ft5406
dmesg | grep -i stmpe
```

### Step 3: Check Permissions

```bash
# Ensure user can read touch device
ls -la /dev/input/event2
# Should show: crw-rw---- 1 root input 13, 2

# Add user to input group
sudo usermod -aG input $USER
# Log out and back in
```

---

## Touch Events Not Registering

### Problem: Taps not registering on UI

**Possible causes:**

1. **Wayland/X11 mismatch** — Tkinter on Wayland without XWayland
2. **Calibration** — Touchscreen not calibrated
3. **Input group** — User lacks permission
4. **Device mapping** — Wrong event device

### Solution: Wayland/XWayland on Pi OS Bookworm+

```bash
# Check if XWayland is installed
dpkg -l | grep xwayland

# Force X11 backend for Tkinter
export GDK_BACKEND=x11
python3 main.py

# Or in config.json:
{
  "tkinter_backend": "x11"
}
```

### Solution: Calibrate Touchscreen

```bash
# Debian/Ubuntu/Raspberry Pi OS
sudo apt install -y xinput-calibration
calibrate

# Arch
sudo pacman -S xinput_calibrator
xinput_calibrator

# Alpine
apk add xinput-calibrator
calibrate
```

---

## Touch Lag / Slow Response

### Check Input Device Polling

```bash
# Check current device
xinput list-props "Your Touchscreen Name"

# Adjust polling if supported
# Or check for system load
top
```

### Reduce UI Polling

In `config.json`:

```json
{
  "ui_poll_interval_ms": 1000,
  "touch_threshold_ms": 50
}
```

---

## Resistive vs Capacitive Touchscreen

### Resistive Touchscreen

- **Requires pressure** — works with finger or stylus
- **Single touch** typically
- **Driver:** Often `ads7846`, `stmpe`

### Capacitive Touchscreen

- **Works with bare finger**
- **Multi-touch** supported
- **Driver:** Often `ft5406`, `goodix`

### Configuration Differences

| Feature | Resistive | Capacitive |
|---------|-----------|------------|
| Driver | `ads7846` | `ft5406` |
| Multi-touch | No | Yes |
| Calibration needed | Yes | Usually no |
| Device node | `/dev/input/eventX` | `/dev/input/eventX` |

---

## Multi-Touch Issues

### Problem: Pinch-to-zoom not working

**Cause:** Tkinter has limited multi-touch support.

**Workaround:**
- Use two-finger tap for right-click equivalent
- Use single-finger gestures for navigation
- Pinch gestures require GTK-based UI (not Tkinter)

---

## Touchscreen Black Screen

### Problem: Touchscreen works but screen is black

**Fix:** Check display configuration in `/boot/firmware/config.txt`:

```ini
# Raspberry Pi Zero 2 W
dispmanx_display0_width=480
dispmanx_display0_height=320
hdmi_force_hotplug=1
hdmi_group=2
hdmi_mode=87
hdmi_cvt=480 320 60 1 0 0 0
```

Reboot after editing:
```bash
sudo reboot
```

---

## Testing Touch Input

### Python Touch Test

```python
# test_touch.py
from core.ui import TouchTester

tester = TouchTester()

# Test tap
result = tester.test_tap(target='play_button')
print(f'Tap registered: {result}')

# Test swipe
result = tester.test_swipe(direction='left')
print(f'Swipe detected: {result}')

# Test long press
result = tester.test_long_press(target='album_art')
print(f'Long press menu: {result}')
```

Run:
```bash
python3 test_touch.py
```

---

## Distribution-Specific Touch Setup

### Raspberry Pi OS (Desktop/Bookworm)

With Wayland default:

```bash
# Check XWayland
dpkg -l | grep xwayland

# Force X11 for Tkinter
export GDK_BACKEND=x11
export DISPLAY=:0
python3 main.py
```

### Arch Linux

```bash
# Install calibration tools
sudo pacman -S xorg-xinput xorg-xev

# Check touch device
xinput --list
xinput test "Your Touchscreen"
```

### Fedora

```bash
# Touchscreen should work out of box
# Check if needed
dnf install xorg-x11-apps
xinput --list
```

### Alpine Linux

```bash
apk add xinput xorg-xev
```

---

## Getting Help

```bash
# Collect diagnostic info
cat /proc/bus/input/devices > touch-diag.txt
xinput --list >> touch-diag.txt
dmesg | grep -i touch >> touch-diag.txt
aplay -l >> touch-diag.txt  # Audio (related on Pi)

# Include in GitHub issue
```
