
from apps.academics.domain.policy import (
    DEFAULT_ATTENDANCE_THRESHOLD_PCT,
    EligibilityPolicyData,
    forecast_attendance,
    validate_policy,
)


def test_default_attendance_forecast_uses_80_percent_threshold():
    assert DEFAULT_ATTENDANCE_THRESHOLD_PCT == 80


def test_attendance_forecast_reports_recoverable_shortfall():
    forecast = forecast_attendance(
        present_sessions=3,
        completed_sessions=4,
        planned_sessions=20,
    )

    assert forecast.current_percentage == 75
    assert forecast.projected_percentage == 75
    assert forecast.maximum_possible_percentage == 95
    assert forecast.sessions_needed_to_reach_threshold == 13
    assert forecast.remaining_sessions == 16
    assert forecast.can_reach_threshold
    assert forecast.below_threshold


def test_attendance_forecast_reports_unreachable_threshold():
    forecast = forecast_attendance(
        present_sessions=1,
        completed_sessions=4,
        planned_sessions=5,
    )

    assert forecast.current_percentage == 25
    assert forecast.maximum_possible_percentage == 40
    assert forecast.sessions_needed_to_reach_threshold == 3
    assert forecast.remaining_sessions == 1
    assert not forecast.can_reach_threshold


def test_attendance_forecast_handles_no_completed_sessions():
    forecast = forecast_attendance(
        present_sessions=0,
        completed_sessions=0,
        planned_sessions=10,
    )

    assert forecast.current_percentage is None
    assert forecast.projected_percentage is None
    assert forecast.maximum_possible_percentage == 100
    assert forecast.sessions_needed_to_reach_threshold == 8
    assert forecast.can_reach_threshold


def test_validate_policy_valid():
    policy = EligibilityPolicyData(
        threshold_pct=75,
        warning_buffer_pct=8,
        trend_window=4,
        min_sessions_before_alert=3,
        alert_cooldown_days=7,
    )
    errors = validate_policy(policy)
    assert errors == []


def test_validate_policy_invalid_threshold():
    policy = EligibilityPolicyData(
        threshold_pct=150,
        warning_buffer_pct=8,
        trend_window=4,
        min_sessions_before_alert=3,
        alert_cooldown_days=7,
    )
    errors = validate_policy(policy)
    assert len(errors) == 2
    assert "threshold_pct" in errors[0]


def test_validate_policy_negative_buffer():
    policy = EligibilityPolicyData(
        threshold_pct=75,
        warning_buffer_pct=-5,
        trend_window=4,
        min_sessions_before_alert=3,
        alert_cooldown_days=7,
    )
    errors = validate_policy(policy)
    assert len(errors) == 1
    assert "warning_buffer_pct" in errors[0]


def test_validate_policy_threshold_plus_buffer_exceeds_100():
    policy = EligibilityPolicyData(
        threshold_pct=75,
        warning_buffer_pct=30,
        trend_window=4,
        min_sessions_before_alert=3,
        alert_cooldown_days=7,
    )
    errors = validate_policy(policy)
    assert len(errors) == 1
    assert "exceed 100" in errors[0]
