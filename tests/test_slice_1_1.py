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

    # Test 6: toggle_play returns True
    toggle_result = player.toggle_play()
    check("toggle_play() returns True", toggle_result is True, f"Result: {toggle_result}")

    # Test 7: next returns True
    next_result = player.next()
    check("next() returns True", next_result is True, f"Result: {next_result}")

    # Test 8: stop returns True
    stop_result = player.stop()
    check("stop() returns True", stop_result is True, f"Result: {stop_result}")

    # Test 9: set_volume(75) returns True and volume applies
    set_vol_result = player.set_volume(75)
    check("set_volume(75) returns True", set_vol_result is True, f"Result: {set_vol_result}")
    vol = player.get_status()["volume"]
    check("set_volume(75) applies", vol == "75", f"Volume: {vol}")

    # Test 10: play() returns True
    play_result = player.play()
    check("play() returns True", play_result is True, f"Result: {play_result}")

    # Test 11: previous returns True
    prev_result = player.previous()
    check("previous() returns True", prev_result is True, f"Result: {prev_result}")

    # Test 12: Stop playback after all tests to clean up
    player.stop()
    final_status = player.get_status()
    check("MPD is stopped after tests", final_status.get("state") != "play",
          f"Final state: {final_status.get('state')}")

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