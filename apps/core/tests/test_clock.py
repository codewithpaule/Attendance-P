from datetime import UTC, datetime

from apps.core.clock import DefaultClock


def test_default_clock_returns_utc():
    clock = DefaultClock()
    now = clock.now()
    assert isinstance(now, datetime)
    assert now.tzinfo == UTC
