from dataclasses import dataclass
from math import ceil

DEFAULT_ATTENDANCE_THRESHOLD_PCT = 80
DEFAULT_MIN_SESSIONS_BEFORE_WARNING = 3


@dataclass(frozen=True)
class AttendanceForecast:
    current_percentage: int | None
    projected_percentage: int | None
    maximum_possible_percentage: int | None
    completed_sessions: int
    remaining_sessions: int
    sessions_needed_to_reach_threshold: int
    can_reach_threshold: bool
    below_threshold: bool


def forecast_attendance(
    present_sessions: int,
    completed_sessions: int,
    planned_sessions: int,
    threshold_pct: int = DEFAULT_ATTENDANCE_THRESHOLD_PCT,
) -> AttendanceForecast:
    if min(present_sessions, completed_sessions, planned_sessions) < 0:
        raise ValueError("Session counts cannot be negative")
    if present_sessions > completed_sessions:
        raise ValueError("Present sessions cannot exceed completed sessions")
    if not 0 <= threshold_pct <= 100:
        raise ValueError("Attendance threshold must be between 0 and 100")

    total_sessions = max(planned_sessions, completed_sessions)
    remaining_sessions = total_sessions - completed_sessions
    current_percentage = (
        round(100 * present_sessions / completed_sessions)
        if completed_sessions
        else None
    )
    projected_percentage = (
        round(
            100
            * (present_sessions + current_percentage / 100 * remaining_sessions)
            / total_sessions
        )
        if current_percentage is not None and total_sessions
        else None
    )
    maximum_possible_percentage = (
        round(100 * (present_sessions + remaining_sessions) / total_sessions)
        if total_sessions
        else None
    )
    sessions_needed = max(
        ceil(threshold_pct * total_sessions / 100) - present_sessions,
        0,
    )

    return AttendanceForecast(
        current_percentage=current_percentage,
        projected_percentage=projected_percentage,
        maximum_possible_percentage=maximum_possible_percentage,
        completed_sessions=completed_sessions,
        remaining_sessions=remaining_sessions,
        sessions_needed_to_reach_threshold=sessions_needed,
        can_reach_threshold=sessions_needed <= remaining_sessions,
        below_threshold=current_percentage is not None and current_percentage < threshold_pct,
    )


@dataclass
class EligibilityPolicyData:
    threshold_pct: int
    warning_buffer_pct: int
    trend_window: int
    min_sessions_before_alert: int
    alert_cooldown_days: int


def validate_policy(policy: EligibilityPolicyData) -> list[str]:
    """Validate eligibility policy configuration. Returns list of error messages."""
    errors = []

    if not (0 <= policy.threshold_pct <= 100):
        errors.append("threshold_pct must be between 0 and 100")

    if policy.warning_buffer_pct < 0:
        errors.append("warning_buffer_pct must be non-negative")

    if policy.trend_window < 1:
        errors.append("trend_window must be at least 1")

    if policy.min_sessions_before_alert < 0:
        errors.append("min_sessions_before_alert must be non-negative")

    if policy.alert_cooldown_days < 0:
        errors.append("alert_cooldown_days must be non-negative")

    if policy.threshold_pct + policy.warning_buffer_pct > 100:
        errors.append("threshold_pct + warning_buffer_pct cannot exceed 100")

    return errors
