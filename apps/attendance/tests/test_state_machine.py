from apps.attendance.domain.state_machine import SessionStatus, can_transition, get_next_status


def test_can_transition_scheduled_to_open():
    transition = can_transition(SessionStatus.SCHEDULED, SessionStatus.OPEN)
    assert transition.is_valid is True
    assert transition.reason is None


def test_can_transition_open_to_closed():
    transition = can_transition(SessionStatus.OPEN, SessionStatus.CLOSED)
    assert transition.is_valid is True
    assert transition.reason is None


def test_can_transition_closed_to_finalized():
    transition = can_transition(SessionStatus.CLOSED, SessionStatus.FINALIZED)
    assert transition.is_valid is True
    assert transition.reason is None


def test_can_transition_invalid():
    transition = can_transition(SessionStatus.OPEN, SessionStatus.SCHEDULED)
    assert transition.is_valid is False
    assert "cannot transition" in transition.reason.lower()


def test_can_transition_same_status():
    transition = can_transition(SessionStatus.OPEN, SessionStatus.OPEN)
    assert transition.is_valid is False
    assert "same status" in transition.reason.lower()


def test_get_next_status_scheduled():
    next_status = get_next_status(SessionStatus.SCHEDULED)
    assert next_status == SessionStatus.OPEN


def test_get_next_status_open():
    next_status = get_next_status(SessionStatus.OPEN)
    assert next_status == SessionStatus.CLOSED


def test_get_next_status_closed():
    next_status = get_next_status(SessionStatus.CLOSED)
    assert next_status == SessionStatus.FINALIZED


def test_get_next_status_finalized():
    next_status = get_next_status(SessionStatus.FINALIZED)
    assert next_status is None
