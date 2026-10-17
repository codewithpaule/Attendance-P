from datetime import timedelta

from django.conf import settings
from django.db import transaction

from apps.accounts.adapters.webauthn import WebAuthnAdapterImpl
from apps.accounts.models import PasskeyCredential, User
from apps.attendance.adapters.qr import DjangoQRTokenAdapter, QRTokenError
from apps.attendance.domain.decision import FlagCode, make_decision
from apps.attendance.domain.geo import haversine_distance
from apps.attendance.models import CheckIn, CheckInAttempt, ClassSession
from apps.attendance.selectors.functions import (
    get_checkin_for_student,
    get_pending_checkin_attempt_for_session,
)
from apps.attendance.services.session import close_session_if_due
from apps.audit.services.record import record
from apps.core.clock import Clock
from apps.core.exceptions import BadRequestError, ConflictError, NotFoundError


@transaction.atomic
def begin_checkin(
    session_id: str,
    student: User,
    qr_token: str,
    device_hint: str,
    clock: Clock,
    max_age_seconds: int = 20,
) -> CheckInAttempt:
    """Begin the check-in process by creating a CheckInAttempt with a WebAuthn challenge."""
    session = ClassSession.objects.filter(id=session_id).select_related("room").first()
    if not session:
        raise NotFoundError("SESSION_NOT_FOUND", "Session not found")

    now = clock.now()
    close_session_if_due(session, now)
    if session.status != ClassSession.Status.OPEN:
        raise BadRequestError("SESSION_NOT_OPEN", "Session is not open")

    # Verify QR token
    adapter = DjangoQRTokenAdapter(max_age_seconds=max_age_seconds)
    try:
        if not adapter.verify_token(qr_token, session_id):
            raise BadRequestError("QR_TOKEN_INVALID", "Invalid QR token")
    except QRTokenError as err:
        record(
            actor=student,
            action="CHECKIN_BEGIN_QR_EXPIRED",
            target_type="ClassSession",
            target_id=str(session.id),
            metadata={"qr_token": qr_token},
        )
        raise BadRequestError("QR_TOKEN_EXPIRED", "QR token expired or invalid") from err

    # Check if student is enrolled
    from apps.academics.selectors import get_enrollments_for_student

    enrollments = get_enrollments_for_student(student)
    if not any(enrollment.course_id == session.course_id for enrollment in enrollments):
        raise BadRequestError("NOT_ENROLLED", "Student is not enrolled in this course")

    if session.scheduled_start_at and now < session.scheduled_start_at - timedelta(
        minutes=settings.CHECKIN_PREOPEN_MINUTES
    ):
        raise BadRequestError(
            "CHECKIN_NOT_OPEN",
            f"Check-in opens {settings.CHECKIN_PREOPEN_MINUTES} minutes before class starts",
        )
    if session.scheduled_end_at and now >= session.scheduled_end_at:
        raise BadRequestError("CHECKIN_WINDOW_CLOSED", "The scheduled class has ended")
    if (
        not session.scheduled_end_at
        and session.opened_at
        and now > session.opened_at + timedelta(minutes=session.checkin_window_minutes)
    ):
        raise BadRequestError("CHECKIN_WINDOW_CLOSED", "Check-in window has closed")

    # Check for existing pending attempt
    existing_attempt = get_pending_checkin_attempt_for_session(session_id, str(student.id))
    if existing_attempt:
        existing_attempt.consumed_at = now
        existing_attempt.save(update_fields=["consumed_at", "updated_at"])
        record(
            actor=student,
            action="CHECKIN_ATTEMPT_REPLACED",
            target_type="CheckInAttempt",
            target_id=str(existing_attempt.id),
            metadata={"replacement_session_id": str(session.id)},
        )

    # Generate WebAuthn challenge
    webauthn_adapter = WebAuthnAdapterImpl(
        rp_id=settings.WEBAUTHN_RP_ID,
        rp_name=settings.WEBAUTHN_RP_NAME,
        origin=settings.WEBAUTHN_ORIGIN,
    )
    options = webauthn_adapter.generate_authentication_options(student.email)

    # Create CheckInAttempt
    attempt = CheckInAttempt.objects.create(
        session=session,
        student=student,
        challenge=options.challenge,
        device_hint=device_hint,
        expires_at=clock.now() + timedelta(seconds=60),
    )

    record(
        actor=student,
        action="CHECKIN_BEGIN",
        target_type="CheckInAttempt",
        target_id=str(attempt.id),
    )

    return attempt


