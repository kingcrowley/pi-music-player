# Touchscreen Gestures Guide

Touch interaction guide for the music player UI on Raspberry Pi Zero 2 W with touchscreen.

> **Target:** Resistive / capacitive touchscreen, X11/Wayland
> **Default mode:** Touchscreen-optimized (large touch targets)

---

## Touch Interaction Overview

The music player supports multi-touch gestures optimized for finger interaction:

| Gesture | Action |
|---------|--------|
| Tap | Click a button, select an option |
| Long press | Open context menu, show additional options |
| Swipe | Navigate between screens |
| Drag | Adjust volume, seek in progress bar |
| Pinch | Zoom in UI (for detail views) |

---

## Primary Touch Controls

### Album Art (Tap)
- **Behavior:** Single tap shows the current album art, double tap opens art gallery (all album art from history)
- **Long press:** Quick actions (Share, Favorite, Set as wallpaper)

### Play/Pause (Tap)
- **Behavior:** Toggles between play and pause states
- **Visual feedback:** Button changes icon and color
- **Long press:** Show current queue

### Volume (Drag)
- **Behavior:** Drag horizontally to adjust volume (0-100%)
- **Visual feedback:** Volume bars show current level
- **Release:** Saves volume setting to MPD

### Progress Bar (Tap)
- **Behavior:** Taps anywhere on progress bar seeks to that position
- **Drag:** Fine control seeking with continuous updates

### Next/Previous Buttons (Tap)
- **Behavior:** Navigate to next or previous track
- **Long press:** Skip to next album (if available)

---

## Navigation Gestures

### Screen Navigation (Swipe)

#### Left to Right
- **Target:** Anywhere on screen
- **Action:** Switch to Previous screen (Settings → Discover → Stats → Now Playing)

#### Right to Left
- **Target:** Anywhere on screen
- **Action:** Switch to Next screen (Now Playing → Stats → Discover → Settings)

#### Up/Down
- **Target:** Scroll inside lists/modals
- **Action:** Scroll through options, dialogs, queue

### Swipe Intensity
- **Light swipe:** Quick navigation between screens
- **Strong swipe:** Immediate screen transition
- **Very strong swipe:** Triggers a long-press equivalent

---

## Specialized Gestures

### Volume Control
- **Horizontal drag from left to right:** Increase volume
- **Horizontal drag from right to left:** Decrease volume
- **From outside app:** Swipe from screen edge for system volume

### Progress Seek
- **Tap:** Instant seek to tapped position
- **Hold and drag:** Fine control seek

### Album Art Gallery
- **Pinch out:** Zoom in on album art
- **Pinch in:** Zoom out
- **Drag:** Pan through zoomed image

---

## Long Press Actions

Long press (500ms) on UI elements triggers context menus:

#### Album Art (Long Press)
- Share: Share via Bluetooth / Messaging
- Favorite: Mark as favorite
- Set wallpaper: Set as home screen (if supported)
- Details: Show track/artist/album info

#### Play/Pause (Long Press)
- Shuffle: Enable/disable shuffle mode
- Repeat: Cycle through repeat modes (off/one/all)
- Sleep timer: Set auto-shutdown (15/30/60/90 min)

#### Volume (Long Press)
- Mute toggle
- System volume controls

---

## Touch Calibration

### Adjusting Touch Sensitivity

Touchscreen calibration may be required for accurate input:

```bash
# Run calibration tool (if available)
calibrate-screen

# Or via Python script
calibrate.py
```

### Common Touch Issues

| Issue | Cause | Fix |
|-------|-------|-----|
| Taps not registering | Touchscreen driver not loading | Check `/dev/input/eventX` exists |
| Overly sensitive | Screen calibration off | Calibrate touch | |
| Touch lag | Poor hardware or X11 config | Adjust X11 touch settings |
| Unresponsive areas | Screen cracks | Physical repair needed |

---

## Multi-Touch

### Supported Multi-Touch Gestures

- **Two-finger tap:** Right-click equivalent
- **Two-finger swipe:** Scroll through lists
- **Three-finger swipe:** Minimize/maximize UI
- **Three-finger tap:** Show system menu (home, recent apps)

### Multi-Touch in UI

#### Queue Selection
- **Multi-select:** Tap and hold one item, then tap others for multi-select mode
- **Actions:** Play, Pause, Delete, Share

#### Art Gallery Navigation
- **Two-finger swipe:** Pan through album art grid
- **Pinch to zoom:** Focus on specific album art

---

## Cross-Distribution Touch Support

### Raspberry Pi OS (Desktop)

With Wayland (Bookworm default):

```ini
# /boot/firmware/config.txt
# Enable touchscreen
lte_vblank_sync=1
dispmanx_display0_width=480
dispmanx_display0_height=320
touch_display=0
```

### Arch Linux

```bash
# Install xorg-xinput for calibration tools
sudo pacman -S xorg-xinput

# Check touch devices
xinput --list
```

### Fedora

```bash
# Touchscreen should work out of the box
# Verify with xinput --list
```

---

## Testing Touch Input

### Manual Testing

1. **Open calibration tool** (`calibrate-screen`)
2. **Follow on-screen prompts**
3. **Test all UI elements**
4. **Verify gestures work correctly**

### Automated Testing

```python
# Python script for touch testing
from core.ui import TouchTester

tester = TouchTester()
tester.test_tap(target=play_pause_button)
tester.test_swipe(direction='left')
tester.test_drag(volume_slider, 0.75)
tester.test_long_press(album_art, 'favorites_menu')
```

---

## Troubleshooting Touch Issues

| Symptom | Diagnosis | Solution |
|---------|-----------|----------|
| Taps not working | Touch driver missing | Install touch firmware |
| Ghost touches | Screen interference | Clean screen surface |
| Unresponsive areas | Screen damage | Repair/replace screen |
| Laggy response | X11 config issues | Adjust X11 polling rate |

---

## Touch Performance Optimization

### Battery Considerations

For portable Pi Zero deployments:
- **Touch polling:** 30Hz minimum, 60Hz optimal
- **Screen brightness:** Auto-dim after 30 seconds inactivity
- **Touch filtering:** Smooth rapid taps to prevent false positives

### Performance Settings

In `/etc/mpd.conf`:

```ini
# Limit MPD to lower CPU usage
# (MPD handles audio decoding; Python app remains lightweight)
```

In `config.json`:

```json
{
  "touch_sensitivity": 0.8,
  "gesture_sensitivity": "medium",
  "double_tap_time_ms": 250,
  "long_press_time_ms": 500
}
```

---

## Future Enhancements

1. **Multi-touch gestures for quick actions**
2. **Swipe gestures for playlist navigation**
3. **Pinch zoom for album art detail**
4. **Haptic feedback for button presses**
5. **Voice command overlay**

---

## Testing Touch Features

### Manual Test

1. Open app on touchscreen device
2. Test all touch gestures described above
3. Verify smooth, responsive interaction
4. Test multi-touch where supported

### Automated Test

```bash
# Run touch test suite
python3 -m pytest tests/test_touch.py -v
```