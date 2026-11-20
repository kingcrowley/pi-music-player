"""Slice 2.3 Test Suite — Plugin System Hardening

Tests for Slice 2.3 deliverables:
- PluginManager.shutdown_all() callable as instance method (fixes AttributeError)
- Plugin enable/disable without unload
- Plugin reload preserves source directory
- Hook dispatch respects enabled state
- Plugin lifecycle: load -> init -> hook registration -> shutdown
"""

import sys
import os
import json
import tempfile
import shutil
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.plugin_base import MusicPlayerPlugin
from plugins import PluginManager


# A minimal test plugin implementation — a concrete subclass we can
# import from a temp module file.
class TestFeaturePlugin(MusicPlayerPlugin):
    """Simple feature plugin for lifecycle testing."""

    def __init__(self, config):
        super().__init__(config)
        self.init_called = False
        self.shutdown_called = False
        self.hook_fired = []

    def initialize(self, core):
        self.core = core
        self._set_initialized(True)
        self.init_called = True
        # Register a hook
        self.register_hook("on_test_event", self._on_test_event)
        return True

    def _on_test_event(self, *args, **kwargs):
        self.hook_fired.append((args, kwargs))

    def shutdown(self):
        self.shutdown_called = True

    def get_capabilities(self):
        return ["test-capability"]


def _make_temp_plugin_dir(plugin_id="test-plugin", plugin_name="Test Plugin", dir_name=None):
    """Create a temporary plugin directory with manifest + Python module.

    Args:
        plugin_id: The plugin_id in the manifest.
        plugin_name: Human-readable name in the manifest.
        dir_name: Directory name (defaults to plugin_id if None).

    Returns the Path to the created plugin directory.
    """
    tmpdir = Path(tempfile.mkdtemp())
    dir_name = dir_name or plugin_id
    plugin_dir = tmpdir / dir_name
    plugin_dir.mkdir(exist_ok=True)

    # Manifest
    manifest = {
        "plugin_id": plugin_id,
        "name": plugin_name,
        "version": "1.0.0",
        "type": "feature",
        "capabilities": ["test-capability"],
        "auto_load": True,
    }
    with open(plugin_dir / "config.json", "w") as f:
        json.dump(manifest, f)

    # Module — a standalone .py file that defines MusicPlayerPlugin subclass
    module_code = f'''import sys
from core.plugin_base import MusicPlayerPlugin

class MusicPlayerPlugin(MusicPlayerPlugin):
    def __init__(self, config):
        super().__init__(config)
        self.init_called = False
        self.shutdown_called = False
        self.hook_fired = []

    def initialize(self, core):
        self.core = core
        self._set_initialized(True)
        self.init_called = True
        self.register_hook("on_test_event", self._on_test_event)
        return True

    def _on_test_event(self, *args, **kwargs):
        self.hook_fired.append((args, kwargs))

    def shutdown(self):
        self.shutdown_called = True

    def get_capabilities(self):
        return ["test-capability"]
'''
    with open(plugin_dir / f"{plugin_id}.py", "w", encoding="utf-8") as f:
        f.write(module_code)

    return tmpdir


