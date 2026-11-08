"""System detection and configuration management for Pi Zero 2 W.

Provides runtime environment detection for audio backend, display server,
distro identification, and MPD config generation.
"""

import subprocess
import os
import re
import json
from pathlib import Path
from typing import Optional, Tuple


class SystemDetector:
    """Detects runtime environment for proper MPD configuration.

    Determines audio backend, display server, and distribution
    to generate appropriate MPD configuration.
    """

    # Audio backends in order of preference
    AUDIO_BACKENDS = ["alsa", "pipewire", "pulse", "null"]

    # Display servers in order of preference
    DISPLAY_SERVERS = ["wayland", "x11", "unknown"]

    # Distribution IDs
    DISTRO_IDS = ["debian", "ubuntu", "fedora", "arch", "alpine", "nixos"]

    # Trusted audio backends
    TRUSTED_AUDIO_BACKENDS = ["alsa", "pipewire", "pulse", "null"]

    def __init__(self, test_mode: bool = False,
                 force_distro: Optional[str] = None,
                 force_audio_backend: Optional[str] = None,
                 force_display_server: Optional[str] = None):
        """Initialize SystemDetector.

        Args:
            test_mode: Run in test mode (skip hardware detection, return defaults)
            force_distro: Override detected distro (for testing)
            force_audio_backend: Override detected audio backend (for testing)
            force_display_server: Override detected display server (for testing)
        """
        self._force_distro = force_distro
        self._force_audio_backend = force_audio_backend
        self._force_display_server = force_display_server
        self._test_mode = test_mode
        self._cache = {}

    def detect_audio_backend(self) -> str:
        """Detect the audio backend being used.

        Checks in order: PipeWire, PulseAudio, ALSA.
        Returns the detected backend name or 'unknown'.

        Returns:
            str: Detected audio backend name
        """
        if self._force_audio_backend:
            return self._force_audio_backend

        # Check PipeWire first
        pipewire_result = self._check_pipewire()
        if pipewire_result:
            return pipewire_result

        # Check PulseAudio
        pulseaudio_result = self._check_pulseaudio()
        if pulseaudio_result:
            return pulseaudio_result

        # Default to ALSA
        return "alsa"

    def _check_pipewire(self) -> Optional[str]:
        """Check if PipeWire is the active audio backend."""
        try:
            # Check for pipewire processes
            result = subprocess.run(
                ["ps", "aux"], capture_output=True, text=True
            )
            pipewire_processes = [
                p for p in result.split("\n")
                if "pipewire" in p.lower()
            ]
            if pipewire_processes:
                return "pipewire"

            # Check pipewire command availability
            result = subprocess.run(
                ["pipewire --version"], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0 and result.stdout:
                return "pipewire"

            # Check pipewire-media-session
            result = subprocess.run(
                ["pipewire-media-session", "--version"], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0 and result.stdout:
                return "pipewire"

        except Exception:
            pass

        return None

    def _check_pulseaudio(self) -> Optional[str]:
        """Check if PulseAudio is the active audio backend."""
        try:
            # Check for pulseaudio processes
            result = subprocess.run(
                ["ps", "aux"], capture_output=True, text=True
            )
            pulseaudio_processes = [
                p for p in result.split("\n")
                if "pulseaudio" in p.lower()
            ]
            if pulseaudio_processes:
                return "pulseaudio"

            # Check pulseaudio command availability
            result = subprocess.run(
                ["pulseaudio --version"], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0 and result.stdout:
                return "pulseaudio"

            # Check environment variable
            if "PULSE_SERVER" in __import__("os").environ:
                return "pulseaudio"

            # Check for paplay command
            result = subprocess.run(
                ["paplay", "--help"], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                return "pulseaudio"

        except Exception:
            pass

        return None

    def detect_display_server(self) -> str:
        """Detect the display server being used.

        Returns:
            str: Detected display server (x11, wayland, or unknown)
        """
        if self._force_display_server:
            return self._force_display_server

        # Check WAYLAND_DISPLAY env var
        display_var = __import__("os").getenv("WAYLAND_DISPLAY")
        if display_var:
            return "wayland"

        # Check for X11 DISPLAY
        display_var = __import__("os").getenv("DISPLAY")
        if display_var:
            # Check if it's a local X11 display
            if ":0" in display_var or display_var.startswith("unix:"):
                return "x11"

        # Check for XWayland
        xwayland_var = __import__("os").getenv("XWAYLAND_DISPLAY")
        if xwayland_var:
            return "wayland"  # XWayland implies Wayland underneath

        return "unknown"

    def detect_distro(self) -> str:
        """Detect the Linux distribution being used.

        Returns:
            str: Detected distribution name or 'unknown'
        """
        if self._force_distro:
            return self._force_distro

        try:
            with open("/etc/os-release", "r") as f:
                content = f.read()
        except FileNotFoundError:
            return "unknown"

        # Parse /etc/os-release
        content = content.lower()
        for distro in self.DISTRO_IDS:
            # Check for exact ID match
            if f'id="{distro}"' in content or f' id="{distro}"' in content:
                return distro
            # Check for LIKE match
            if f'id LIKE "{distro}"' in content or f' id LIKE "{distro}"' in content:
                return distro

        # Check /etc/os-release standard fields
        for field in ["PRETTY_NAME", "VERSION", "NAME"]:
            if f'"{field}"' in content:
                # Try to extract the value
                lines = content.split("\n")
                for line in lines:
                    if field in line:
                        # Extract the value after the equals sign
                        parts = line.split('="')
                        if len(parts) > 1:
                            value = parts[1].split('"')[0]
                            # Check if it contains one of our distro IDs
                            for d in self.DISTRO_IDS:
                                if d in value.lower():
                                    return d

        return "unknown"

    def get_mpd_config_template(self) -> str:
        """Get the appropriate MPD config template name.

        Returns:
            str: Template name (alsa, pipewire, pulse, null)
        """
        audio_backend = self.detect_audio_backend()
        return f"mpd.conf.{audio_backend}"

    def generate_mpd_conf(self, output_path: str = "/etc/mpd.conf") -> bool:
        """Generate and write MPD configuration file.

        Creates an MPD configuration file with the appropriate
        audio_output block based on the detected audio backend.

        Args:
            output_path: Path to write the MPD configuration file

        Returns:
            bool: True if config was generated successfully
        """
        audio_backend = self.detect_audio_backend()
        distro = self.detect_distro()

        # Get the template
        template_name = f"mpd.conf.{audio_backend}"
        template_path = f"configs/{mpd.conf.alsa}"  # default

        # Try to find the template
        template_path = f"configs/mpd.conf.{audio_backend}"
        if not __import__("os").path.exists(f"configs/{mpd.conf.alsa}"):
            # Fall back to alsa as default
            template_path = "configs/mpd.conf.alsa"

        # Read the template
        try:
            with open(f"configs/{mpd.conf.alsa}", "r") as f:
                template = f.read()
        except FileNotFoundError:
            template = self._generate_default_config(audio_backend)

        # Customize based on distro
        template = self._customize_config(template, distro)

        # Write the config file
        try:
            with open(output_path, "w") as f:
                f.write(template)
            return True
        except (IOError, OSError) as e:
            print(f"Error writing MPD config: {e}")
            return False

    def _customize_config(self, template: str, distro: str) -> str:
        """Customize the MPD config based on distribution.

        Args:
            template: The template string
            distro: The detected distribution

        Returns:
            Customized config string
        """
        # Add distro-specific modifications
        if distro == "debian":
            # Debian-specific settings
            pass
        elif distro == "ubuntu":
            # Ubuntu-specific settings
            pass
        elif distro == "fedora":
            # Fedora-specific settings
            pass
        elif distro == "arch":
            # Arch-specific settings
            pass
        elif distro == "alpine":
            # Alpine-specific settings
            pass

        return template

    def get_audio_backend(self) -> str:
        """Public API: Get the detected audio backend.

        Returns:
            str: Detected audio backend name
        """
        return self.detect_audio_backend()

    def get_display_server(self) -> str:
        """Public API: Get the detected display server.

        Returns:
            str: Detected display server name
        """
        return self.detect_display_server()

    def get_distro(self) -> str:
        """Public API: Get the detected distribution.

        Returns:
            str: Detected distribution name
        """
        return self.detect_distro()

    def get_mpd_config_template(self) -> str:
        """Public API: Get the MPD config template name.

        Returns:
            str: Template name
        """
        audio_backend = self.detect_audio_backend()
        return f"mpd.conf.{audio_backend}"

    def generate_mpd_conf(self, output_path: str = "/etc/mpd.conf") -> bool:
        """Public API: Generate MPD config file.

        Args:
            output_path: Path to write the MPD config

        Returns:
            bool: True if config was generated successfully
        """
        audio_backend = self.detect_audio_backend()
        distro = self.detect_distro()

        # Get the template
        template_name = f"mpd.conf.{audio_backend}"

        # Try to find the template
        try:
            with open(f"configs/{template_name}", "r") as f:
                template = f.read()
        except FileNotFoundError:
            template = self._generate_default_config(audio_backend)

        # Customize based on distro
        template = self._customize_config(template, distro)

        # Write the config file
        try:
            with open(output_path, "w") as f:
                f.write(template)
            return True
        except (IOError, OSError) as e:
            print(f"Error writing MPD config: {e}")
            return False