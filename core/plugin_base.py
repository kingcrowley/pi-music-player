"""Plugin system foundation for Pi Zero 2 W Music Player.

Defines the abstract base class for all plugins and the plugin manifest schema.
Plugins communicate with the core engine through capabilities, event hooks,
and direct API access.
"""

import json
import logging
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any as CoreEngine, TYPE_CHECKING

if TYPE_CHECKING:
    # Forward reference for type hints only - not imported at runtime
    from typing import Any as CoreEngine

logger = logging.getLogger(__name__)


class MusicPlayerPlugin(ABC):
    """Abstract base class for all music player plugins.

    Plugins are discovered by scanning plugin directories for config.json
    manifest files. Each plugin instantiates a class derived from this base
    class and implements the required methods.
    """

    def __init__(self, config: Dict[str, Any]):
        """Initialize plugin with configuration from manifest.

        Args:
            config: Dict loaded from plugin's config.json manifest.
        """
        self.config = config
        self.name = config.get("name", "Unknown Plugin")
        self.version = config.get("version", "0.0.1")
        self.core: Optional["CoreEngine"] = None  # Set during initialize()
        self._initialized = False

    @abstractmethod
    def initialize(self, core: "CoreEngine") -> bool:
        """Initialize plugin with core engine reference.

        Called once by PluginManager after loading. Register hooks,
        register capabilities, and set up resources here.

        Args:
            core: Core engine instance providing access to player, UI, stats.

        Returns:
            bool: True if initialization succeeded, False otherwise.
        """
        return False

    def shutdown(self) -> None:
        """Shutdown plugin gracefully.

        Called when plugin is unloaded or core engine exits. Clean up
        resources, unregister hooks, stop background threads here.
        Default implementation does nothing.
        """
        pass

    def get_capabilities(self) -> List[str]:
        """Return list of capability strings this plugin provides.

        Capabilities are used by core engine to route commands to plugins.
        Examples: "audio-output", "volume-control", "sleep-timer",
        "statistics", "recommendations".

        Returns:
            List[str]: Capability names this plugin supports.
        """
        return []

    def handle_command(self, command: str, args: Optional[Dict[str, Any]] = None) -> Any:
        """Handle commands routed from core engine.

        Args:
            command: Command string (e.g., "play", "pause", "set_volume").
            args: Optional dict of command arguments.

        Returns:
            Any: Command-specific result, or None if command not handled.
        """
        return None

    def get_settings(self) -> Dict[str, Any]:
        """Return current plugin settings as a dictionary.

        Returns:
            Dict[str, Any]: Current plugin settings/values.
        """
        return {}

    def update_settings(self, settings: Dict[str, Any]) -> None:
        """Update plugin settings at runtime.

        Args:
            settings: Dict of new setting values to apply.
        """
        pass

    def register_hook(self, event_name: str, callback: Callable) -> None:
        """Register an event hook callback on the core engine.

        Convenience wrapper around core.register_hook().

        Args:
            event_name: Event name (e.g., "on_song_change", "on_playback_state").
            callback: Function to call when event fires.
        """
        if self.core and hasattr(self.core, "register_hook"):
            self.core.register_hook(event_name, callback)

    def trigger_hook(self, event_name: str, *args, **kwargs) -> None:
        """Trigger an event hook on the core engine.

        Args:
            event_name: Event name to trigger.
            *args: Positional arguments for hook callbacks.
            **kwargs: Keyword arguments for hook callbacks.
        """
        if self.core and hasattr(self.core, "trigger_hook"):
            self.core.trigger_hook(event_name, *args, **kwargs)

    def get_registered_hooks(self) -> Dict[str, List[Callable]]:
        """Return hooks registered by this plugin.

        Called by PluginManager during load to register declared hooks
        with the manager. Returns an empty dict by default since plugins
        must register hooks via register_hook().

        Returns:
            Dict mapping event name to list of callbacks.
        """
        return {event: list(cbs) for event, cbs in getattr(self, "_plugin_hooks", {}).items()}

    @property
    def initialized(self) -> bool:
        """Return whether plugin has been initialized."""
        return self._initialized

    def _set_initialized(self, value: bool) -> None:
        """Set initialization flag (used by PluginManager internally)."""
        self._initialized = value


