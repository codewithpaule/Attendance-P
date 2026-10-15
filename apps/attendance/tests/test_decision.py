
from apps.attendance.domain.decision import (
    CheckInSignal,
    FlagCode,
    evaluate_location_flags,
    evaluate_passkey_flags,
    make_decision,
)


def test_evaluate_location_flags_outside_radius():
    """Test flag when distance exceeds room radius."""
    signal = CheckInSignal(
        qr_fresh=True,
        passkey_verified=True,
        location_available=True,
        latitude=6.5244,
        longitude=3.3792,
        accuracy_m=10,
        distance_m=100,
        location_timestamp=1000,
        credential_age_hours=None,
        device_hint=None,
        network_ip=None,
    )

    flags = evaluate_location_flags(signal, room_radius_m=50)

    assert FlagCode.OUTSIDE_RADIUS in flags


def test_evaluate_location_flags_gps_borderline():
    """Test flag when distance is borderline (within accuracy)."""
    signal = CheckInSignal(
        qr_fresh=True,
        passkey_verified=True,
        location_available=True,
        latitude=6.5244,
        longitude=3.3792,
        accuracy_m=10,
        distance_m=45,
        location_timestamp=1000,
        credential_age_hours=None,
        device_hint=None,
        network_ip=None,
    )

    flags = evaluate_location_flags(signal, room_radius_m=50)

    assert FlagCode.GPS_BORDERLINE in flags


def test_evaluate_location_flags_low_accuracy():
    """Test flag when GPS accuracy is low."""
    signal = CheckInSignal(
        qr_fresh=True,
        passkey_verified=True,
        location_available=True,
        latitude=6.5244,
        longitude=3.3792,
        accuracy_m=150,
        distance_m=30,
        location_timestamp=1000,
        credential_age_hours=None,
        device_hint=None,
        network_ip=None,
    )

    flags = evaluate_location_flags(signal, room_radius_m=50, low_accuracy_m=100)

    assert FlagCode.LOW_GPS_ACCURACY in flags


def test_evaluate_location_flags_unavailable():
    """Test flag when location is unavailable."""
    signal = CheckInSignal(
        qr_fresh=True,
        passkey_verified=True,
        location_available=False,
        latitude=None,
        longitude=None,
        accuracy_m=None,
        distance_m=None,
        location_timestamp=None,
        credential_age_hours=None,
        device_hint=None,
        network_ip=None,
    )

    flags = evaluate_location_flags(signal, room_radius_m=50)

    assert FlagCode.LOCATION_UNAVAILABLE in flags


def test_evaluate_location_flags_stale():
    """Test flag when location timestamp is None."""
    signal = CheckInSignal(
        qr_fresh=True,
        passkey_verified=True,
        location_available=True,
        latitude=6.5244,
        longitude=3.3792,
        accuracy_m=10,
        distance_m=30,
        location_timestamp=None,
        credential_age_hours=None,
        device_hint=None,
        network_ip=None,
    )

    flags = evaluate_location_flags(signal, room_radius_m=50)

    assert FlagCode.LOCATION_STALE in flags


def test_evaluate_location_flags_implausible_accuracy():
    """Test flag when accuracy is exactly 0."""
    signal = CheckInSignal(
        qr_fresh=True,
        passkey_verified=True,
        location_available=True,
        latitude=6.5244,
        longitude=3.3792,
        accuracy_m=0,
        distance_m=30,
        location_timestamp=1000,
        credential_age_hours=None,
        device_hint=None,
        network_ip=None,
    )

    flags = evaluate_location_flags(signal, room_radius_m=50)

    assert FlagCode.IMPLAUSIBLE_ACCURACY in flags


def test_evaluate_location_flags_no_flags():
    """Test no flags when location is valid."""
    signal = CheckInSignal(
        qr_fresh=True,
        passkey_verified=True,
        location_available=True,
        latitude=6.5244,
        longitude=3.3792,
        accuracy_m=10,
        distance_m=30,
        location_timestamp=1000,
        credential_age_hours=None,
        device_hint=None,
        network_ip=None,
    )

    flags = evaluate_location_flags(signal, room_radius_m=50)

    assert len(flags) == 0


def test_evaluate_passkey_flags_unavailable():
    """Test flag when passkey is not verified."""
    signal = CheckInSignal(
        qr_fresh=True,
        passkey_verified=False,
        location_available=True,
        latitude=6.5244,
        longitude=3.3792,
        accuracy_m=10,
        distance_m=30,
        location_timestamp=1000,
        credential_age_hours=None,
        device_hint=None,
        network_ip=None,
    )

    flags = evaluate_passkey_flags(signal)

    assert FlagCode.PASSKEY_UNAVAILABLE in flags


def test_evaluate_passkey_flags_new_credential():
    """Test flag when credential is new."""
    signal = CheckInSignal(
        qr_fresh=True,
        passkey_verified=True,
        location_available=True,
        latitude=6.5244,
        longitude=3.3792,
        accuracy_m=10,
        distance_m=30,
        location_timestamp=1000,
        credential_age_hours=12,
        device_hint=None,
        network_ip=None,
    )

    flags = evaluate_passkey_flags(signal, new_credential_flag_hours=24)

    assert FlagCode.NEW_CREDENTIAL in flags


def test_evaluate_passkey_flags_no_flags():
    """Test no flags when passkey is verified and credential is not new."""
    signal = CheckInSignal(
        qr_fresh=True,
        passkey_verified=True,
        location_available=True,
        latitude=6.5244,
        longitude=3.3792,
        accuracy_m=10,
        distance_m=30,
        location_timestamp=1000,
        credential_age_hours=48,
        device_hint=None,
        network_ip=None,
    )

    flags = evaluate_passkey_flags(signal, new_credential_flag_hours=24)

    assert len(flags) == 0


def test_make_decision_present():
    """Test decision is PRESENT when no flags."""
    signal = CheckInSignal(
        qr_fresh=True,
        passkey_verified=True,
        location_available=True,
        latitude=6.5244,
        longitude=3.3792,
        accuracy_m=10,
        distance_m=30,
        location_timestamp=1000,
        credential_age_hours=48,
        device_hint=None,
        network_ip=None,
    )

    decision = make_decision(signal, room_radius_m=50)

    assert decision.status == "PRESENT"
    assert len(decision.flag_reasons) == 0


def test_make_decision_flagged():
    """Test decision is FLAGGED when there are flags."""
    signal = CheckInSignal(
        qr_fresh=True,
        passkey_verified=True,
        location_available=True,
        latitude=6.5244,
        longitude=3.3792,
        accuracy_m=10,
        distance_m=100,
        location_timestamp=1000,
        credential_age_hours=48,
        device_hint=None,
        network_ip=None,
    )

    decision = make_decision(signal, room_radius_m=50)

    assert decision.status == "FLAGGED"
    assert FlagCode.OUTSIDE_RADIUS in decision.flag_reasons


def test_make_decision_stale_qr():
    """Test decision is FLAGGED when QR is stale."""
    signal = CheckInSignal(
        qr_fresh=False,
        passkey_verified=True,
        location_available=True,
        latitude=6.5244,
        longitude=3.3792,
        accuracy_m=10,
        distance_m=30,
        location_timestamp=1000,
        credential_age_hours=48,
        device_hint=None,
        network_ip=None,
    )

    decision = make_decision(signal, room_radius_m=50)

    assert decision.status == "FLAGGED"
