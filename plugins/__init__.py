"""Plugin system for Pi Zero 2 W Music Player.

Discovers, loads, and manages plugins from plugin directories.
Plugins communicate with the core engine through capabilities, event hooks,
and direct API access.

Usage:

    from plugins import PluginManager

    manager = PluginManager(core_engine, plugin_dir="plugins")
    manager.load_plugins()
    audio_plugins = manager.get_plugins_with_capability("audio-output")
"""

import importlib.util
import json
import logging
import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from core.plugin_base import (
    MusicPlayerPlugin,
    PluginManifest,
    load_manifest,
    load_plugin_class,
)

logger = logging.getLogger(__name__)


class PluginManager:
    """Discovers, loads, and manages plugins for the music player.

    Scans plugin directories for config.json manifest files, loads plugin
    modules, instantiates plugin classes, and manages their lifecycle.
    """

    def __init__(
        self,
        core_engine: Any = None,
        plugin_dir: str = "plugins",
    ):
        """Initialize PluginManager.

        Args:
            core_engine: Core engine instance (MusicPlayer wrapper + system
                components) that plugins will reference via self.core.
            plugin_dir: Directory containing plugin subdirectories. Each
                subdirectory should contain a config.json manifest and
                implementation module.
        """
        self.core = core_engine
        self.plugin_dir = Path(plugin_dir)
        self.plugins: Dict[str, MusicPlayerPlugin] = {}
        self.plugins_metadata: Dict[str, PluginManifest] = {}
        self.hooks: Dict[str, List[Callable]] = defaultdict(list)
        self._enabled: Dict[str, bool] = {}

    # --- Discovery ---

    def discover_plugins(self) -> List[Path]:
        """Scan plugin directory for config.json manifest files.

        Returns:
            List[Path]: List of directories containing valid plugin manifests.
        """
        plugin_dirs = []
        if not self.plugin_dir.exists():
            logger.warning("Plugin directory does not exist: %s", self.plugin_dir)
            return plugin_dirs

        for entry in sorted(self.plugin_dir.iterdir()):
            if not entry.is_dir():
                continue
            manifest_path = entry / "config.json"
            if manifest_path.exists():
                plugin_dirs.append(entry)
            else:
                logger.debug(
                    "Skipping %s: no config.json manifest", entry
                )

        return plugin_dirs

    def load_all_plugins(self) -> int:
        """Discover and load all plugins from plugin_dir.

        Returns:
            int: Number of plugins successfully loaded.
        """
        loaded_count = 0
        plugin_dirs = self.discover_plugins()

        for plugin_dir_path in plugin_dirs:
            try:
                result = self.load_plugin_from_dir(plugin_dir_path)
                if result is not None:
                    loaded_count += 1
            except Exception as e:
                logger.error(
                    "Failed to load plugin from %s: %s", plugin_dir_path, e
                )

        return loaded_count

    def load_plugins(self) -> int:
        """Discover and load all plugins from plugin_dir.

        Convenience alias for load_all_plugins(), kept for backward
        compatibility with callers and documentation.

        Returns:
            int: Number of plugins successfully loaded.
        """
        return self.load_all_plugins()

    def load_plugin_from_dir(self, plugin_dir_path: Path) -> Optional[MusicPlayerPlugin]:
        """Load a single plugin from a directory containing config.json.

        Args:
            plugin_dir_path: Path to plugin directory.

        Returns:
            MusicPlayerPlugin instance or None if loading fails.
        """
        manifest_path = plugin_dir_path / "config.json"
        manifest = load_manifest(str(manifest_path))
        if manifest is None:
            return None

        plugin_id = manifest.plugin_id
        if plugin_id in self.plugins:
            logger.warning(
                "Plugin %s already loaded, skipping duplicate", plugin_id
            )
            return self.plugins[plugin_id]

        # Try to find and import the plugin module
        plugin_class = self._load_plugin_class_from_dir(plugin_dir_path, manifest)
        if plugin_class is None:
            return None

        # Instantiate plugin with manifest config
        try:
            plugin_instance = plugin_class(manifest.data)
        except Exception as e:
            logger.error(
                "Failed to instantiate plugin %s: %s", plugin_id, e
            )
            return None

        # Initialize plugin with core engine
        try:
            success = plugin_instance.initialize(self.core)
        except Exception as e:
            logger.error(
                "Failed to initialize plugin %s: %s", plugin_id, e
            )
            return None

        if not success:
            logger.warning(
                "Plugin %s initialization returned False", plugin_id
            )
            return None

        # Register plugin
        plugin_instance._set_initialized(True)
        self.plugins[plugin_id] = plugin_instance
        self.plugins_metadata[plugin_id] = manifest
        self._enabled[plugin_id] = True

        # Register any hooks the plugin declared
        if hasattr(plugin_instance, "get_registered_hooks"):
            hooks = plugin_instance.get_registered_hooks()
            for event_name, callback in hooks.items():
                self.register_hook(event_name, callback)

        logger.info("Loaded plugin: %s v%s (%s)", plugin_id, manifest.version, manifest.type)
        return plugin_instance

    def _load_plugin_class_from_dir(
        self,
        plugin_dir_path: Path,
        manifest: PluginManifest,
    ):
        """Find and load the plugin class from a directory.

        Looks for a Python file matching the plugin_id or any .py file in
        the directory containing a MusicPlayerPlugin subclass.
        """
        plugin_id = manifest.plugin_id

        # Try plugin_id.py first
        plugin_file = plugin_dir_path / f"{plugin_id}.py"
        if plugin_file.exists():
            return self._load_class_from_file(plugin_file, "MusicPlayerPlugin")

        # Try any .py file in the directory
        for py_file in sorted(plugin_dir_path.glob("*.py")):
            if py_file.name == "__init__.py":
                continue
            plugin_class = self._load_class_from_file(py_file, "MusicPlayerPlugin")
            if plugin_class is not None:
                return plugin_class

        logger.warning(
            "No plugin class found in %s", plugin_dir_path
        )
        return None

    def _load_class_from_file(self, file_path: Path, class_name: str):
        """Dynamically load a class from a Python file."""
        try:
            spec = importlib.util.spec_from_file_location(
                f"plugin_{file_path.stem}",
                str(file_path),
            )
            if spec is None or spec.loader is None:
                return None

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return getattr(module, class_name, None)
        except Exception as e:
            logger.warning(
                "Failed to load plugin module %s: %s", file_path, e
            )
            return None

    # --- Plugin Access ---

    def get_plugin(self, plugin_id: str) -> Optional[MusicPlayerPlugin]:
        """Get a loaded plugin instance by ID.

        Args:
            plugin_id: Plugin identifier string.

        Returns:
            MusicPlayerPlugin instance or None if not found.
        """
        return self.plugins.get(plugin_id)

    def get_plugins_with_capability(self, capability: str) -> List[MusicPlayerPlugin]:
        """Get all loaded plugins that provide a given capability.

        Args:
            capability: Capability string (e.g., "audio-output", "volume-control").

        Returns:
            List[MusicPlayerPlugin]: List of matching plugin instances.
        """
        result = []
        for plugin in self.plugins.values():
            if capability in plugin.get_capabilities():
                result.append(plugin)
        return result

    def get_plugins_by_type(self, type_name: str) -> List[MusicPlayerPlugin]:
        """Get all loaded plugins of a given type.

        Args:
            type_name: Plugin type string (e.g., "audio-backend", "feature").

        Returns:
            List[MusicPlayerPlugin]: List of matching plugin instances.
        """
        result = []
        manifest: PluginManifest
        for plugin_id, manifest in self.plugins_metadata.items():
            if manifest.type == type_name:
                plugin = self.plugins.get(plugin_id)
                if plugin is not None:
                    result.append(plugin)
        return result

    def get_all_plugins(self) -> List[MusicPlayerPlugin]:
        """Get all loaded plugin instances.

        Returns:
            List[MusicPlayerPlugin]: All loaded plugins.
        """
        return list(self.plugins.values())

    def get_manifest(self, plugin_id: str) -> Optional[PluginManifest]:
        """Get the manifest for a loaded plugin.

        Args:
            plugin_id: Plugin identifier string.

        Returns:
            PluginManifest or None if not found.
        """
        return self.plugins_metadata.get(plugin_id)

    # --- Plugin Lifecycle ---

    def load_plugin(self, plugin_id: str) -> Optional[MusicPlayerPlugin]:
        """Load a single plugin by manifest ID.

        Args:
            plugin_id: Plugin identifier string.

        Returns:
            MusicPlayerPlugin instance or None if loading fails.
        """
        if plugin_id in self.plugins:
            return self.plugins[plugin_id]

        manifest_path = self.plugin_dir / plugin_id / "config.json"
        if not manifest_path.exists():
            logger.warning("Plugin manifest not found: %s", manifest_path)
            return None

        return self.load_plugin_from_dir(self.plugin_dir / plugin_id)

    def unload_plugin(self, plugin_id: str) -> bool:
        """Unload and cleanup a plugin.

        Args:
            plugin_id: Plugin identifier string.

        Returns:
            bool: True if plugin was unloaded, False if not found.
        """
        plugin = self.plugins.get(plugin_id)
        if plugin is None:
            return False

        try:
            plugin.shutdown()
        except Exception as e:
            logger.warning("Error shutting down plugin %s: %s", plugin_id, e)

        del self.plugins[plugin_id]
        del self.plugins_metadata[plugin_id]
        del self._enabled[plugin_id]
        return True

    def reload_plugin(self, plugin_id: str) -> bool:
        """Reload a plugin (unload then load again).

        Args:
            plugin_id: Plugin identifier string.

        Returns:
            bool: True if reload succeeded, False otherwise.
        """
        if not self.unload_plugin(plugin_id):
            return False
        return self.load_plugin(plugin_id) is not None

    def enable_plugin(self, plugin_id: str) -> bool:
        """Enable a disabled plugin.

        Args:
            plugin_id: Plugin identifier string.

        Returns:
            bool: True if enabled, False if plugin not found.
        """
        if plugin_id not in self.plugins:
            return False
        self._enabled[plugin_id] = True
        return True

    def disable_plugin(self, plugin_id: str) -> bool:
        """Disable a plugin without unloading it.

        Args:
            plugin_id: Plugin identifier string.

        Returns:
            bool: True if disabled, False if plugin not found.
        """
        if plugin_id not in self.plugins:
            return False
        self._enabled[plugin_id] = False
        return True

    # --- Hook Management ---

    def register_hook(self, event_name: str, callback: Callable) -> None:
        """Register an event hook callback.

        Args:
            event_name: Event name string.
            callback: Callable to invoke when event fires.
        """
        self.hooks[event_name].append(callback)

    def trigger_hook(self, event_name: str, *args, **kwargs) -> None:
        """Trigger all callbacks registered for an event.

        Args:
            event_name: Event name string.
            *args: Positional arguments for callbacks.
            **kwargs: Keyword arguments for callbacks.
        """
        for callback in self.hooks.get(event_name, []):
            try:
                callback(*args, **kwargs)
            except Exception as e:
                logger.warning("Hook %s failed: %s", event_name, e)

    def unregister_hook(self, event_name: str, callback: Callable) -> bool:
        """Remove a hook callback.

        Args:
            event_name: Event name string.
            callback: Callable to remove.

        Returns:
            bool: True if callback was removed, False if not found.
        """
        callbacks = self.hooks.get(event_name, [])
        if callback in callbacks:
            callbacks.remove(callback)
            return True
        return False

    def get_registered_hooks(self) -> Dict[str, List[Callable]]:
        """Get all registered hooks.

        Returns:
            Dict[str, List[Callable]]: Event name to callbacks mapping.
        """
        return dict(self.hooks)

    # --- Info ---

    def get_plugin_info(self) -> List[Dict[str, Any]]:
        """Get info about all loaded plugins.

        Returns:
            List[Dict]: List of plugin info dicts with id, name, version,
                type, capabilities, enabled status.
        """
        result = []
        for plugin_id, manifest in self.plugins_metadata.items():
            plugin = self.plugins.get(plugin_id)
            result.append({
                "plugin_id": plugin_id,
                "name": manifest.name,
                "version": manifest.version,
                "type": manifest.type,
                "capabilities": manifest.capabilities,
                "enabled": self._enabled.get(plugin_id, False),
                "initialized": plugin.initialized if plugin else False,
            })
        return result


__all__ = [
    "PluginManager",
]