# Plugin manifest schema
PLUGIN_MANIFEST_SCHEMA = {
    "type": "object",
    "required": ["plugin_id", "name", "version", "type"],
    "properties": {
        "plugin_id": {"type": "string", "description": "Unique identifier (lowercase, hyphens only)"},
        "name": {"type": "string", "description": "Human-readable plugin name"},
        "version": {"type": "string", "description": "Semantic version (major.minor.patch)"},
        "description": {"type": "string", "description": "One-sentence description"},
        "author": {"type": "string", "description": "Plugin author name"},
        "email": {"type": "string", "description": "Plugin author email"},
        "license": {"type": "string", "description": "License (MIT, GPL-3.0, etc.)"},
        "homepage": {"type": "string", "description": "Plugin homepage URL"},
        "type": {
            "type": "string",
            "enum": ["audio-backend", "feature", "ui-widget", "data-source", "integration"],
            "description": "Plugin type category",
        },
        "capabilities": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of capability strings provided by this plugin",
        },
        "required_core_version": {"type": "string", "description": "Minimum core engine version"},
        "dependencies": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of plugin_id dependencies",
        },
        "settings_schema": {
            "type": "object",
            "description": "JSON schema for plugin configuration settings",
        },
        "auto_load": {"type": "boolean", "description": "Auto-load on startup (default: true)"},
    },
}


class PluginManifest:
    """Validates and holds plugin manifest data."""

    def __init__(self, data: Dict[str, Any]):
        """Initialize manifest from config dict.

        Args:
            data: Dict loaded from plugin's config.json manifest file.
        """
        self.data = data
        self.plugin_id = data.get("plugin_id", "")
        self.name = data.get("name", "Unknown Plugin")
        self.version = data.get("version", "0.0.1")
        self.description = data.get("description", "")
        self.author = data.get("author", "")
        self.email = data.get("email", "")
        self.license = data.get("license", "MIT")
        self.homepage = data.get("homepage", "")
        self.type = data.get("type", "feature")
        self.capabilities = data.get("capabilities", [])
        self.required_core_version = data.get("required_core_version", "1.0.0")
        self.dependencies = data.get("dependencies", [])
        self.settings_schema = data.get("settings_schema", {})
        self.auto_load = data.get("auto_load", True)

    def is_valid(self) -> bool:
        """Check if manifest has all required fields."""
        required = ["plugin_id", "name", "version", "type"]
        return all(bool(self.data.get(k)) for k in required)

    def __str__(self) -> str:
        return f"PluginManifest({self.plugin_id} v{self.version})"

    def __repr__(self) -> str:
        return self.__str__()


def load_manifest(manifest_path: str) -> Optional[PluginManifest]:
    """Load and validate a plugin manifest from a JSON file.

    Args:
        manifest_path: Path to config.json manifest file.

    Returns:
        PluginManifest instance or None if loading fails.
    """
    try:
        with open(manifest_path, "r") as f:
            data = json.load(f)
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError, OSError) as e:
        logger.warning("Failed to load plugin manifest from %s: %s", manifest_path, e)
        return None

    if not isinstance(data, dict):
        logger.warning("Invalid plugin manifest at %s: expected a JSON object", manifest_path)
        return None

    manifest = PluginManifest(data)
    if not manifest.is_valid():
        logger.warning("Invalid plugin manifest at %s: missing required fields", manifest_path)
        return None

    return manifest


def load_plugin_class(module_path: str, class_name: str = "MusicPlayerPlugin"):
    """Dynamically load a plugin class from a module.

    Args:
        module_path: Dotted module path or file path.
        class_name: Class name to instantiate (default: MusicPlayerPlugin).

    Returns:
        Plugin class or None if loading fails.
    """
    try:
        module = __import__(module_path, fromlist=[class_name])
        return getattr(module, class_name)
    except (ImportError, AttributeError, Exception) as e:
        logger.warning("Failed to load plugin class %s from %s: %s", class_name, module_path, e)
        return None


__all__ = [
    "MusicPlayerPlugin",
    "PluginManifest",
    "PLUGIN_MANIFEST_SCHEMA",
    "load_manifest",
    "load_plugin_class",
]
