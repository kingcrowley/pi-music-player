# Testing Guide

How to run the test suite for the Low-Resource Linux Music Player.

## Test Layout

| File | What it covers |
|------|----------------|
| `tests/test_artwork.py` | Album art extraction + web fallback + LRU cache |
| `tests/test_slice_1_1.py` | MPD connection, reconnect, `get_status()`, `get_current_song()`, volume/seek (manual, needs live MPD) |
| `tests/test_slice_1_4.py` | System detection, distro/audio/display detection, MPD config generation, Config schema |
| `tests/test_slice_1_5.py` | Styles, UI widgets, plugin base class, manifest loading, PluginManager basics |
| `tests/test_slice_2_1.py` | PlayStats SQLite: record/queries/retention/CSV export, config defaults |
| `tests/test_slice_2_2.py` | Slice 2.2 query methods + Dashboard `_update_ui` state machine |
| `tests/test_slice_2_3.py` | Plugin system hardening (shutdown_all, unload hooks, reload, enable/disable) |
| `tests/test_slice_3_1.py` | Recommendation engine: co-occurrence matrix, genre radio, revisit, new-to-you, session rules, live pairing, library scan |

## Running the Suite

### Full suite (discovery command + select manual scripts)

The `unittest discover` pattern `test_*.py` will include `test_slice_1_1.py`, but that file is a manual script with no `unittest.TestCase` class and no `test_` functions — its checks only run through the `run_all_tests()` `__main__` block. The Test Layout table lists it so developers know it exists, but it will not be collected by the discovery command.

To run the full automated suite (all collected tests, excluding the manual script):

```bash
python -m unittest discover -s tests -p "test_*.py"
```

To run the Slice 1.1 MPD acceptance checks (requires a running MPD):

```bash
python3 tests/test_slice_1_1.py
```

### Dashboard tests require a display server

The dashboard tests (`test_slice_1_5.py`) create a real `tk.Tk()` root window and withdraw it immediately. On Linux without an X server or a desktop session, `tk.Tk()` raises an error before the window is withdrawn. To run these tests in headless environments, use a virtual framebuffer:

```bash
xvfb-run -a python -m unittest discover -s tests -p "test_*.py"
```

The discovery command runs headless (no MPD required) because `MusicPlayer` and `PlayStats` are exercised through mocks and temporary databases. It does not execute `tests/test_slice_1_1.py`, which needs a running MPD. The dashboard tests spin up a real `tk.Tk()` root and withdraw it, so they need a display — `xvfb-run` provides a virtual one.

### Slice 1.1 MPD acceptance checks (manual, not collected by discovery)

`tests/test_slice_1_1.py` defines no `unittest.TestCase` class and no `test_` function. Its checks run only through the `run_all_tests()` function under the `__main__` block. The Test Layout table lists this file, and the acceptance criteria require full-suite runs, so a developer who follows this guide can skip these MPD checks without noticing if only using the discovery command.

Use the separate command above to run them.

## Acceptance Criteria

A slice is "done" when:

1. All deliverables implemented
2. Test plan passes on target hardware (Pi Zero 2W)
3. No regressions in previous slices (run the full suite)
4. Code committed with a clear message
5. `config.json` updated if new settings added
6. Memory usage verified (< target for that phase)

## Writing Tests

- Tests live in `tests/test_slice_<X>_<Y>.py` and follow the
  `Slice<N>M>TestCase(unittest.TestCase)` naming convention.
- Use `tempfile.mkdtemp()` for any database or cache file and clean it up in
  `tearDown()` so tests never touch the real `play_stats.db`.
- Mock `MusicPlayer` with `unittest.mock.MagicMock` rather than spinning up MPD.
- The `check()` helper in `test_slice_2_2.py` raises immediately on failure so
  the suite is green only when every assertion genuinely holds.
- The `check()` helper in `test_slice_2_1.py` also raises on failure
  (updated to match Slice 2.2 behavior).
- Do not run `tests/test_slice_1_1.py` under the discovery command; it requires
  a running MPD and runs separately.