@transaction.atomic
def complete_checkin(
    attempt_id: str,
    student: User,
    assertion: dict,
    location: dict | None,
    clock: Clock,
) -> CheckIn:
    """Complete the check-in by verifying the assertion and running the decision pipeline."""
    from apps.accounts.domain.webauthn import PasskeyAuthenticationResponse
    from apps.accounts.services.login import login_with_passkey

    # Lock the attempt
    attempt = CheckInAttempt.objects.filter(id=attempt_id).select_for_update().first()
    if not attempt:
        raise NotFoundError("ATTEMPT_NOT_FOUND", "Check-in attempt not found")

    if attempt.student != student:
        raise NotFoundError("ATTEMPT_NOT_FOUND", "Check-in attempt not found")

    if attempt.consumed_at is not None:
        # Idempotent: return existing CheckIn
        existing_checkin = get_checkin_for_student(attempt.session_id, student.id)
        if existing_checkin:
            return existing_checkin
        raise ConflictError("ATTEMPT_ALREADY_CONSUMED", "Attempt already consumed")

    if attempt.expires_at < clock.now():
        raise BadRequestError("ATTEMPT_EXPIRED", "Check-in attempt has expired")

    if not location or any(
        location.get(key) is None for key in ("lat", "lng", "accuracy_m", "timestamp")
    ):
        raise BadRequestError("LOCATION_REQUIRED", "Share your current location to check in")
    if location["accuracy_m"] <= 0:
        raise BadRequestError("LOCATION_INVALID", "The location reading is not accurate enough")

    distance_m = haversine_distance(
        location["lat"],
        location["lng"],
        float(attempt.session.room.latitude),
        float(attempt.session.room.longitude),
    )
    if distance_m > attempt.session.room.radius_m:
        raise BadRequestError(
            "OUTSIDE_CLASSROOM",
            "You are outside the classroom check-in area. Go to class and scan again.",
        )

    # Verify passkey assertion
    try:
        from django.conf import settings

        webauthn_adapter = WebAuthnAdapterImpl(
            rp_id=settings.WEBAUTHN_RP_ID,
            rp_name=settings.WEBAUTHN_RP_NAME,
            origin=settings.WEBAUTHN_ORIGIN,
        )

        auth_response = PasskeyAuthenticationResponse(
            credential_id=assertion.get("credentialId", ""),
            client_data_json=assertion.get("response", {}).get("clientDataJSON", ""),
            authenticator_data=assertion.get("response", {}).get("authenticatorData", ""),
            signature=assertion.get("response", {}).get("signature", ""),
            user_handle=assertion.get("response", {}).get("userHandle", ""),
        )

        login_with_passkey(
            email=student.email,
            response=auth_response,
            expected_challenge=attempt.challenge,
            clock=clock,
            webauthn_adapter=webauthn_adapter,
            origin=settings.WEBAUTHN_ORIGIN,
        )
    except Exception as err:
        record(
            actor=student,
            action="CHECKIN_PASSKEY_VERIFICATION_FAILED",
            target_type="CheckInAttempt",
            target_id=str(attempt.id),
            metadata={"error": str(err)},
        )
        raise BadRequestError("PASSKEY_VERIFICATION_FAILED", "Passkey verification failed") from err

    # Consume the attempt
    attempt.consumed_at = clock.now()
    attempt.save()

    # Calculate distance if location provided
    latitude = location["lat"]
    longitude = location["lng"]
    accuracy_m = location["accuracy_m"]
    location_timestamp = location["timestamp"]

    # Get credential age
    credential_age_hours = None
    if assertion.get("credentialId"):
        credential = PasskeyCredential.objects.filter(credential_id=assertion["credentialId"]).first()
        if credential and credential.created_at:
            credential_age_hours = (clock.now() - credential.created_at).total_seconds() / 3600

    # Run decision pipeline
    from apps.attendance.domain.decision import CheckInSignal

    signal = CheckInSignal(
        qr_fresh=True,  # Already verified in begin_checkin
        passkey_verified=True,  # Just verified
        location_available=True,
        latitude=latitude,
        longitude=longitude,
        accuracy_m=accuracy_m,
        distance_m=distance_m,
        location_timestamp=location_timestamp,
        credential_age_hours=credential_age_hours,
        device_hint=attempt.device_hint,
        network_ip=None,  # Will be set from request in API layer
    )

    decision = make_decision(
        signal,
        room_radius_m=attempt.session.room.radius_m,
    )

    # Create CheckIn
    checkin = CheckIn.objects.create(
        session=attempt.session,
        student=student,
        status=decision.status,
        latitude=latitude,
        longitude=longitude,
        accuracy_m=accuracy_m,
        distance_m=distance_m,
        device_hint=attempt.device_hint,
        network_ip=None,  # Will be set from request in API layer
        flag_reasons=[code.value for code in decision.flag_reasons],
        checked_in_at=clock.now(),
    )

    record(
        actor=student,
        action="CHECKIN_COMPLETE",
        target_type="CheckIn",
        target_id=str(checkin.id),
        metadata={"status": decision.status, "flags": decision.flag_reasons},
    )

    # Run session-level detectors
    _run_session_level_detectors(checkin, clock)

    return checkin


