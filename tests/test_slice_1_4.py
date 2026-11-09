"""Slice 1.4 Test Script — System Detection & Config Management

Usage:
    python3 tests/test_slice_1_4.py

Usage for quick import check:
    python3 -c "from tests.test_slice_1_4 import run_all_tests; run_all_tests()"
"""

import sys
import os
import tempfile

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


def run_all_tests():
    """Run all Slice 1.4 acceptance tests."""
    print("=" * 60)
    print("Slice 1.4: System Detection & Config Management")
    print("=" * 60)

    tmpdirs = []

    try:
        # Test 1: Audio backend detection with force values for determinism
        print("\n--- Audio Backend Detection ---")
        detector = SystemDetector(test_mode=True, force_audio_backend="pipewire")
        backend = detector.detect_audio_backend()
        check("Audio backend detection returns valid value",
              backend in ["alsa", "pipewire", "pulse", "null"],
              f"Backend: {backend}")

        # Test 2: Display server detection with force values
        print("\n--- Display Server Detection ---")
        detector_forced_display = SystemDetector(force_display_server="wayland")
        display_server = detector_forced_display.detect_display_server()
        check("Display server detection returns valid value",
              display_server in ["x11", "wayland", "unknown"],
              f"Display: {display_server}")

        # Test 3: Distro detection with force values
        print("\n--- Distro Detection ---")
        detector_forced_distro = SystemDetector(force_distro="fedora")
        distro = detector_forced_distro.detect_distro()
        check("Distro detection returns valid value",
              distro in ["debian", "ubuntu", "fedora", "arch", "alpine", "nixos", "unknown"],
              f"Distro: {distro}")

        # Test 4: MPD config template
        print("\n--- MPD Config Template ---")
        template_name = detector.get_mpd_config_template()
        check("Config template name matches detected backend",
              template_name == f"mpd.conf.{backend}",
              f"Template: {template_name}, Backend: {backend}")

        # Test 5: MPD config generation
        print("\n--- MPD Config Generation ---")
        tmpdir = tempfile.mkdtemp()
        tmpdirs.append(tmpdir)
        output_path = os.path.join(tmpdir, "test_mpd.conf")

        result = detector.generate_mpd_conf(output_path)
        check("MPD config generation succeeds",
              result is True,
              f"Result: {result}")

        # Test 6: Generated config contains audio_output
        print("\n--- Generated Config Content ---")
        if result and os.path.exists(output_path):
            with open(output_path, "r") as f:
                config_content = f.read()
            check("Generated config contains audio_output block",
                  "audio_output" in config_content,
                  f"Contains audio_output: {config_content}")
        else:
            check("Generated config file exists",
                  result is True,
                  f"Output path: {output_path}, Result: {result}")

        # Test 7: Config management
        print("\n--- Config Management ---")
        config_tmpdir = tempfile.mkdtemp()
        tmpdirs.append(config_tmpdir)
        config_path = os.path.join(config_tmpdir, "config.json")

        cfg = Config(config_path)
        check("Config object created successfully",
              cfg is not None,
              f"Config: {cfg}")

        # Test 8: Config get/set
        print("\n--- Config Get/Set ---")
        cfg.set("audio.backend", "pipewire")
        backend_val = cfg.get("audio.backend")
        check("Config get/set works correctly",
              backend_val == "pipewire",
              f"Got: {backend_val}")

        # Test 9: Config persistence
        print("\n--- Config Persistence ---")
        cfg.save()
        check("Config saved successfully",
              os.path.exists(config_path),
              f"Config path: {config_path}")

        # Test 10: Config reload
        print("\n--- Config Reload ---")
        cfg2 = Config(config_path)
        loaded_backend = cfg2.get("audio.backend")
        check("Config reload preserves values",
              loaded_backend == "pipewire",
              f"Loaded: {loaded_backend}")

        # Test 11: Update detected values
        print("\n--- Update Detected Values ---")
        cfg.update_detected_values("pipewire", "wayland", "fedora")
        updated_backend = cfg.get("system.detected_audio_backend")
        updated_display = cfg.get("system.detected_display_server")
        updated_distro = cfg.get("system.detected_distro")
        check("Update detected values works",
              updated_backend == "pipewire" and
              updated_display == "wayland" and
              updated_distro == "fedora",
              f"Backend: {updated_backend}, Display: {updated_display}, Distro: {updated_distro}")

        # Test 12: Mocked detector for test_mode
        print("\n--- Detector test_mode ---")
        detector_forced = SystemDetector(force_audio_backend="pipewire",
                                         force_display_server="wayland",
                                         force_distro="fedora")
        forced_backend = detector_forced.detect_audio_backend()
        forced_display = detector_forced.detect_display_server()
        forced_distro = detector_forced.detect_distro()
        check("Detector force_overrides work",
              forced_backend == "pipewire" and
              forced_display == "wayland" and
              forced_distro == "fedora",
              f"Backend: {forced_backend}, Display: {forced_display}, Distro: {forced_distro}")

        # Summary
        print("\n" + "=" * 60)
        passed = sum(1 for s, _ in RESULTS if s == "PASS")
        total = len(RESULTS)
        print(f"Results: {passed}/{total} tests passed")

        if passed == total:
            print("\n[OK] Slice 1.4: ACCEPTANCE CRITERIA MET")
            return True
        else:
            print(f"\n[WARN] Slice 1.4: {total - passed} test(s) need review")
            return False

    finally:
        # Cleanup
        for d in tmpdirs:
            import shutil
            shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)