from dataclasses import dataclass
from enum import StrEnum


class SessionStatus(StrEnum):
    SCHEDULED = "SCHEDULED"
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    FINALIZED = "FINALIZED"


@dataclass
class SessionTransition:
    from_status: SessionStatus
    to_status: SessionStatus
    is_valid: bool
    reason: str | None = None


def can_transition(from_status: SessionStatus, to_status: SessionStatus) -> SessionTransition:
    """Determine if a session status transition is valid."""
    transitions = {
        SessionStatus.SCHEDULED: [SessionStatus.OPEN],
        SessionStatus.OPEN: [SessionStatus.CLOSED],
        SessionStatus.CLOSED: [SessionStatus.FINALIZED],
        SessionStatus.FINALIZED: [],
    }

    valid_targets = transitions.get(from_status, [])

    if to_status in valid_targets:
        return SessionTransition(from_status, to_status, True, None)

    if from_status == to_status:
        return SessionTransition(from_status, to_status, False, "Cannot transition to same status")

    return SessionTransition(
        from_status,
        to_status,
        False,
        f"Cannot transition from {from_status.value} to {to_status.value}",
    )


def get_next_status(current_status: SessionStatus) -> SessionStatus | None:
    """Get the next valid status for a session (for auto-finalization)."""
    if current_status == SessionStatus.SCHEDULED:
        return SessionStatus.OPEN
    if current_status == SessionStatus.OPEN:
        return SessionStatus.CLOSED
    if current_status == SessionStatus.CLOSED:
        return SessionStatus.FINALIZED
    return None