def _run_session_level_detectors(checkin: CheckIn, clock: Clock) -> None:
    """Run session-level detectors that may flag other check-ins."""
    # SHARED_DEVICE detector
    if checkin.device_hint:
        _detect_shared_device(checkin, clock)

    # DUPLICATE_COORDINATES detector
    if checkin.latitude is not None and checkin.longitude is not None:
        _detect_duplicate_coordinates(checkin, clock)

    # NETWORK_BURST detector (disabled by default)
    # _detect_network_burst(checkin, clock)


def _detect_shared_device(checkin: CheckIn, clock: Clock) -> None:
    """Detect if same device_hint used by 2+ students in one session."""
    from apps.attendance.models import CheckIn

    same_device_checkins = CheckIn.objects.filter(
        session=checkin.session,
        device_hint=checkin.device_hint,
        status="PRESENT",
    ).exclude(id=checkin.id)

    if same_device_checkins.count() >= 1:
        # Flag all check-ins with this device
        for other_checkin in same_device_checkins:
            other_checkin.status = "FLAGGED"
            other_checkin.flag_reasons.append(FlagCode.SHARED_DEVICE.value)
            other_checkin.save()

            record(
                actor=None,
                action="SHARED_DEVICE_DETECTED",
                target_type="CheckIn",
                target_id=str(other_checkin.id),
                metadata={"device_hint": checkin.device_hint},
            )

        # Also flag the current check-in
        checkin.status = "FLAGGED"
        checkin.flag_reasons.append(FlagCode.SHARED_DEVICE.value)
        checkin.save()

        record(
            actor=None,
            action="SHARED_DEVICE_DETECTED",
            target_type="CheckIn",
            target_id=str(checkin.id),
            metadata={"device_hint": checkin.device_hint},
        )


def _detect_duplicate_coordinates(checkin: CheckIn, clock: Clock) -> None:
    """Detect if identical coordinates (6 decimals) used by 3+ students in one session."""
    from apps.attendance.models import CheckIn

    # Round to 6 decimal places (~0.1 meter precision)
    lat_rounded = round(checkin.latitude, 6) if checkin.latitude else None
    lng_rounded = round(checkin.longitude, 6) if checkin.longitude else None

    if lat_rounded is None or lng_rounded is None:
        return

    duplicate_checkins = CheckIn.objects.filter(
        session=checkin.session,
        status="PRESENT",
    ).exclude(id=checkin.id)

    # Filter by matching coordinates
    matching_checkins = []
    for other in duplicate_checkins:
        if (
            other.latitude is not None
            and other.longitude is not None
            and round(other.latitude, 6) == lat_rounded
            and round(other.longitude, 6) == lng_rounded
        ):
            matching_checkins.append(other)

    if len(matching_checkins) >= 2:
        # Flag all matching check-ins
        for other_checkin in matching_checkins:
            other_checkin.status = "FLAGGED"
            other_checkin.flag_reasons.append(FlagCode.DUPLICATE_COORDINATES.value)
            other_checkin.save()

            record(
                actor=None,
                action="DUPLICATE_COORDINATES_DETECTED",
                target_type="CheckIn",
                target_id=str(other_checkin.id),
                metadata={"lat": lat_rounded, "lng": lng_rounded},
            )

        # Also flag the current check-in
        checkin.status = "FLAGGED"
        checkin.flag_reasons.append(FlagCode.DUPLICATE_COORDINATES.value)
        checkin.save()

        record(
            actor=None,
            action="DUPLICATE_COORDINATES_DETECTED",
            target_type="CheckIn",
            target_id=str(checkin.id),
            metadata={"lat": lat_rounded, "lng": lng_rounded},
        )
