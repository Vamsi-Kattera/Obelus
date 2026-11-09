import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest

from limits import DemoLimiter, RateLimited


class Clock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


def test_visitor_limit_then_recovers():
    clock = Clock()
    lim = DemoLimiter(per_visitor=2, window_s=60, daily_cap=100, clock=clock)
    lim.check("a"); lim.check("a")
    with pytest.raises(RateLimited) as err:
        lim.check("a")
    assert 1 <= err.value.retry_after <= 60
    lim.check("b")                       # another visitor is unaffected
    clock.t += 61
    lim.check("a")                       # window has passed


def test_daily_cap_applies_to_everyone():
    clock = Clock()
    lim = DemoLimiter(per_visitor=10, window_s=3600, daily_cap=3, clock=clock)
    for v in ("a", "b", "c"):
        lim.check(v)
    with pytest.raises(RateLimited):
        lim.check("d")
    clock.t += 86401
    lim.check("d")


def test_rejected_calls_are_not_counted():
    clock = Clock()
    lim = DemoLimiter(per_visitor=1, window_s=60, daily_cap=2, clock=clock)
    lim.check("a")
    for _ in range(5):
        with pytest.raises(RateLimited):
            lim.check("a")
    lim.check("b")                       # still one slot left in the daily cap
