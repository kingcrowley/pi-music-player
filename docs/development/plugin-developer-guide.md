# Plugin Developer Guide

Step-by-step guide for building, testing, and publishing plugins for the Low-Resource Linux Music Player.

> **Estimated reading time:** 20 minutes
> **Prerequisites:** Python 3.8+, basic understanding of Python, access to a Linux terminal

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Understanding the Plugin Directory Structure](#understanding-the-plugin-directory-structure)
3. [Step 1: Create a New Plugin](#step-1-create-a-new-plugin)
4. [Step 2: Write Your Plugin Code](#step-2-write-your-plugin-code)
5. [Step 3: Define the Plugin Manifest](#step-3-define-the-plugin-manifest)
6. [Step 4: Load and Test Your Plugin](#step-4-load-and-test-your-plugin)
7. [Step 5: Add Settings UI](#step-5-add-settings-ui)
8. [Step 6: Handle Events](#step-6-handle-events)
9. [Step 7: Package and Publish](#step-7-package-and-publish)
10. [Common Pitfalls](#common-pitfalls)
11. [Next Steps](#next-steps)

---

## Prerequisites

### System Requirements

| Requirement | Minimum |
|-------------|---------|
| Python | 3.8+ |
| Operating System | Any Linux distro (Debian, Ubuntu, Fedora, Arch, etc.) |
| Disk Space | 50 MB for core player + plugin space |
| Memory | 512 MB RAM minimum (works on Pi Zero 2 W) |

### Install Core Player

If you haven't already:

```bash
cd /path/to/music-player
pip3 install -r requirements.txt

# Or with virtual environment (recommended for development):
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Run the Core Player

```bash
python3 main.py
```

---

## Understanding the Plugin Directory Structure

Plugins live in the `plugins/` directory, organized by **category**:

```
plugins/
├── audio-backends/        # Audio output backends
│   ├── alsa/
│   │   ├── __init__.py
│   │   └── config.json
│   └── pipewire/
│       ├── __init__.py
│       └── config.json
├── features/              # Standalone features
│   └── sleep-timer/
│       ├── __init__.py
│       └── config.json
├── ui-widgets/            # Reusable UI components
│   └── progress-bar/
│       ├── __init__.py
│       └── config.json
└── data-sources/          # Music library sources
    └── local-fs/
        ├── __init__.py
        └── config.json
```

Each plugin has:
- **`__init__.py`** — Main plugin class file
- **`config.json`** — Plugin manifest/metadata

> 💡 **Tip:** Plugin names use lowercase with hyphens. Directory names match `plugin_id` from `config.json`.

---

## Step 1: Create a New Plugin

We'll build an **"Announcement Plugin"** that prints the artist name whenever a new song starts.

### Create the Plugin Directory

```bash
# Create your plugin directory
mkdir -p plugins/features/announcer

# Or for any other category:
# mkdir -p plugins/[category]/[plugin-name]
```

### Directory Name

Choose a descriptive name:
- ✅ `announcer`
- ✅ `crossfade-tracks`
- ❌ `myplugin`, `newthing`, `plugin1`

---

## Step 2: Write Your Plugin Code

Create `plugins/features/announcer/__init__.py`:

```python
"""
Announcement Plugin
Prints announcement messages when songs change.
"""

class MusicPlayerPlugin:
    def __init__(self, config):
        """Initialize with plugin config from config.json."""
        self.config = config
        self.name = config.get("name", "Announcer")
        self.version = config.get("version", "1.0.0")
        self.core = None
        # Get plugin-specific settings (with defaults)
        self.announcement_template = config.get("settings_schema", {}).get(
            "announcement_template", {}
        ).get("default", "Now playing: {artist} - {title}")
        self.verbose = False  # Will be set from settings
    
    def initialize(self, core):
        """Called when plugin is loaded by PluginManager."""
        self.core = core
        
        # Register event hooks
        self.core.register_hook("on_song_change", self.on_song_change)
        self.core.register_hook("on_playback_state", self.on_playback_state)
        self.core.register_hook("on_startup", self.on_startup)
        self.core.register_hook("on_shutdown", self.on_shutdown)
        
        # Log successful initialization
        self.core.log(f"{self.name} v{self.version} loaded successfully")
        return True
    
    def shutdown(self):
        """Cleanup when plugin is unloaded."""
        self.core.log(f"{self.name} shutting down")
    
    def get_capabilities(self):
        """Declare what capabilities this plugin provides."""
        return ["announcement"]
    
    def handle_command(self, command, args=None):
        """Handle commands from core engine."""
        if command == "set_verbose":
            self.verbose = args.get("verbose", False)
            return True
        elif command == "announce":
            message = args.get("message", "Announcing")
            self.do_announcement({"message": message})
            return True
        return None
    
    # ----------------------
    # Event Handlers
    # ----------------------
    
    def on_startup(self):
        """Called when core engine starts up."""
        print(f"[Announcer] Plugin loaded and ready!")
    
    def on_shutdown(self):
        """Called when core engine shuts down."""
        print(f"[Announcer] Goodbye!")
    
    def on_playback_state(self, state):
        """Handle playback state changes."""
        if self.verbose:
            print(f"[Announcer] Playback state changed to: {state}")
    
    def on_song_change(self, song_info):
        """Handle new song events."""
        # Extract song info (defensive programming for missing fields)
        artist = song_info.get("artist", "Unknown Artist")
        title = song_info.get("title", "Unknown Title")
        album = song_info.get("album", "")
        
        # Format message
        if album:
            message = f"🎵 Now playing: {artist} — {title} (from {album})"
        else:
            message = f"🎵 Now playing: {artist} — {title}"
        
        # Announce
        self.do_announcement({"message": message})
    
    # ----------------------
    # Plugin Methods
    # ----------------------
    
    def do_announcement(self, data):
        """Print an announcement message."""
        message = data.get("message", "")
        if message:
            print(f"[Announcer] {message}")

    def get_settings(self):
        """Return current settings."""
        return {
            "announcement_template": self.announcement_template,
            "verbose": self.verbose
        }
    
    def update_settings(self, settings):
        """Update settings from core engine."""
        if "announcement_template" in settings:
            self.announcement_template = settings["announcement_template"]
        if "verbose" in settings:
            self.verbose = settings["verbose"]
```

---

## Step 3: Define the Plugin Manifest

Create `plugins/features/announcer/config.json`:

```json
{
  "plugin_id": "announcer",
  "name": "Track Announcer",
  "version": "1.0.0",
  "description": "Prints announcements when songs change",
  "author": "Your Name",
  "email": "you@example.com",
  "license": "MIT",
  "homepage": "https://github.com/yourusername/track-announcer",
  "required_core_version": "1.0.0",
  "type": "feature",
  "capabilities": [
    "announcement"
  ],
  "dependencies": [],
  "settings_schema": {
    "announcement_template": {
      "type": "string",
      "default": "Now playing: {artist} - {title}",
      "description": "Message template for announcements",
      "required": false
    },
    "verbose": {
      "type": "boolean",
      "default": false,
      "description": "Include verbose logging",
      "required": false
    }
  },
  "auto_load": true
}
```

> 🔍 **Important:** Make sure `plugin_id` matches your directory name (`announcer`).

---

## Step 4: Load and Test Your Plugin

### Test 1: Auto-Discovery

If you placed your plugin in `plugins/features/announcer/`, it will be auto-discovered on startup.

Run the core player:

```bash
cd /path/to/music-player
python3 main.py
```

**Expected output:**
```
[Announcer] Plugin loaded and ready!
```

### Test 2: Manual Loading

Test your plugin without running the full player:

```bash
python3 -c "
import json
from core.plugin_manager import PluginManager

# Create plugin manager
manager = PluginManager()

# Load your plugin manually
with open('plugins/features/announcer/config.json') as f:
    config = json.load(f)

# Simulate core for testing
class MockCore:
    hooks = {}
    def register_hook(self, event, callback):
        self.hooks.setdefault(event, []).append(callback)
    def trigger_hook(self, event, args=None):
        for callback in self.hooks.get(event, []):
            callback(args or {})
    def log(self, msg):
        print(f'[CORE] {msg}')

# Create mock core
mock_core = MockCore()

# Initialize plugin
from plugins.features.announcer import MusicPlayerPlugin
plugin = MusicPlayerPlugin(config)
plugin.initialize(mock_core)

# Test song change event
mock_core.trigger_hook('on_song_change', {
    'artist': 'Pink Floyd',
    'title': 'Comfortably Numb',
    'album': 'The Wall'
})

# Test command
plugin.handle_command('set_verbose', {'verbose': True})
mock_core.trigger_hook('on_playback_state', 'play')

plugin.shutdown()
"
```

**Expected output:**
```
[CORE] Track Announcer v1.0.0 loaded successfully
[Announcer] Plugin loaded and ready!
🎵 Now playing: Pink Floyd — Comfortably Numb (from The Wall)
[Announcer] Playback state changed to: play
[Announcer] Goodbye!
```

### Test 3: Check Plugin List

```bash
python3 -c "
from core.plugin_manager import PluginManager
import json

manager = PluginManager()
manager.load_plugins('plugins/')

print('Loaded plugins:')
for plugin in manager.get_all_plugins():
    print(f'  - {plugin.name} (v{plugin.version})')

print()
print('Capabilities:')
for cap in ['announcement', 'audio-output']:
    plugins = manager.get_plugins_with_capability(cap)
    print(f'  {cap}: {[p.name for p in plugins]}')
"
```

---

## Step 5: Add Settings UI

Your plugin can be controlled from the Settings screen if it declares settings:

```python
# In your plugin class
def get_settings(self):
    """Return current settings for display in UI."""
    return {
        "verbose": self.verbose,
        "announcement_template": self.announcement_template
    }

def update_settings(self, settings):
    """Apply settings changes from UI."""
    if "verbose" in settings:
        self.verbose = settings["verbose"]
        print(f"[Announcer] Verbose mode: {self.verbose}")
    if "announcement_template" in settings:
        self.announcement_template = settings["announcement_template"]
```

### Settings Schema

The UI will auto-generate controls based on your `config.json` `settings_schema`:

```json
"settings_schema": {
  "verbose": {
    "type": "boolean",
    "default": false
  },
  "min_volume": {
    "type": "integer",
    "default": 20,
    "min": 0,
    "max": 100
  },
  "mode": {
    "type": "string",
    "default": "simple",
    "options": ["simple", "verbose", "minimal"]
  }
}
```

Supported UI types:
- `string` → Text input
- `integer` → Number slider
- `boolean` → Toggle switch
- `string` with `options` → Dropdown selector

---

## Step 6: Handle Events

Your plugin hooks into core events. Here's the full list:

| Event | Triggered By | Args |
|-------|-------------|------|
| `on_song_change` | Playback starts new track | `song_info` dict |
| `on_playback_state` | Play/pause/stop | `state` string |
| `on_volume_change` | Volume adjusted | `volume` int (0-100) |
| `on_error` | Error in core or plugin | `error` dict |
| `on_startup` | Core engine starts | None |
| `on_shutdown` | Core engine exits | None |
| `on_user_interaction` | User interacts with UI | `interaction` dict |

### Example: Reacting to Volume Changes

```python
def on_volume_change(self, volume):
    """Called when volume changes."""
    print(f"[Announcer] Volume is now {volume}%")
    if self.verbose:
        if volume > 80:
            print("[Announcer] Warning: Volume is very loud!")
        elif volume < 20:
            print("[Announcer] Tip: Volume is low")
```

---

## Step 7: Package and Publish

### Step 7.1: Add Documentation

Create `README.md` in your plugin directory:

```markdown
# Track Announcer Plugin

Print announcements when songs change.

## Installation

1. Clone this repo:
   ```bash
   git clone https://github.com/yourusername/track-announcer.git
   ```
2. Copy to plugins directory:
   ```bash
   cp -r track-announcer /path/to/music-player/plugins/features/announcer/
   ```
3. Restart the player

## Configuration

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `verbose` | boolean | false | Include verbose logging |
| `announcement_template` | string | See default | Message format template |

## License

MIT
```

### Step 7.2: Create GitHub Repository

1. Go to https://github.com/new
2. Repository name: `track-announcer` (or your-plugin-name)
3. Description: A plugin for the Low-Resource Linux Music Player
4. Public ✓
5. Initialize this repository with: **None** (don't add README, .gitignore, or license)
6. Click **Create repository**

### Step 7.3: Publish

```bash
cd /path/to/your/plugin
git init
git add .
git commit -m "feat: initial plugin implementation

- Announce song changes with configurable template
- Verbose logging mode
- Event hooks for playback state changes"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/track-announcer.git
git push -u origin main
```

### Step 7.4: Tag a Release

```bash
git tag -a v1.0.0 -m "First release"
git push origin v1.0.0
```

---

## Common Pitfalls

### ❌ Plugin Not Loading

**Checklist:**
1. ✅ Directory name matches `plugin_id` in `config.json`
2. ✅ `config.json` is valid JSON
3. ✅ Class inherits from `MusicPlayerPlugin`
4. ✅ `initialize(self, core)` returns `True`
5. ✅ File is named `__init__.py`

**Debug:**
```python
# Check for errors
python3 -c "
from core.plugin_manager import PluginManager
manager = PluginManager()
manager.load_plugins('plugins/')
for p in manager.get_all_plugins():
    print(p.name, p.version, p.get_capabilities())
"
```

### ❌ Event Handler Not Called

**Checklist:**
1. ✅ Registered hook in `initialize()`: `self.core.register_hook("on_song_change", self.on_song_change)`
2. ✅ Method signature matches: `def on_song_change(self, song_info):`
3. ✅ Core is not crashing before the event

### ❌ Settings Not Saving

**Checklist:**
1. ✅ Settings declared in `config.json` under `settings_schema`
2. ✅ `get_settings()` returns dict with correct keys
3. ✅ `update_settings(settings)` handles all keys

---

## Next Steps

### Build More Plugins

| Plugin | Category | Difficulty |
|--------|----------|-----------|
| **Visualizer** | ui-widget | Easy |
| **Queue Manager** | feature | Medium |
| **Web API** | integration | Medium |
| **Bluetooth Control** | integration | Hard |
| **Equalizer** | feature | Medium |

### Learn More

- **[Plugin API Reference](plugin-api.md)** — Full API documentation
- **[Plugin Lifecycle](plugin-api.md#plugin-lifecycle)** — Loading/unloading details
- **[Core Engine Events](plugin-api.md#plugin-hooks-and-events)** — All available hooks

### Get Help

- Check [`docs/troubleshooting/README.md`](../troubleshooting/README.md)
- Open an issue on GitHub: https://github.com/your-repo/issues
- Ask in the development Discord/Twitch
