from dataclasses import dataclass
from enum import StrEnum


class FlagCode(StrEnum):
    """Flag codes for check-in anomalies."""
    OUTSIDE_RADIUS = "OUTSIDE_RADIUS"
    GPS_BORDERLINE = "GPS_BORDERLINE"
    LOW_GPS_ACCURACY = "LOW_GPS_ACCURACY"
    LOCATION_UNAVAILABLE = "LOCATION_UNAVAILABLE"
    LOCATION_STALE = "LOCATION_STALE"
    PASSKEY_UNAVAILABLE = "PASSKEY_UNAVAILABLE"
    NEW_CREDENTIAL = "NEW_CREDENTIAL"
    SHARED_DEVICE = "SHARED_DEVICE"
    DUPLICATE_COORDINATES = "DUPLICATE_COORDINATES"
    IMPLAUSIBLE_ACCURACY = "IMPLAUSIBLE_ACCURACY"
    NETWORK_BURST = "NETWORK_BURST"
    SPOT_CHECK_FAILED = "SPOT_CHECK_FAILED"


@dataclass
class CheckInSignal:
    """Collected signals for check-in decision."""
    qr_fresh: bool
    passkey_verified: bool
    location_available: bool
    latitude: float | None
    longitude: float | None
    accuracy_m: float | None
    distance_m: float | None
    location_timestamp: float | None
    credential_age_hours: float | None
    device_hint: str | None
    network_ip: str | None


@dataclass
class DecisionResult:
    """Result of check-in decision pipeline."""
    status: str
    flag_reasons: list[FlagCode]


def evaluate_location_flags(
    signal: CheckInSignal,
    room_radius_m: float,
    low_accuracy_m: float = 100,
    location_stale_seconds: float = 30,
) -> list[FlagCode]:
    """Evaluate location-based flags."""
    flags = []

    if not signal.location_available:
        flags.append(FlagCode.LOCATION_UNAVAILABLE)
        return flags

    if signal.location_timestamp is None:
        flags.append(FlagCode.LOCATION_STALE)
        return flags

    if signal.accuracy_m is not None and signal.accuracy_m > low_accuracy_m:
        flags.append(FlagCode.LOW_GPS_ACCURACY)

    if signal.distance_m is not None:
        if signal.distance_m > room_radius_m:
            flags.append(FlagCode.OUTSIDE_RADIUS)
        elif signal.distance_m > room_radius_m - (signal.accuracy_m or 0):
            flags.append(FlagCode.GPS_BORDERLINE)

    if signal.accuracy_m == 0:
        flags.append(FlagCode.IMPLAUSIBLE_ACCURACY)

    return flags


def evaluate_passkey_flags(
    signal: CheckInSignal,
    new_credential_flag_hours: float = 24,
) -> list[FlagCode]:
    """Evaluate passkey-based flags."""
    flags = []

    if not signal.passkey_verified:
        flags.append(FlagCode.PASSKEY_UNAVAILABLE)

    if signal.credential_age_hours is not None and signal.credential_age_hours < new_credential_flag_hours:
        flags.append(FlagCode.NEW_CREDENTIAL)

    return flags


def make_decision(
    signal: CheckInSignal,
    room_radius_m: float,
    low_accuracy_m: float = 100,
    location_stale_seconds: float = 30,
    new_credential_flag_hours: float = 24,
) -> DecisionResult:
    """Run the decision pipeline and return status with flag reasons.

    PRESENT only when there is no flag. Otherwise FLAGGED.
    The pipeline never produces ABSENT; only a teacher decision does.
    """
    if not signal.qr_fresh:
        # Stale QR is not a flag - it's a hard failure that should be handled before calling this
        return DecisionResult(status="FLAGGED", flag_reasons=[])

    location_flags = evaluate_location_flags(
        signal,
        room_radius_m,
        low_accuracy_m,
        location_stale_seconds,
    )

    passkey_flags = evaluate_passkey_flags(signal, new_credential_flag_hours)

    all_flags = location_flags + passkey_flags

    if all_flags:
        return DecisionResult(status="FLAGGED", flag_reasons=all_flags)

    return DecisionResult(status="PRESENT", flag_reasons=[])

