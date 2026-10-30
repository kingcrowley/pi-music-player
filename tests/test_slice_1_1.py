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

    # Test 1: Connection succeeds
    connected = player.connect()
    check("Connection succeeds", connected)

    if not connected:
        print("\n❌ Cannot proceed — MPD not reachable.")
        print("   Ensure MPD is running: sudo systemctl start mpd")
        print("   Then re-run this test.")
        return False

    # Test 2: connect result reflects actual connection
    check("connect() returns True", player.connect())

    # Test 3: is_connected reflects actual state
    connected_check = player.is_connected()
    check("is_connected() reflects connection", True if connected_check else False,
          f"Is connected: {connected_check}")

    # Test 4: get_status returns valid dict
    status = player.get_status()
    check("get_status() returns dict", isinstance(status, dict))
    check("get_status() has 'state' key", "state" in status)
    check("get_status() has 'volume' key", "volume" in status)

    # Test 5: get_current_song returns dict
    song = player.get_current_song()
    check("get_current_song() returns dict", isinstance(song, dict))

    # Test 6: toggle_play returns success
    toggle_result = player.toggle_play()
    check("toggle_play() returns success", toggle_result is True or toggle_result is None)

    # Test 7: next returns success
    next_result = player.next()
    check("next() returns success", next_result is True or next_result is None)

    # Test 8: stop returns success
    stop_result = player.stop()
    check("stop() returns success", stop_result is True or stop_result is None)

    # Test 9: set_volume(75) returns success and volume applies
    set_vol_result = player.set_volume(75)
    check("set_volume(75) returns success", set_vol_result is True or set_vol_result is None)
    vol = player.get_status()["volume"]
    check("set_volume(75) applies", vol == "75", f"Volume: {vol}")

    # Test 10: play() returns success
    play_result = player.play()
    check("play() returns success", play_result is True or play_result is None)

    # Test 11: previous returns success
    prev_result = player.previous()
    check("previous() returns success", prev_result is True or prev_result is None)

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