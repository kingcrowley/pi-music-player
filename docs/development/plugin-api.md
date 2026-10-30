# Plugin API Reference

Complete specification for building plugins for the Low-Resource Linux Music Player.

> **Version:** 1.0.0
> **Target:** Plugin developers who want to extend the core music player

---

## Table of Contents

1. [Plugin Architecture Overview](#plugin-architecture-overview)
2. [Plugin Types](#plugin-types)
3. [Plugin Manifest (`config.json`)](#plugin-manifest-configjson)
4. [Plugin Base Class](#plugin-base-class)
5. [Plugin Hooks and Events](#plugin-hooks-and-events)
6. [Capabilities](#capabilities)
7. [Plugin Manager API](#plugin-manager-api)
8. [Plugin Lifecycle](#plugin-lifecycle)
9. [Best Practices](#best-practices)
10. [Example Plugins](#example-plugins)

---

## Plugin Architecture Overview

The music player uses a **plugin-first architecture**. Every major feature is implemented as a plugin:

```
Core Engine (Python 3)
  ├── Plugin Manager (discovers, loads, unloads plugins)
  ├── Audio Backend Plugins (ALSA, PipeWire, PulseAudio)
  ├── Feature Plugins (Sleep timer, Equalizer, Stats)
  ├── UI Widget Plugins (Progress bar, Volume slider)
  ├── Data Source Plugins (Local files, SMB, Cloud)
  └── Integration Plugins (Bluetooth, Web API, System tray)
```

Plugins communicate through:
- **Direct API calls** to the core engine
- **Event hooks** (`on_song_change`, `on_volume_change`, etc.)
- **Capability registry** (query which plugins provide which features)

---

## Plugin Types

| Type | Capabilities | Example |
|------|-------------|---------|
| `audio-backend` | audio-output, volume-control | ALSA, PipeWire |
| `feature` | sleep-timer, equalizer, repeat-mode | Sleep timer |
| `ui-widget` | progress-bar, volume-slider, album-art | Progress bar |
| `data-source` | music-library, playlist | Local filesystem |
| `integration` | web-api, bluetooth, system-tray | Remote control API |

A plugin can declare multiple types/capabilities.

---

## Plugin Manifest (`config.json`)

Every plugin directory must contain a `config.json` manifest:

```json
{
  "plugin_id": "alsa-audio",
  "name": "ALSA Audio Backend",
  "version": "1.0.0",
  "description": "Plays audio using ALSA audio system",
  "author": "Your Name",
  "email": "you@example.com",
  "license": "MIT",
  "homepage": "https://github.com/you/alsa-audio-plugin",
  "required_core_version": "1.0.0",
  "type": "audio-backend",
  "capabilities": [
    "audio-output",
    "volume-control"
  ],
  "dependencies": [],
  "settings_schema": {
    "device": {
      "type": "string",
      "default": "hw:0,0",
      "description": "ALSA device path"
    },
    "buffer_size": {
      "type": "integer",
      "default": 512,
      "min": 64,
      "max": 4096,
      "description": "Audio buffer size"
    }
  },
  "auto_load": true
}
```

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `plugin_id` | string | Yes | Unique identifier (lowercase, hyphens) |
| `name` | string | Yes | Human-readable plugin name |
| `version` | string | Yes | Semantic versioning (major.minor.patch) |
| `description` | string | Yes | One-sentence description |
| `author` | string | Yes | Plugin author name |
| `license` | string | Yes | License (MIT, GPL-3.0, Apache-2.0, etc.) |
| `type` | string | Yes | One of: audio-backend, feature, ui-widget, data-source, integration |
| `capabilities` | array | Yes | List of capability strings provided |
| `required_core_version` | string | Yes | Minimum core engine version |
| `dependencies` | array | No | List of plugin_ids this plugin depends on |
| `settings_schema` | object | No | JSON schema for plugin configuration |
| `auto_load` | boolean | No | Auto-load on startup (default: true) |

---

## Plugin Base Class

All plugins must implement a class inheriting from the base plugin:

```python
class MusicPlayerPlugin:
    def __init__(self, config):
        """Initialize plugin with configuration dict from config.json"""
        self.config = config
        self.name = config.get("name", "Unknown Plugin")
        self.version = config.get("version", "0.0.1")
        self.core = None  # Set by PluginManager during initialize()
    
    def initialize(self, core):
        """Called when plugin is loaded by PluginManager.
        
        Args:
            core: Reference to core MusicPlayer instance
            
        Returns:
            bool: True if initialization succeeded
        """
        self.core = core
        return True
    
    def shutdown(self):
        """Called when plugin is unloaded. Clean up resources here."""
        pass
    
    def get_capabilities(self):
        """Return list of capability strings this plugin provides.
        
        Returns:
            list[str]: Capabilities like ["audio-output", "volume-control"]
        """
        return []
    
    def handle_command(self, command, args=None):
        """Handle commands from core or UI.
        
        Args:
            command: String command name
            args: Optional dict of arguments
            
        Returns:
            Any: Command-specific result, or None if command not handled
        """
        return None
    
    def get_settings(self):
        """Return current plugin settings.
        
        Returns:
            dict: Current configuration values
        """
        return self.config.get("settings_schema", {})
    
    def update_settings(self, settings):
        """Update plugin settings at runtime.
        
        Args:
            settings: Dict of new setting values
        """
        pass
```

---

## Plugin Hooks and Events

Plugins can register handlers for core events:

| Hook | Triggered When | Args | Example Use |
|------|---------------|------|-------------|
| `on_song_change` | New track starts playing | `song_info` dict | Update UI, record stats |
| `on_playback_state` | Play/pause/stop changes | `state` string | Sleep timer logic |
| `on_volume_change` | Volume adjusted | `volume` int | UI volume slider update |
| `on_error` | Error occurs | `error` dict | Error handling, logging |
| `on_startup` | Core starts up | None | Initialize plugin state |
| `on_shutdown` | Core shuts down | None | Clean up resources |
| `on_user_interaction` | User touches UI | `interaction` dict | Analytics, telemetry |

### Registering Hooks

```python
class MyPlugin(MusicPlayerPlugin):
    def initialize(self, core):
        self.core = core
        core.register_hook("on_song_change", self.on_song_change)
        core.register_hook("on_playback_state", self.on_playback_state)
    
    def on_song_change(self, song_info):
        print(f"Now playing: {song_info.get('title')}")
    
    def on_playback_state(self, state):
        if state == "play":
            print("Playback started")
```

---

## Capabilities

Capabilities are strings that describe what a plugin can do. The core engine queries capabilities to route commands:

| Capability | Description | Provided By |
|------------|-------------|-------------|
| `audio-output` | Plays audio to speakers/headphones | ALSA, PipeWire plugins |
| `volume-control` | Adjusts system/software volume | ALSA, PipeWire plugins |
| `sleep-timer` | Auto-stop playback after delay | Sleep timer plugin |
| `equalizer` | Frequency band adjustments | Equalizer plugin |
| `progress-bar` | Displays playback progress | UI widget plugin |
| `volume-slider` | Volume adjustment UI | UI widget plugin |
| `music-library` | Provides track listings | Local filesystem plugin |
| `web-api` | HTTP API for remote control | Remote control plugin |
| `bluetooth` | Bluetooth device control | Bluetooth integration plugin |

### Querying Capabilities

```python
# Get all plugins that provide audio output
audio_plugins = core.plugin_manager.get_plugins_with_capability("audio-output")

# Use first available
if audio_plugins:
    audio_plugins[0].handle_command("play", {"path": "/music/track.flac"})
```

---

## Plugin Manager API

The PluginManager handles discovery, loading, and communication:

### Methods

| Method | Description |
|--------|-------------|
| `load_plugins(plugin_dir)` | Discover and load all plugins from directory |
| `load_plugin(category_path, plugin_dir_name)` | Load a single plugin |
| `unload_plugin(plugin_id)` | Unload and cleanup a plugin |
| `get_plugin(plugin_id)` | Get plugin instance by ID |
| `get_plugins_with_capability(capability)` | List plugins providing a capability |
| `get_all_plugins()` | List all loaded plugins |
| `register_hook(event_name, callback)` | Register event handler |
| `trigger_hook(event_name, args)` | Trigger all handlers for an event |

### Example Usage

```python
from core.plugin_manager import PluginManager

manager = PluginManager()
manager.load_plugins("plugins/")

# Get ALSA audio backend
alsa_plugin = manager.get_plugin("alsa-audio")

# Play a track
alsa_plugin.handle_command("play", {"path": "/music/track.flac"})

# Get all plugins that can control volume
volume_plugins = manager.get_plugins_with_capability("volume-control")
for plugin in volume_plugins:
    plugin.handle_command("set_volume", {"level": 75})
```

---

## Plugin Lifecycle

```
Discovery → Loading → Initialization → Active → Shutdown → Cleanup
```

### Lifecycle Methods

| Phase | Method | Called By |
|-------|--------|-----------|
| Discovery | (none) | Plugin Manager scans directories |
| Loading | `__init__()` | When plugin module is imported |
| Initialization | `initialize(core)` | After load, before use |
| Active | `handle_command()` | During normal operation |
| Shutdown | `shutdown()` | When unloading or core exits |
| Cleanup | (none) | After shutdown completes |

### Error Handling

Plugins should never crash the core engine:

```python
def handle_command(self, command, args=None):
    try:
        if command == "play":
            return self.play(args["path"])
    except Exception as e:
        self.core.handle_error("plugin-error", {
            "plugin": self.name,
            "command": command,
            "error": str(e)
        })
        return None
```

---

## Best Practices

### 1. Never Block the Main Thread

Plugins should use threads for long operations:

```python
import threading

class MyPlugin(MusicPlayerPlugin):
    def download_artwork(self, url):
        def _download():
            # Long-running download
            pass
        thread = threading.Thread(target=_download)
        thread.daemon = True
        thread.start()
```

### 2. Handle Configuration Gracefully

```python
def update_settings(self, settings):
    if "device" in settings:
        self.device = settings["device"]
        self.reinitialize_audio()
```

### 3. Declare All Capabilities

```python
def get_capabilities(self):
    return ["audio-output", "volume-control", "seek"]
```

### 4. Document Your Plugin

Include a `README.md` in your plugin directory:

```markdown
# My Plugin

Description of what this plugin does.

## Installation

Copy this directory to `plugins/my-plugin/`.

## Configuration

Edit `config.json` to customize settings.

## License

MIT
```

---

## Example Plugins

### ALSA Audio Backend

```python
# plugins/audio-backends/alsa/alsa.py
import subprocess

class MusicPlayerPlugin:
    def __init__(self, config):
        self.config = config
        self.device = config.get("settings_schema", {}).get("device", "hw:0,0")
    
    def initialize(self, core):
        self.core = core
        return True
    
    def shutdown(self):
        pass
    
    def get_capabilities(self):
        return ["audio-output", "volume-control"]
    
    def handle_command(self, command, args=None):
        if command == "play":
            path = args.get("path")
            if path:
                subprocess.Popen(["aplay", "-D", self.device, path])
                return True
        elif command == "stop":
            subprocess.run(["killall", "aplay"])
            return True
        elif command == "set_volume":
            level = args.get("level", 50)
            subprocess.run(["amixer", "set", "PCM", f"{level}%"])
            return True
        return None
```

### Sleep Timer Feature

```python
# plugins/features/sleep-timer/sleep_timer.py
import threading
import time

class MusicPlayerPlugin:
    def __init__(self, config):
        self.config = config
        self.timer_active = False
        self.timer_thread = None
    
    def initialize(self, core):
        self.core = core
        return True
    
    def get_capabilities(self):
        return ["sleep-timer"]
    
    def handle_command(self, command, args=None):
        if command == "start_timer":
            minutes = args.get("minutes", 30)
            self.start_timer(minutes)
            return True
        elif command == "stop_timer":
            self.stop_timer()
            return True
        return None
    
    def start_timer(self, minutes):
        self.stop_timer()  # Cancel existing
        self.timer_active = True
        
        def _timer():
            time.sleep(minutes * 60)
            if self.timer_active:
                self.core.player.stop()
                self.timer_active = False
        
        self.timer_thread = threading.Thread(target=_timer, daemon=True)
        self.timer_thread.start()
    
    def stop_timer(self):
        self.timer_active = False
```

---

## Publishing Plugins

To share your plugin with the community:

1. **Create a GitHub repo** named `your-plugin-name`
2. **Include** `config.json`, plugin code, `README.md`, `LICENSE`
3. **Tag releases** with semantic versioning
4. **Add to the plugin registry** (see `docs/development/release-process.md`)

Users can install via:

```bash
git clone https://github.com/yourusername/your-plugin.git plugins/your-plugin
python3 -m plugins load your-plugin
```
