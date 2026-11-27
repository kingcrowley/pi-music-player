"""Slice 3.1a Touch Toolkit tests.

Headless: gesture logic and momentum (no display needed).
Tk tests: ScrollList scrolling/momentum/tap (need a display; skip headless).
"""

import time
import unittest

from ui.gestures import GestureRecognizer, momentum_step, bind_gestures


def _tk_available():
    try:
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        root.destroy()
        return True
    except Exception:
        return False


TK_AVAILABLE = _tk_available()


class FakeWidth:
    """Callable returning a fixed window width."""

    def __init__(self, width):
        self.width = width

    def __call__(self):
        return self.width


def _run(recognizer, actions):
    """Run a sequence of (method, *args) on the recognizer, collect events."""
    events = []
    for action in actions:
        name = action[0]
        args = action[1:]
        events.extend(getattr(recognizer, name)(*args))
    return events


def _final_events(events):
    return [e for e in events if e[0] in ("tap", "long_press", "drag_end", "swipe")]


class GestureContractTestCase(unittest.TestCase):
    """Assert the recognizer contract: 0+ drag_move, then exactly one final."""

    def test_press_stays_under_slop(self):
        r = GestureRecognizer(FakeWidth(800))
        events = _run(r, [
            ("press", 0, 0, 0.0),
            ("move", 5, 0, 0.01),
            ("move", 5, 0, 0.02),
            ("release", 5, 0, 0.05),
        ])
        self.assertEqual(events, [("tap",)])

    def test_10px_is_tap(self):
        r = GestureRecognizer(FakeWidth(800))
        events = _run(r, [
            ("press", 0, 0, 0.0),
            ("move", 10, 0, 0.02),
            ("release", 10, 0, 0.05),
        ])
        self.assertEqual(events, [("tap",)])

    def test_11px_is_drag(self):
        r = GestureRecognizer(FakeWidth(800))
        events = _run(r, [
            ("press", 0, 0, 0.0),
            ("move", 11, 0, 0.02),
            ("release", 11, 0, 0.05),
        ])
        self.assertTrue(any(e[0] == "drag_move" for e in events))
        self.assertEqual(events[-1][0], "drag_end")

    def test_long_press_timeout(self):
        r = GestureRecognizer(FakeWidth(800))
        events = _run(r, [
            ("press", 0, 0, 0.0),
            ("timeout", 0.51),
        ])
        self.assertEqual(events, [("long_press",)])

    def test_long_press_release_late_timer(self):
        # Held 520 ms, released before the timeout was delivered -> long_press.
        r = GestureRecognizer(FakeWidth(800))
        events = _run(r, [
            ("press", 0, 0, 0.0),
            ("release", 0, 0, 0.52),
        ])
        self.assertEqual(events, [("long_press",)])

    def test_timeout_after_release_is_nothing(self):
        r = GestureRecognizer(FakeWidth(800))
        events = _run(r, [
            ("press", 0, 0, 0.0),
            ("release", 0, 0, 0.05),
            ("timeout", 0.51),
        ])
        self.assertEqual(events, [("tap",)])

    def test_long_press_then_release_is_silent(self):
        r = GestureRecognizer(FakeWidth(800))
        events = _run(r, [
            ("press", 0, 0, 0.0),
            ("timeout", 0.51),
            ("release", 0, 0, 0.6),
        ])
        self.assertEqual(events, [("long_press",)])

    def test_drag_cancels_long_press(self):
        r = GestureRecognizer(FakeWidth(800))
        events = _run(r, [
            ("press", 0, 0, 0.0),
            ("move", 11, 0, 0.02),
            ("timeout", 0.51),   # too late: drag already started
            ("release", 11, 0, 0.52),
        ])
        self.assertTrue(any(e[0] == "drag_move" for e in events))
        self.assertEqual(events[-1][0], "drag_end")
        self.assertNotIn("long_press", [e[0] for e in events])

    def test_swipe_left(self):
        # 100 px movement leftwards (dx < 0) at width 800 -> threshold max(80, 80) = 80; swipe passes.
        r = GestureRecognizer(FakeWidth(800))
        events = _run(r, [
            ("press", 100, 0, 0.0),
            ("move", 0, 0, 0.02),
            ("release", 0, 0, 0.03),
        ])
        self.assertEqual(events[-1][0], "swipe")
        self.assertEqual(events[-1][1], "left")

    def test_swipe_right(self):
        # 100 px movement rightwards (dx > 0) -> swipe "right".
        r = GestureRecognizer(FakeWidth(800))
        events = _run(r, [
            ("press", 0, 0, 0.0),
            ("move", 100, 0, 0.02),
            ("release", 100, 0, 0.03),
        ])
        self.assertEqual(events[-1][0], "swipe")
        self.assertEqual(events[-1][1], "right")

    def test_swipe_wide_width_is_drag_end(self):
        # width 1200 -> threshold max(80, 120) = 120; 100 px too small.
        r = GestureRecognizer(FakeWidth(1200))
        events = _run(r, [
            ("press", 0, 0, 0.0),
            ("move", 100, 0, 0.02),
            ("release", 100, 0, 0.03),
        ])
        self.assertEqual(events[-1][0], "drag_end")

    def test_diagonal_fails_swipe_test(self):
        # dx=100, dy=100 -> |dx| is not > 2*|dy| -> drag_end, not swipe.
        r = GestureRecognizer(FakeWidth(800))
        events = _run(r, [
            ("press", 0, 0, 0.0),
            ("move", 100, 100, 0.02),
            ("release", 100, 100, 0.03),
        ])
        self.assertEqual(events[-1][0], "drag_end")

    def test_slow_horizontal_move_is_not_swipe(self):
        # 500 ms > 400 ms swipe max -> drag_end.
        r = GestureRecognizer(FakeWidth(800))
        events = _run(r, [
            ("press", 0, 0, 0.0),
            ("move", 100, 0, 0.5),
            ("release", 100, 0, 0.51),
        ])
        self.assertEqual(events[-1][0], "drag_end")

    def test_release_point_past_slop_is_drag(self):
        # Press and release 50 px apart with no motion events -> drag_end.
        r = GestureRecognizer(FakeWidth(800))
        events = _run(r, [
            ("press", 0, 0, 0.0),
            ("release", 50, 0, 0.05),
        ])
        self.assertEqual(events[-1][0], "drag_end")

    def test_multiple_drag_moves_then_one_final(self):
        r = GestureRecognizer(FakeWidth(800))
        events = _run(r, [
            ("press", 0, 0, 0.0),
            ("move", 5, 0, 0.01),
            ("move", 11, 0, 0.02),
            ("move", 22, 0, 0.03),
            ("release", 22, 0, 0.05),
        ])
        self.assertTrue(len([e for e in events if e[0] == "drag_move"]) > 0)
        self.assertEqual(len(_final_events(events)), 1)
        self.assertEqual(events[-1][0], "drag_end")

    def test_every_sequence_has_at_most_one_final(self):
        sequences = [
            [("press", 0, 0, 0.0), ("release", 0, 0, 0.05)],
            [("press", 0, 0, 0.0), ("timeout", 0.51), ("release", 0, 0, 0.6)],
            [("press", 0, 0, 0.0), ("move", 50, 0, 0.02), ("release", 50, 0, 0.03)],
            [("press", 0, 0, 0.0), ("move", 11, 0, 0.02), ("release", 11, 0, 0.02)],
        ]
        for seq in sequences:
            events = _run(GestureRecognizer(FakeWidth(800)), seq)
            self.assertLessEqual(len(_final_events(events)), 1, seq)


