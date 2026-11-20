# Testing Guide

How to run the test suite for the Low-Resource Linux Music Player.

## Test Layout

| File | What it covers |
|------|----------------|
| `tests/test_slice_1_1.py` | MPD connection, reconnect, `get_status()`, `get_current_song()`, volume/seek |
| `tests/test_slice_1_4.py` | System detection, distro/audio/display detection, MPD config generation, Config schema |
| `tests/test_slice_1_5.py` | Styles, UI widgets, plugin base class, manifest loading, PluginManager basics |
| `tests/test_slice_2_1.py` | PlayStats SQLite: record/queries/retention/CSV export, config defaults |
| `tests/test_slice_2_2.py` | Slice 2.2 query methods + Dashboard `_update_ui` state machine |

## Running the Suite

```bash
# Run everything
python -m unittest discover -s tests -p "test_*.py"

# Run a single file
python -m unittest tests.test_slice_2_2

# Run a single test class
python -m unittest tests.test_slice_2_2.Slice22TestCase

# Run a single test method
python -m unittest tests.test_slice_2_2.Slice22TestCase.test_get_top_tracks_basic
```

The full suite runs headless (no MPD required) because `MusicPlayer` and
`PlayStats` are exercised through mocks and temporary databases. The dashboard
tests spin up a real `tk.Tk()` root window and withdraw it immediately.

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
- Mock `MusicPlayer` with `unittest.mock.MagicMock` (see `MockMusicPlayer` in
  `test_slice_2_2.py` for a richer pattern) rather than spinning up MPD.
- The `check()` helper in `test_slice_2_2.py` raises immediately on failure so
  the suite is green only when every assertion genuinely holds.