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


class Slice15TestCase(unittest.TestCase):
    """Unit tests for Slice 1.5 (Styles, Components, Plugin System)."""

    def setUp(self):
        self.tmpdirs = []

    def tearDown(self):
        for d in self.tmpdirs:
            shutil.rmtree(d, ignore_errors=True)

    # --- Styles Constants ---

    def test_styles_constants_exist(self):
        self.assertTrue(TOUCH_TARGET_SIZE == 48, "TOUCH_TARGET_SIZE == 48")
        self.assertTrue("bg" in COLORS, "COLORS has bg")
        self.assertTrue("fg" in COLORS, "COLORS has fg")
        self.assertTrue("accent" in COLORS, "COLORS has accent")
        self.assertTrue("warning" in COLORS, "COLORS has warning")

    def test_fonts_constants_exist(self):
        self.assertTrue("title" in FONTS, "FONTS has title")
        self.assertTrue("artist" in FONTS, "FONTS has artist")
        self.assertTrue("album" in FONTS, "FONTS has album")

    def test_spacing_constants_exist(self):
        self.assertTrue("xs" in SPACING, "SPACING has xs")
        self.assertTrue("lg" in SPACING, "SPACING has lg")

    def test_window_defaults_exist(self):
        self.assertTrue("fullscreen" in WINDOW, "WINDOW has fullscreen")
        self.assertTrue("min_width" in WINDOW, "WINDOW has min_width")

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
        except Exception as e:
            self.assertTrue(False, f"TouchButton creation works: {e}")
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
            self.assertTrue(canvas_width > 0, "AlbumArtLabel has non-zero width")
            root.destroy()
        except Exception as e:
            self.assertTrue(False, f"AlbumArtLabel creation works: {e}")
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
        except Exception as e:
            self.assertTrue(False, f"ProgressBar set_progress works: {e}")
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
        except Exception as e:
            self.assertTrue(False, f"Seek callback registration works: {e}")
            root.destroy()

    def test_volumeslider_creation(self):
        import tkinter as tk
        root = tk.Tk()
        try:
            from ui.widget import VolumeSlider
            vs = VolumeSlider(root, orientation="horizontal")
            vs.pack()
            root.update()
        except Exception as e:
            self.assertTrue(False, f"VolumeSlider creation does not crash: {e}")
            root.destroy()

    def test_volumeslider_set_volume(self):
        import tkinter as tk
        root = tk.Tk()
        try:
            from ui.widget import VolumeSlider
            vs = VolumeSlider(root, orientation="horizontal")
            vs.set_volume(0.5)
            root.update()
        except Exception as e:
            self.assertTrue(False, f"VolumeSlider set_volume works: {e}")
            root.destroy()

    def test_statuslabel_creation(self):
        import tkinter as tk
        root = tk.Tk()
        try:
            from ui.widget import StatusLabel
            sl = StatusLabel(root, text="Test")
            root.update()
        except Exception as e:
            self.assertTrue(False, f"StatusLabel creation does not crash: {e}")
            root.destroy()

    # --- Plugin System ---

    def test_plugin_manager_instantiate(self):
        mgr = PluginManager(core_engine=None, plugin_dir="plugins")
        self.assertTrue(mgr is not None, "PluginManager instantiates")

    def test_plugin_manager_basic(self):
        import tkinter as tk
        root = tk.Tk()
        try:
            mgr = PluginManager(core_engine=root, plugin_dir="plugins")
            self.assertTrue(mgr is not None, "PluginManager creates successfully")
            mgr.load_plugins()
        finally:
            root.destroy()

    def test_plugin_manager_load_nonexistent(self):
        import tkinter as tk
        root = tk.Tk()
        try:
            mgr = PluginManager(core_engine=root, plugin_dir="plugins")
            result = mgr.load_plugin("nonexistent_plugin")
            self.assertTrue(result is None, "Loading nonexistent plugin returns None")
        finally:
            root.destroy()

    def test_plugin_manager_unload_nonexistent(self):
        import tkinter as tk
        root = tk.Tk()
        try:
            mgr = PluginManager(core_engine=root, plugin_dir="plugins")
            result = mgr.unload_plugin("nonexistent_plugin")
            self.assertTrue(result is False, "Unloading nonexistent plugin returns False")
        finally:
            root.destroy()

    def test_plugin_manager_get_plugin(self):
        import tkinter as tk
        root = tk.Tk()
        try:
            mgr = PluginManager(core_engine=root, plugin_dir="plugins")
            result = mgr.get_plugin("nonexistent")
            self.assertTrue(result is None, "Getting nonexistent plugin returns None")
        finally:
            root.destroy()

    def test_plugin_manager_get_all_plugins_empty(self):
        import tkinter as tk
        root = tk.Tk()
        try:
            mgr = PluginManager(core_engine=root, plugin_dir="plugins")
            mgr.load_plugins()
            plugins = mgr.get_all_plugins()
            self.assertTrue(plugins == [], "PluginManager returns empty list when no plugins")
        finally:
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
            self.assertTrue(plugin.name == "Test", "Plugin subclass instantiates")
            self.assertTrue(plugin.version == "1.0.0", "Plugin version correct")
            self.assertTrue(plugin.initialized is False, "Plugin initialized False initially")
            self.assertTrue(plugin.initialize(root), "Plugin initialize works")
            self.assertTrue(plugin.initialized is True, "Plugin initialized True after init")

            # Abstract base class itself cannot be instantiated directly
            with self.assertRaises(TypeError):
                MusicPlayerPlugin(config={})

            root.destroy()
        except Exception as e:
            self.assertTrue(False, f"Plugin subclass instantiation works: {e}")
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
        self.assertTrue(manifest is not None, "PluginManifest creates successfully")
        self.assertTrue(manifest.plugin_id == "test-plugin", "Manifest plugin_id correct")
        self.assertTrue(manifest.name == "Test Plugin", "Manifest name correct")

    def test_plugin_manifest_is_valid(self):
        manifest_data = {
            "plugin_id": "test-plugin",
            "name": "Test Plugin",
            "version": "1.0.0",
            "type": "feature",
        }
        manifest = PluginManifest(manifest_data)
        self.assertTrue(manifest.is_valid(), "Manifest is valid")

    def test_plugin_manifest_missing_required(self):
        manifest_data = {"name": "Test Plugin"}  # missing plugin_id, version, type
        manifest = PluginManifest(manifest_data)
        self.assertTrue(not manifest.is_valid(), "Manifest with missing required fields is invalid")

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
        self.assertTrue(manifest is not None, "load_manifest loads valid manifest")
        self.assertTrue(manifest.name == "Test Plugin", "Manifest name matches")

    def test_load_manifest_invalid_json(self):
        import json
        tmpdir = tempfile.mkdtemp()
        self.tmpdirs.append(tmpdir)
        manifest_path = os.path.join(tmpdir, "config.json")
        with open(manifest_path, "w") as f:
            f.write("{invalid json")

        manifest = load_manifest(manifest_path)
        self.assertTrue(manifest is None, "load_manifest handles invalid JSON")

    def test_load_plugin_class_from_module(self):
        import tkinter as tk
        root = tk.Tk()
        try:
            cls = load_plugin_class("core.plugin_base", "MusicPlayerPlugin")
            self.assertTrue(cls is not None, "load_plugin_class loads MusicPlayerPlugin")
        except Exception as e:
            self.assertTrue(False, f"load_plugin_class works: {e}")
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

    if result.wasSuccessful():
        print("\n[OK] Slice 1.5: ACCEPTANCE CRITERIA MET")
        return True
    else:
        print(f"\n[WARN] Slice 1.5: {len(result.failures) + len(result.errors)} check(s) failed")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