class MomentumTestCase(unittest.TestCase):
    """Momentum speed step is a pure function."""

    def test_momentum_applies_friction(self):
        self.assertAlmostEqual(momentum_step(100.0), 90.0)
        self.assertAlmostEqual(momentum_step(100.0, friction=0.5), 50.0)
        self.assertAlmostEqual(momentum_step(0.0), 0.0)
        self.assertAlmostEqual(momentum_step(100.0, friction=0.0), 0.0)

    def test_momentum_decays_to_zero(self):
        speed = 100.0
        for _ in range(100):
            speed = momentum_step(speed)
        self.assertLess(speed, 1.0)


class ScrollListMomentumUnitTests(unittest.TestCase):
    """ScrollList momentum logic, tested through a real Tk canvas.

    These drive ``_momentum_tick`` directly (no event-loop waiting) so the
    stopping point, the end-clamping and the new-press cancel are all
    exercised without real time passing.
    """

    def setUp(self):
        if not TK_AVAILABLE:
            self.skipTest("no display available")
        import tkinter as tk
        from ui.widget import ScrollList, TouchButton

        self.root = tk.Tk()
        self.root.withdraw()
        self.root.geometry("400x400")
        self.list = ScrollList(self.root)
        self.list.pack(fill=tk.BOTH, expand=True)
        # A tall list so there is room to scroll.
        rows = []
        for i in range(100):
            rows.append({"label": "Row %d" % i})
        self.list.set_items(rows, lambda parent, item: TouchButton(
            parent, text=item["label"], command=lambda: None))
        self.root.update()

    def tearDown(self):
        try:
            self.root.destroy()
        except Exception:
            pass

    def test_momentum_stops_below_threshold(self):
        # Start at a low speed; a few ticks should stop it.
        self.list._start_momentum(0.4)  # below the 1 px/s start guard
        self.assertEqual(self.list._mom_speed, 0.0)
        self.assertIsNone(self.list._mom_job)

    def test_momentum_decays_and_stops(self):
        # Start at a high speed and tick until it stops.
        self.list._start_momentum(5000.0)
        self.assertGreater(abs(self.list._mom_speed), 0.5)
        # Drive ticks synchronously.
        for _ in range(500):
            self.list._momentum_tick()
            if self.list._mom_job is None:
                break
        self.assertEqual(self.list._mom_speed, 0.0)

    def test_new_press_cancels_momentum(self):
        self.list._start_momentum(5000.0)
        self.assertIsNotNone(self.list._mom_job)
        self.list._stop_momentum()
        self.assertIsNone(self.list._mom_job)
        self.assertEqual(self.list._mom_speed, 0.0)

    def test_momentum_stops_at_list_end(self):
        # Scroll to near the bottom, then momentum downward stops.
        self.list._canvas.yview_moveto(0.99)
        self.root.update()
        self.list._start_momentum(5000.0)
        for _ in range(50):
            self.list._momentum_tick()
            if self.list._mom_job is None:
                break
        # Either it stopped at the end or ran out of speed — but no crash.
        self.assertIsNone(self.list._mom_job)


