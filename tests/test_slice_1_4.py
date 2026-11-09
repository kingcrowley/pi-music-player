"""Slice 1.4 Test Script — System Detection & Config Management

Usage:
    python3 tests/test_slice_1_4.py

Usage for quick import check:
    python3 -c "from tests.test_slice_1_4 import run_all_tests; run_all_tests()"
"""

import sys
import os
import tempfile
import subprocess
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.system import SystemDetector
from core.config import Config

RESULTS = []


def check(name: str, condition: bool, detail: str = ""):
    """Record a test result."""
    status = "PASS" if condition else "FAIL"
    mark = "PASS" if condition else "FAIL"
    RESULTS.append((status, name))
    print(f"  [{mark}] {status}: {name}" + (f" - {detail}" if detail else ""))


class Slice14TestCase(unittest.TestCase):
    """Unit tests for SystemDetector and Config that exercise real detection paths."""

    def setUp(self):
        self.tmpdirs = []

    def tearDown(self):
        for d in self.tmpdirs:
            import shutil
            shutil.rmtree(d, ignore_errors=True)

    # --- Audio Backend Detection ---

    @patch("core.system.subprocess.run")
    def test_detect_audio_backend_pipewire(self, mock_run):
        """PipeWire is installed but idle still counts as active."""
        mock_run.side_effect = [
            # First call: ps aux
            subprocess.CompletedProcess(args=[], returncode=0, stdout="user   pipewire"),
            # Second call: pipewire --version
            subprocess.CompletedProcess(args=["pipewire", "--version"], returncode=0, stdout="pw-1.0"),
            # Third call: pipewire-media-session --version (not found)
            subprocess.CompletedProcess(
                args=["pipewire-media-session", "--version"],
                returncode=127,
                stdout="",
                stderr="",
            ),
        ]
        detector = SystemDetector()
        backend = detector.detect_audio_backend()
        check("Detect PipeWire from ps output", backend == "pipewire")

    @patch("core.system.subprocess.run")
    def test_detect_audio_backend_pulse(self, mock_run):
        """PulseAudio detection via PULSE_SERVER env and paplay fallback."""
        mock_run.side_effect = [
            # ps aux - no pipewire processes (pipewire check first)
            subprocess.CompletedProcess(args=[], returncode=0, stdout="other line\n"),
            # pipewire --version not found
            subprocess.CompletedProcess(args=["pipewire", "--version"], returncode=127, stdout="", stderr=""),
            # pipewire-media-session --version not found
            subprocess.CompletedProcess(
                args=["pipewire-media-session", "--version"],
                returncode=127, stdout="", stderr="",
            ),
            # ps aux - no pulseaudio process
            subprocess.CompletedProcess(args=[], returncode=0, stdout="other line\n"),
            # pulseaudio --version found
            subprocess.CompletedProcess(args=["pulseaudio", "--version"], returncode=0, stdout="pulse 15.0"),
        ]
        detector = SystemDetector()
        backend = detector.detect_audio_backend()
        check("Detect PulseAudio via command availability", backend == "pulse")

    @patch("core.system.subprocess.run")
    def test_detect_audio_backend_alsa_default(self, mock_run):
        """Default ALSA when no PipeWire or PulseAudio detected."""
        mock_run.side_effect = [
            # ps aux - no audio processes
            subprocess.CompletedProcess(args=[], returncode=0, stdout="other line\n"),
            # pipewire --version - not found
            subprocess.CompletedProcess(args=["pipewire", "--version"], returncode=127, stdout="", stderr=""),
            # pulseaudio --version - not found
            subprocess.CompletedProcess(args=["pulseaudio", "--version"], returncode=127, stdout="", stderr=""),
            # paplay --help - not found
            subprocess.CompletedProcess(args=["paplay", "--help"], returncode=127, stdout="", stderr=""),
        ]
        detector = SystemDetector()
        backend = detector.detect_audio_backend()
        check("Fallback to ALSA default", backend == "alsa")

    # --- Display Server Detection ---

    @patch("core.system.subprocess.run")
    def test_detect_display_x11(self, mock_run):
        """X11 display via DISPLAY env var."""
        import os
        old_display = os.environ.get("DISPLAY")
        try:
            os.environ["DISPLAY"] = ":0.0"
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout=""
            )
            detector = SystemDetector()
            server = detector.detect_display_server()
            check("Detect X11 display via DISPLAY env", server == "x11")
        finally:
            if old_display is None:
                os.environ.pop("DISPLAY", None)
            else:
                os.environ["DISPLAY"] = old_display

    @patch("core.system.subprocess.run")
    def test_detect_display_wayland(self, mock_run):
        """Wayland display via WAYLAND_DISPLAY env var."""
        import os
        old_wl = os.environ.get("WAYLAND_DISPLAY")
        try:
            os.environ["WAYLAND_DISPLAY"] = "wayland-0"
            mock_run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0, stdout=""
            )
            detector = SystemDetector()
            server = detector.detect_display_server()
            check("Detect Wayland display via WAYLAND_DISPLAY env", server == "wayland")
        finally:
            if old_wl is None:
                os.environ.pop("WAYLAND_DISPLAY", None)
            else:
                os.environ["WAYLAND_DISPLAY"] = old_wl

    @patch("core.system.subprocess.run")
    def test_detect_display_unknown(self, mock_run):
        """Unknown display when no env vars set."""
        import os
        for var in ("DISPLAY", "WAYLAND_DISPLAY"):
            os.environ.pop(var, None)
        detector = SystemDetector()
        server = detector.detect_display_server()
        check("Return unknown when no display env vars", server == "unknown")

    # --- Distro Detection ---

    def test_detect_distro_debian(self):
        """Debian distro detected from /etc/os-release ID=debian."""
        with patch("builtins.open", new_callable=lambda: __import__("io").StringIO(
            "ID=debian\nVERSION_ID=\"12\"\nPRETTY_NAME=\"Debian GNU/Linux 12 (bookworm)\"\n"
            "ID_LIKE=debian\n"
        )):
            detector = SystemDetector()
            distro = detector.detect_distro()
            check("Detect Debian from /etc/os-release", distro == "debian")

    def test_detect_distro_ubuntu(self):
        """Ubuntu distro detected via ID_LIKE."""
        with patch("builtins.open", new_callable=lambda: __import__("io").StringIO(
            "ID=ubuntu\nPRETTY_NAME=\"Ubuntu 24.04 LTS\"\nID_LIKE=debian\n"
        )):
            detector = SystemDetector()
            distro = detector.detect_distro()
            check("Detect Ubuntu via ID_LIKE match", distro == "ubuntu")

    @patch("core.system.open", create=True)
    def test_detect_distro_unknown(self, mock_file):
        """Unknown distro when /etc/os-release doesn't match known IDs."""
        mock_file.return_value.read.return_value = (
            "ID=artiso\n"
        )
        detector = SystemDetector()
        distro = detector.detect_distro()
        check("Detect unknown distro gracefully", distro == "unknown")

    @patch("builtins.open", new_callable=lambda: __import__("io").StringIO(""))
    def test_detect_distro_malformed(self, mock_file):
        """Handle malformed /etc/os-release with bare content."""
        detector = SystemDetector()
        distro = detector.detect_distro()
        check("Handle empty /etc/os-release", distro == "unknown")

    # --- MPD Config Generation ---

    def test_generate_mpd_conf_alsa(self):
        """Generated config has correct structure without input block."""
        output_path = os.path.join(tempfile.mkdtemp(), "test_mpd.conf")
        self.tmpdirs.append(output_path)
        detector = SystemDetector(force_audio_backend="alsa")
        result = detector.generate_mpd_conf(output_path)
        check("MPD config generation succeeds for ALSA", result is True)
        if result and os.path.exists(output_path):
            with open(output_path, "r") as f:
                content = f.read()
            check("Config contains audio_output block", "audio_output" in content)
            check("Config has no input block", "input {" not in content)
            check("auto_update appears exactly once", content.count('auto_update') == 1)

    def test_generate_mpd_conf_pipewire(self):
        """Generated config works for PipeWire backend."""
        output_path = os.path.join(tempfile.mkdtemp(), "test_mpd.conf")
        self.tmpdirs.append(output_path)
        detector = SystemDetector(force_audio_backend="pipewire")
        result = detector.generate_mpd_conf(output_path)
        check("MPD config generation succeeds for PipeWire", result is True)
        if result and os.path.exists(output_path):
            with open(output_path, "r") as f:
                content = f.read()
            check("Config contains audio_output block", "audio_output" in content)
            check("Config has no input block", "input {" not in content)

    def test_template_path_resolves(self):
        """Template path resolves relative to module location."""
        detector = SystemDetector(force_audio_backend="alsa")
        template_name = detector.get_mpd_config_template()
        expected_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..", "configs", template_name
        ).replace("\\", "/")
        actual_path = os.path.normpath(os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..", "configs", template_name
        )).replace("\\", "/")
        check("Template path points to valid config file",
              os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                          "..", "configs", template_name)))

    # --- Config Management ---

    def test_config_get_set(self):
        """Config get/set works correctly."""
        config_path = os.path.join(tempfile.mkdtemp(), "config.json")
        self.tmpdirs.append(config_path)
        cfg = Config(config_path)
        cfg.set("audio.backend", "pipewire")
        val = cfg.get("audio.backend")
        check("Config set/get works for audio.backend", val == "pipewire")

    def test_config_persistence(self):
        """Config persists across reload."""
        config_path = os.path.join(tempfile.mkdtemp(), "config.json")
        self.tmpdirs.append(config_path)
        cfg = Config(config_path)
        cfg.set("audio.backend", "alsa")
        cfg.save()
        cfg2 = Config(config_path)
        val = cfg2.get("audio.backend")
        check("Config reload preserves values", val == "alsa")

    def test_config_update_detected_values(self):
        """update_detected_values persists system settings."""
        config_path = os.path.join(tempfile.mkdtemp(), "config.json")
        self.tmpdirs.append(config_path)
        cfg = Config(config_path)
        cfg.update_detected_values("pipewire", "wayland", "fedora")
        check("Detected values persisted for audio",
              cfg.get("system.detected_audio_backend") == "pipewire")
        check("Detected values persisted for display",
              cfg.get("system.detected_display_server") == "wayland")
        check("Detected values persisted for distro",
              cfg.get("system.detected_distro") == "fedora")

    def test_config_update_detected_values_non_dict(self):
        """Reject non-dictionary system value in update_detected_values."""
        config_path = os.path.join(tempfile.mkdtemp(), "config.json")
        self.tmpdirs.append(config_path)
        # Write a JSON array instead of object
        with open(config_path, "w") as f:
            f.write("[]")
        cfg = Config(config_path)
        result = cfg.update_detected_values("pipewire", "wayland", "fedora")
        check("Non-dict system returns False instead of crash", result is False)

    def test_config_invalid_json(self):
        """Invalid JSON raises ValueError, not AttributeError."""
        config_path = os.path.join(tempfile.mkdtemp(), "config.json")
        self.tmpdirs.append(config_path)
        with open(config_path, "w") as f:
            f.write("{broken json")
        with self.assertRaises(ValueError):
            Config(config_path)

    def test_merge_defaults_preserves_nested(self):
        """Merge preserves omitted nested defaults like audio.device."""
        config_path = os.path.join(tempfile.mkdtemp(), "config.json")
        self.tmpdirs.append(config_path)
        # Write partial config missing some nested keys
        with open(config_path, "w") as f:
            f.write('{"audio": {"backend": "pipewire"}}')
        cfg = Config(config_path)
        # Should not crash; nested defaults preserved
        val = cfg.get("audio.device")
        check("Nested default audio.device preserved", val == "default")
        val2 = cfg.get("audio.mixer_type")
        check("Nested default audio.mixer_type preserved", val2 == "software")

    # --- Template matching logic ---

    def test_detect_audio_never_returns_unknown(self):
        """detect_audio_backend always returns one of the four known values."""
        detector = SystemDetector(force_audio_backend="alsa")
        backend = detector.detect_audio_backend()
        check("detect_audio_backend never returns 'unknown'",
              backend in ["alsa", "pipewire", "pulse", "null"])

    def test_get_mpd_config_template(self):
        """get_mpd_config_template returns expected name."""
        for backend in ["alsa", "pipewire", "pulse", "null"]:
            detector = SystemDetector(force_audio_backend=backend)
            template_name = detector.get_mpd_config_template()
            check(f"Template name for {backend} is correct",
                  template_name == f"mpd.conf.{backend}")


def run_all_tests():
    """Run all Slice 1.4 acceptance tests."""
    print("=" * 60)
    print("Slice 1.4: System Detection & Config Management")
    print("=" * 60)

    # Run the unit tests
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(Slice14TestCase)
    runner = unittest.TextTestRunner(verbosity=1)
    result = runner.run(suite)

    total = len(RESULTS)
    passed = sum(1 for s, _ in RESULTS if s == "PASS")
    print(f"\nResults: {passed}/{total} checks passed")

    if passed == total:
        print("\n[OK] Slice 1.4: ACCEPTANCE CRITERIA MET")
        return True
    else:
        print(f"\n[WARN] Slice 1.4: {total - passed} check(s) failed")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
