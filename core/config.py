"""Configuration management for Pi Zero 2 W Music Player.

Provides configuration loading and saving with
detected values + user overrides.
"""

import copy
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional


class Config:
    """Manages application configuration with defaults."""

    # Default configuration schema
    DEFAULT_CONFIG = {
        "audio": {
            "backend": "auto",  # auto, alsa, pipewire, pulse, null
            "device": "default",
            "mixer_type": "software",
        },
        "mpd": {
            "host": "localhost",
            "port": 6600,
            "timeout": 5.0,
        },
        "ui": {
            "fullscreen": True,
            "touch_friendly": True,
            "theme": "dark",
        },
        "cache": {
            "artwork_max_size_mb": 50,
            "artwork_cache_dir": "~/.cache/pi-music-player/artwork",
        },
        "system": {
            "detected_audio_backend": "auto",
            "detected_display_server": "auto",
            "detected_distro": "auto",
        },
        "stats": {
            "enabled": True,
            "db_path": "~/.local/share/pi-music-player/play_stats.db",
            "max_size_mb": 10,
            "retention_days": 365,
            "reset": False,
        },
    }

    def __init__(self, config_path: Optional[str] = None):
        """Initialize configuration manager.

        Args:
            config_path: Path to config file. Defaults to ./config.json
        """
        self.config_path = Path(config_path) if config_path else Path("config.json")
        self._config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file or return defaults."""
        if self.config_path.exists():
            try:
                with open(self.config_path, "r") as f:
                    loaded = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                raise ValueError(f"Invalid or unreadable configuration file: {self.config_path}") from e
            if not isinstance(loaded, dict):
                raise ValueError(
                    f"Configuration file {self.config_path} does not contain a JSON object"
                )
            # Merge with defaults to ensure all keys exist
            return self._merge_with_defaults(loaded)
        return copy.deepcopy(self.DEFAULT_CONFIG)

    def _merge_with_defaults(
        self, loaded: Dict[str, Any], defaults: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Recursively merge loaded config with defaults."""
        result = copy.deepcopy(self.DEFAULT_CONFIG if defaults is None else defaults)
        for key, value in loaded.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_with_defaults(value, result[key])
            else:
                result[key] = value
        return result

    def save(self) -> bool:
        """Save current configuration to file.

        Returns:
            bool: True if saved successfully
        """
        try:
            # Ensure parent directory exists
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, "w") as f:
                json.dump(self._config, f, indent=2)
            return True
        except (IOError, OSError) as e:
            print(f"Error saving config: {e}")
            return False

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value by dot-separated key path.

        Args:
            key: Dot-separated key path (e.g., "audio.backend")
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        keys = key.split(".")
        value = self._config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    def set(self, key: str, value: Any) -> bool:
        """Set a configuration value by dot-separated key path.

        Args:
            key: Dot-separated key path (e.g., "audio.backend")
            value: Value to set

        Returns:
            bool: True if set successfully
        """
        keys = key.split(".")
        target = self._config
        for k in keys[:-1]:
            if k not in target:
                target[k] = {}
            # Ensure intermediate value is a dict before descending
            if not isinstance(target[k], dict):
                return False
            target = target[k]
        target[keys[-1]] = value
        return True

    def update_detected_values(self, audio_backend: str, display_server: str, distro: str) -> bool:
        """Update detected system values in config.

        Args:
            audio_backend: Detected audio backend
            display_server: Detected display server
            distro: Detected distribution

        Returns:
            bool: True if updated successfully
        """
        if not isinstance(self._config.get("system"), dict):
            return False
        self._config["system"]["detected_audio_backend"] = audio_backend
        self._config["system"]["detected_display_server"] = display_server
        self._config["system"]["detected_distro"] = distro
        return self.save()

    def get_all(self) -> Dict[str, Any]:
        """Get the entire configuration.

        Returns:
            Complete configuration dictionary
        """
        return self._config.copy()


# Convenience function for quick config access
def get_config(config_path: Optional[str] = None) -> Config:
    """Get a Config instance.

    Args:
        config_path: Optional path to config file

    Returns:
        Config instance
    """
    return Config(config_path)