@unittest.skipUnless(TK_AVAILABLE, "no display available")
class ScrollListTkAdapterTests(unittest.TestCase):
    """Tk adapter tests: drag on a row scrolls and does not fire the button."""

    def setUp(self):
        import tkinter as tk
        from ui.widget import ScrollList, TouchButton

        self.root = tk.Tk()
        self.root.withdraw()
        self.root.geometry("400x600")
        self.fired = []

        self.list = ScrollList(self.root)
        self.list.pack(fill=tk.BOTH, expand=True)

        rows = []
        for i in range(60):
            rows.append({"label": "Row %d" % i})
        self.list.set_items(rows, lambda parent, item: TouchButton(
            parent, text=item["label"], command=lambda i=item: self.fired.append(i)))
        self.root.update()

    def tearDown(self):
        try:
            self.root.destroy()
        except Exception:
            pass

    def _row_at(self, index):
        return self.list._inner.winfo_children()[index]

    def test_drag_on_row_scrolls_and_does_not_fire_button(self):
        row = self._row_at(20)
        # Generate a press, several motions, and a release on the row.
        row.event_generate("<ButtonPress-1>", x=100, y=10)
        self.root.update()
        for dy in (20, 40, 60, 80):
            row.event_generate("<B1-Motion>", x=100, y=10 + dy)
            self.root.update()
        row.event_generate("<ButtonRelease-1>", x=100, y=90)
        self.root.update()
        # The button command must NOT have fired.
        self.assertEqual(self.fired, [])
        # The list should have scrolled (yview moved from top).
        self.assertGreater(self.list._canvas.yview()[0], 0.0)

    def test_tap_on_row_calls_on_select(self):
        selected = []
        self.list.on_select(lambda item: selected.append(item))
        row = self._row_at(10)
        row.event_generate("<ButtonPress-1>", x=100, y=10)
        self.root.update()
        row.event_generate("<ButtonRelease-1>", x=100, y=10)
        self.root.update()
        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0]["label"], "Row 10")


if __name__ == "__main__":
    unittest.main()
