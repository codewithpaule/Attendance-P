from dataclasses import dataclass

DEFAULT_ATTENDANCE_THRESHOLD_PCT = 80
DEFAULT_MIN_SESSIONS_BEFORE_WARNING = 3


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
