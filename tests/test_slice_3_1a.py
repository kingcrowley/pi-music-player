"""Slice 3.1a Touch Toolkit tests.

Headless: gesture logic and momentum, no display needed.
"""

import time
import unittest

from ui.gestures import GestureRecognizer, momentum_step, bind_gestures


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


if __name__ == "__main__":
    unittest.main()