class Slice23TestCase(unittest.TestCase):
    """Unit tests for Plugin System Hardening (Slice 2.3)."""

    def setUp(self):
        self.tmpdirs = []

    def tearDown(self):
        for d in self.tmpdirs:
            shutil.rmtree(d, ignore_errors=True)

    def test_shutdown_all_is_instance_method(self):
        """PluginManager.shutdown_all() is callable as instance method."""
        mgr = PluginManager(core_engine=None, plugin_dir="plugins")
        mgr.shutdown_all()  # Should not raise AttributeError

    def test_plugin_load_initializes_and_registers_hooks(self):
        """Loading a plugin runs initialize() and registers declared hooks."""
        tmpdir = _make_temp_plugin_dir("lt", "Load Test")
        self.tmpdirs.append(tmpdir)
        plugin_dir = Path(tmpdir) / "lt"
        mgr = PluginManager(core_engine=None, plugin_dir=str(tmpdir))
        loaded = mgr.load_plugin_from_dir(plugin_dir)
        self.assertIsNotNone(loaded, "Plugin loads successfully")
        self.assertTrue(loaded.init_called, "initialize() was called")
        # Hook was registered with the manager
        self.assertIn("on_test_event", mgr.hooks)

    def test_plugin_unload_calls_shutdown(self):
        """Unloading a plugin calls shutdown()."""
        tmpdir = _make_temp_plugin_dir("ut", "Unload Test")
        self.tmpdirs.append(tmpdir)
        plugin_dir = Path(tmpdir) / "ut"
        mgr = PluginManager(core_engine=None, plugin_dir=str(tmpdir))
        plugin = mgr.load_plugin_from_dir(plugin_dir)
        self.assertIsNotNone(plugin)
        self.assertFalse(plugin.shutdown_called)

        mgr.unload_plugin(plugin.config.get("plugin_id", "ut"))
        self.assertTrue(plugin.shutdown_called, "shutdown() was called")

    def test_plugin_enable_disable(self):
        """enable_plugin/disable_plugin toggle without unload."""
        tmpdir = _make_temp_plugin_dir("et", "Enable Test")
        self.tmpdirs.append(tmpdir)
        plugin_dir = Path(tmpdir) / "et"
        mgr = PluginManager(core_engine=None, plugin_dir=str(tmpdir))
        plugin = mgr.load_plugin_from_dir(plugin_dir)
        self.assertIsNotNone(plugin)
        pid = plugin.config.get("plugin_id", "et")

        # Initially enabled
        self.assertTrue(mgr._enabled.get(pid))

        # Disable
        mgr.disable_plugin(pid)
        self.assertFalse(mgr._enabled.get(pid))

        # Re-enable
        mgr.enable_plugin(pid)
        self.assertTrue(mgr._enabled.get(pid))

    def test_disabled_plugin_hooks_not_fired(self):
        """Hook callbacks for disabled plugins are skipped."""
        tmpdir = _make_temp_plugin_dir("ht", "Hook Test")
        self.tmpdirs.append(tmpdir)
        plugin_dir = Path(tmpdir) / "ht"
        mgr = PluginManager(core_engine=None, plugin_dir=str(tmpdir))
        plugin = mgr.load_plugin_from_dir(plugin_dir)
        self.assertIsNotNone(plugin)
        pid = plugin.config.get("plugin_id", "ht")

        mgr.disable_plugin(pid)
        mgr.trigger_hook("on_test_event", "arg1", kw="val")
        self.assertEqual(len(plugin.hook_fired), 0, "Disabled plugin hooks not fired")

        mgr.enable_plugin(pid)
        mgr.trigger_hook("on_test_event", "arg1", kw="val")
        self.assertEqual(len(plugin.hook_fired), 1, "Enabled plugin hooks fired")
        self.assertEqual(plugin.hook_fired[0], (("arg1",), {"kw": "val"}))

    def test_plugin_reload_preserves_source_dir(self):
        """reload_plugin unloads then reloads from the original source directory.

        The fixture directory name (rt_src) deliberately differs from the
        manifest plugin_id (rt). Without the recorded-source-directory branch,
        reload_plugin falls back to load_plugin("rt"), which looks for a
        directory named "rt" and fails — so this test actually exercises the
        source-directory preservation logic.
        """
        tmpdir = _make_temp_plugin_dir("rt", "Reload Test", dir_name="rt_src")
        self.tmpdirs.append(tmpdir)
        plugin_dir = Path(tmpdir) / "rt_src"
        mgr = PluginManager(core_engine=None, plugin_dir=str(tmpdir))
        plugin = mgr.load_plugin_from_dir(plugin_dir)
        self.assertIsNotNone(plugin)
        self.assertTrue(plugin.init_called)
        pid = plugin.config.get("plugin_id", "rt")

        # Reload
        ok = mgr.reload_plugin(pid)
        self.assertTrue(ok, "reload_plugin returns True")

        # New instance should be loaded and initialized
        new_plugin = mgr.get_plugin(pid)
        self.assertIsNotNone(new_plugin)
        self.assertTrue(new_plugin.init_called)
        # Should be a different instance object
        self.assertIsNot(plugin, new_plugin, "New instance after reload")

    def test_shutdown_all_cleans_up_all_plugins(self):
        """shutdown_all() shuts down every loaded plugin."""
        mgr = PluginManager(core_engine=None, plugin_dir="plugins")

        # Load two test plugins
        dir1 = _make_temp_plugin_dir("sd1", "SD 1")
        dir2 = _make_temp_plugin_dir("sd2", "SD 2")
        self.tmpdirs.extend([dir1, dir2])
        # _make_temp_plugin_dir returns parent tmpdir; plugin is in subdir
        p1 = mgr.load_plugin_from_dir(dir1 / "sd1")
        p2 = mgr.load_plugin_from_dir(dir2 / "sd2")

        self.assertFalse(p1.shutdown_called)
        self.assertFalse(p2.shutdown_called)

        mgr.shutdown_all()

        self.assertTrue(p1.shutdown_called, "Plugin 1 shutdown called")
        self.assertTrue(p2.shutdown_called, "Plugin 2 shutdown called")
        self.assertEqual(len(mgr.plugins), 0, "All plugins removed")

    def test_get_plugins_with_capability(self):
        """get_plugins_with_capability returns matching plugins."""
        tmpdir = _make_temp_plugin_dir("ct", "Cap Test")
        self.tmpdirs.append(tmpdir)
        plugin_dir = Path(tmpdir) / "ct"
        mgr = PluginManager(core_engine=None, plugin_dir=str(tmpdir))
        plugin = mgr.load_plugin_from_dir(plugin_dir)
        self.assertIsNotNone(plugin)

        matches = mgr.get_plugins_with_capability("test-capability")
        self.assertIn(plugin, matches)

        matches = mgr.get_plugins_with_capability("nonexistent-cap")
        self.assertEqual(matches, [])

    def test_get_plugins_by_type(self):
        """get_plugins_by_type returns plugins of the given type."""
        tmpdir = _make_temp_plugin_dir("tt", "Type Test")
        self.tmpdirs.append(tmpdir)
        plugin_dir = Path(tmpdir) / "tt"
        mgr = PluginManager(core_engine=None, plugin_dir=str(tmpdir))
        plugin = mgr.load_plugin_from_dir(plugin_dir)
        self.assertIsNotNone(plugin)

        matches = mgr.get_plugins_by_type("feature")
        self.assertIn(plugin, matches)

        matches = mgr.get_plugins_by_type("audio-backend")
        self.assertEqual(matches, [])

    def test_plugin_manifest_auto_load_false_skipped(self):
        """Plugins with auto_load: false are skipped by load_all_plugins()."""
        tmpdir = Path(tempfile.mkdtemp())
        self.tmpdirs.append(tmpdir)
        plugin_dir = Path(tmpdir) / "no-auto"
        plugin_dir.mkdir(exist_ok=True)

        manifest = {
            "plugin_id": "no-auto",
            "name": "No Auto",
            "version": "1.0.0",
            "type": "feature",
            "auto_load": False,
        }
        with open(plugin_dir / "config.json", "w") as f:
            json.dump(manifest, f)

        # Module (required even if auto_load:false, for the loader to find it)
        module_code = '''from core.plugin_base import MusicPlayerPlugin
class MusicPlayerPlugin(MusicPlayerPlugin):
    def initialize(self, core):
        return True
    def get_capabilities(self):
        return ["test"]'''
        with open(plugin_dir / "no_auto.py", "w", encoding="utf-8") as f:
            f.write(module_code)

        mgr = PluginManager(core_engine=None, plugin_dir=str(tmpdir))
        loaded_count = mgr.load_all_plugins()
        self.assertEqual(loaded_count, 0, "auto_load: false plugins are skipped")


def run_all_tests():
    """Run all Slice 2.3 acceptance tests."""
    print("=" * 60)
    print("Slice 2.3: Plugin System Hardening")
    print("=" * 60)

    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(Slice23TestCase)
    runner = unittest.TextTestRunner(verbosity=1)
    result = runner.run(suite)

    if result.wasSuccessful():
        print("\n[OK] Slice 2.3: ACCEPTANCE CRITERIA MET")
        return True
    else:
        print(f"\n[WARN] Slice 2.3: {len(result.failures) + len(result.errors)} check(s) failed")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)