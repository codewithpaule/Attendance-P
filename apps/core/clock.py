from datetime import UTC, datetime
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime: ...


class DefaultClock:
    def now(self) -> datetime:
        return datetime.now(UTC)
