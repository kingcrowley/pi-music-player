"""Slice 1.5 Test Suite — Touch UI & Plugin System

Tests for Slice 1.5 deliverables:
- Styles constants
- Touch widget components (button, progress bar, art label, volume slider, status label)
- Plugin system (manager, base class, manifest loading)
"""

import sys
import os
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ui.styles import TOUCH_TARGET_SIZE, COLORS, FONTS, SPACING, WINDOW
from core.plugin_base import MusicPlayerPlugin, PluginManifest, load_manifest, load_plugin_class
from plugins import PluginManager

RESULTS = []


def check(name: str, condition: bool, detail: str = ""):
    """Record a test result."""
    status = "PASS" if condition else "FAIL"
    mark = "PASS" if condition else "FAIL"
    RESULTS.append((status, name))
    print(f"  [{mark}] {status}: {name}" + (f" - {detail}" if detail else ""))


class Slice15TestCase(unittest.TestCase):
    """Unit tests for Slice 1.5 (Styles, Components, Plugin System)."""

    def setUp(self):
        self.tmpdirs = []

    def tearDown(self):
        for d in self.tmpdirs:
            shutil.rmtree(d, ignore_errors=True)

    # --- Styles Constants ---

    def test_styles_constants_exist(self):
        check("TOUCH_TARGET_SIZE == 48", TOUCH_TARGET_SIZE == 48)
        check("COLORS has bg", "bg" in COLORS)
        check("COLORS has fg", "fg" in COLORS)
        check("COLORS has accent", "accent" in COLORS)
        check("COLORS has warning", "warning" in COLORS)

    def test_fonts_constants_exist(self):
        check("FONTS has title", "title" in FONTS)
        check("FONTS has artist", "artist" in FONTS)
        check("FONTS has album", "album" in FONTS)

    def test_spacing_constants_exist(self):
        check("SPACING has xs", "xs" in SPACING)
        check("SPACING has lg", "lg" in SPACING)

    def test_window_defaults_exist(self):
        check("WINDOW has fullscreen", "fullscreen" in WINDOW)
        check("WINDOW has min_width", "min_width" in WINDOW)

    # --- TouchButton Component ---

    def test_touch_button_creation(self):
        import tkinter as tk
        root = tk.Tk()
        try:
            from ui.widget import TouchButton
            btn = TouchButton(root, text="Test")
            btn.pack()
            root.update()
            root.destroy()
            check("TouchButton creation does not crash", True)
        except Exception as e:
            check("TouchButton creation works", False, str(e))
            root.destroy()

    def test_album_art_placeholder(self):
        import tkinter as tk
        root = tk.Tk()
        try:
            from ui.widget import AlbumArtLabel
            widget = AlbumArtLabel(root, size=100)
            widget.pack()
            root.update()
            canvas_width = widget.winfo_width()
            check("AlbumArtLabel has non-zero width", canvas_width > 0)
            root.destroy()
        except Exception as e:
            check("AlbumArtLabel creation works", False, str(e))
            root.destroy()

    def test_progress_bar_seek(self):
        import tkinter as tk
        root = tk.Tk()
        try:
            from ui.widget import ProgressBar
            pb = ProgressBar(root, width=200, height=20)
            pb.pack()
            root.update()
            pb.set_progress(0.5)
            root.update()
            check("ProgressBar set_progress works", True)
            root.destroy()
        except Exception as e:
            check("ProgressBar set_progress works", False, str(e))
            root.destroy()

    def test_progressbar_seek_callback(self):
        import tkinter as tk
        root = tk.Tk()
        try:
            from ui.widget import ProgressBar

            def on_seek(fraction):
                pass

            pb = ProgressBar(root, width=200, height=20)
            pb.set_seek_callback(on_seek)
            root.update()
            check("Seek callback registration works", True)
            root.destroy()
        except Exception as e:
            check("Seek callback registration works", False, str(e))
            root.destroy()

    def test_volumeslider_creation(self):
        import tkinter as tk
        root = tk.Tk()
        try:
            from ui.widget import VolumeSlider
            vs = VolumeSlider(root, orientation="horizontal")
            vs.pack()
            root.update()
            check("VolumeSlider creation does not crash", True)
            root.destroy()
        except Exception as e:
            check("VolumeSlider creation works", False, str(e))
            root.destroy()

    def test_volumeslider_set_volume(self):
        import tkinter as tk
        root = tk.Tk()
        try:
            from ui.widget import VolumeSlider
            vs = VolumeSlider(root, orientation="horizontal")
            vs.set_volume(0.5)
            root.update()
            check("VolumeSlider set_volume works", True)
            root.destroy()
        except Exception as e:
            check("VolumeSlider set_volume works", False, str(e))
            root.destroy()

    def test_statuslabel_creation(self):
        import tkinter as tk
        root = tk.Tk()
        try:
            from ui.widget import StatusLabel
            sl = StatusLabel(root, text="Test")
            root.update()
            check("StatusLabel creation does not crash", True)
            root.destroy()
        except Exception as e:
            check("StatusLabel creation works", False, str(e))
            root.destroy()

    # --- Plugin System ---

    def test_plugin_manager_instantiate(self):
        mgr = PluginManager(root=None, plugin_dir="plugins")
        check("PluginManager instantiates", mgr is not None)

    def test_plugin_manager_basic(self):
        import tkinter as tk
        root = tk.Tk()
        mgr = PluginManager(root, plugin_dir="plugins")
        check("PluginManager creates successfully", mgr is not None)
        mgr.load_plugins()
        check("PluginManager handles missing plugins gracefully", True)
        root.destroy()

    def test_plugin_manager_load_nonexistent(self):
        import tkinter as tk
        root = tk.Tk()
        mgr = PluginManager(root, plugin_dir="plugins")
        result = mgr.load_plugin("nonexistent_plugin")
        check("Loading nonexistent plugin returns None", result is None)
        root.destroy()

    def test_plugin_manager_unload_nonexistent(self):
        import tkinter as tk
        root = tk.Tk()
        mgr = PluginManager(root, plugin_dir="plugins")
        result = mgr.unload_plugin("nonexistent_plugin")
        check("Unloading nonexistent plugin returns False", result is False)
        root.destroy()

    def test_plugin_manager_get_plugin(self):
        import tkinter as tk
        root = tk.Tk()
        mgr = PluginManager(root, plugin_dir="plugins")
        result = mgr.get_plugin("nonexistent")
        check("Getting nonexistent plugin returns None", result is None)
        root.destroy()

    def test_plugin_manager_get_all_plugins_empty(self):
        import tkinter as tk
        root = tk.Tk()
        mgr = PluginManager(root, plugin_dir="plugins")
        mgr.load_plugins()
        plugins = mgr.get_all_plugins()
        check("PluginManager returns empty list when no plugins", plugins == [])
        root.destroy()

    # --- PluginBase Tests ---

    def test_plugin_base_abstract_instantiation(self):
        """Test that Plugin base class can be subclassed and instantiated."""
        import tkinter as tk
        from core.plugin_base import MusicPlayerPlugin

        root = tk.Tk()
        try:

            class TestPlugin(MusicPlayerPlugin):
                def initialize(self, core):
                    self.core = core
                    self._set_initialized(True)
                    return True

            plugin = TestPlugin(config={"name": "Test", "version": "1.0.0"})
            check("Plugin subclass instantiates", plugin.name == "Test")
            check("Plugin version correct", plugin.version == "1.0.0")
            check("Plugin initialized False initially", plugin.initialized is False)
            check("Plugin initialize works", plugin.initialize(root))
            check("Plugin initialized True after init", plugin.initialized is True)
            root.destroy()
        except Exception as e:
            check("Plugin subclass instantiation works", False, str(e))
            root.destroy()

    # --- PluginManifest Tests ---

    def test_plugin_manifest_creation(self):
        manifest_data = {
            "plugin_id": "test-plugin",
            "name": "Test Plugin",
            "version": "1.0.0",
            "type": "feature",
            "capabilities": ["test-cap"],
        }
        manifest = PluginManifest(manifest_data)
        check("PluginManifest creates successfully", manifest is not None)
        check("Manifest plugin_id correct", manifest.plugin_id == "test-plugin")
        check("Manifest name correct", manifest.name == "Test Plugin")

    def test_plugin_manifest_is_valid(self):
        manifest_data = {
            "plugin_id": "test-plugin",
            "name": "Test Plugin",
            "version": "1.0.0",
            "type": "feature",
        }
        manifest = PluginManifest(manifest_data)
        check("Manifest is valid", manifest.is_valid())

    def test_plugin_manifest_missing_required(self):
        manifest_data = {"name": "Test Plugin"}  # missing plugin_id, version, type
        manifest = PluginManifest(manifest_data)
        check("Manifest with missing required fields is invalid", not manifest.is_valid())

    def test_load_manifest_from_file(self):
        import json
        tmpdir = tempfile.mkdtemp()
        self.tmpdirs.append(tmpdir)
        manifest_path = os.path.join(tmpdir, "config.json")
        manifest_data = {
            "plugin_id": "test-plugin",
            "name": "Test Plugin",
            "version": "1.0.0",
            "type": "feature",
            "capabilities": ["test-cap"],
        }
        with open(manifest_path, "w") as f:
            json.dump(manifest_data, f)

        manifest = load_manifest(manifest_path)
        check("load_manifest loads valid manifest", manifest is not None)
        check("Manifest name matches", manifest.name == "Test Plugin")

    def test_load_manifest_invalid_json(self):
        import json
        tmpdir = tempfile.mkdtemp()
        self.tmpdirs.append(tmpdir)
        manifest_path = os.path.join(tmpdir, "config.json")
        with open(manifest_path, "w") as f:
            f.write("{invalid json")

        manifest = load_manifest(manifest_path)
        check("load_manifest handles invalid JSON", manifest is None)

    def test_load_plugin_class_from_module(self):
        import tkinter as tk
        root = tk.Tk()
        try:
            cls = load_plugin_class("core.plugin_base", "MusicPlayerPlugin")
            check("load_plugin_class loads MusicPlayerPlugin", cls is not None)
        except Exception as e:
            check("load_plugin_class works", False, str(e))
        root.destroy()


def run_all_tests():
    """Run all Slice 1.5 acceptance tests."""
    print("=" * 60)
    print("Slice 1.5: Tkinter Touch UI & Plugin System")
    print("=" * 60)

    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(Slice15TestCase)
    runner = unittest.TextTestRunner(verbosity=1)
    result = runner.run(suite)

    total = len(RESULTS)
    passed = sum(1 for s, _ in RESULTS if s == "PASS")
    print(f"\nResults: {passed}/{total} checks passed")

    if passed == total:
        print("\n[OK] Slice 1.5: ACCEPTANCE CRITERIA MET")
        return True
    else:
        print(f"\n[WARN] Slice 1.5: {total - passed} check(s) failed")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)