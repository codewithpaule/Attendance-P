
from apps.academics.domain.policy import EligibilityPolicyData, validate_policy


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
