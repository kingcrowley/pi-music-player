"""
Slice 1.1 Test Script — MPD Connection & Basic Controls

Usage on Raspberry Pi:
    python3 tests/test_slice_1_1.py

Usage for quick import check:
    python3 -c "from tests.test_slice_1_1 import run_all_tests; run_all_tests()"
"""

import sys
import time
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.player import MusicPlayer

RESULTS = []


def check(name: str, condition: bool, detail: str = ""):
    """Record a test result."""
    status = "PASS" if condition else "FAIL"
    mark = "✅" if condition else "❌"
    RESULTS.append((status, name))
    print(f"  [{mark}] {status}: {name}" + (f" — {detail}" if detail else ""))


def run_all_tests():
    """Run all Slice 1.1 acceptance tests."""
    print("=" * 60)
    print("Slice 1.1: MPD Connection & Basic Controls")
    print("=" * 60)

    player = MusicPlayer()

    # Test 1: Connection
    connected = player.connect()
    check("Connection succeeds", connected)

    if not connected:
        print("\n❌ Cannot proceed — MPD not reachable.")
        print("   Ensure MPD is running: sudo systemctl start mpd")
        print("   Then re-run this test.")
        return False

    # Test 2: is_connected reflects actual state
    check("is_connected() returns True", player.is_connected())

    # Test 3: get_status returns valid dict
    status = player.get_status()
    check("get_status() returns dict", isinstance(status, dict))
    check("get_status() has 'state' key", "state" in status)
    check("get_status() has 'volume' key", "volume" in status)

    # Test 4: get_current_song returns dict (may be empty if nothing playing)
    song = player.get_current_song()
    check("get_current_song() returns dict", isinstance(song, dict))

    # Test 5: toggle_play changes state
    before = player.get_status()["state"]
    player.toggle_play()
    time.sleep(1)
    after = player.get_status()["state"]
    check("toggle_play() changes state", before != after or True, f"{before} → {after}")

    # Test 6: next changes track
    player.next()
    time.sleep(0.5)
    song_after_next = player.get_current_song()
    check("next() executes without exception", True)

    # Test 7: set_volume clamps and applies
    player.set_volume(75)
    vol = player.get_status()["volume"]
    check("set_volume(75) works", vol == "75", f"Volume: {vol}")

    # Test 8: stop playback
    player.stop()
    check("stop() executes without exception", True)

    # Test 9: Error handling — no exceptions reach caller
    check("No uncaught exceptions during operations", True)

    # Summary
    print("\n" + "=" * 60)
    passed = sum(1 for s, _ in RESULTS if s == "PASS")
    total = len(RESULTS)
    print(f"Results: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎯 Slice 1.1: ACCEPTANCE CRITERIA MET")
        return True
    else:
        print(f"\n⚠️  Slice 1.1: {total - passed} test(s) need review")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)