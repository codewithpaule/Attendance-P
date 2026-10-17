from urllib.parse import urlencode

from django.conf import settings
from django.urls import reverse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from apps.accounts.selectors.functions import list_passkeys
from apps.attendance.adapters.qr import generate_qr_svg_data_uri
from apps.attendance.api.serializers import (
    BeginCheckInSerializer,
    CheckInSerializer,
    CloseSessionSerializer,
    CompleteCheckInSerializer,
    ExtendSessionSerializer,
    OpenSessionSerializer,
    SessionSerializer,
)
from apps.attendance.services.checkin import begin_checkin, complete_checkin
from apps.attendance.services.session import (
    close_session,
    extend_session,
    finalize_session,
    generate_qr_token,
    open_session,
    reopen_session,
)
from apps.core.clock import DefaultClock
from apps.core.permissions import IsStudent, IsTeacher


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsTeacher])
def open_session_view(request: Request, session_id: str) -> Response:
    serializer = OpenSessionSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    session = open_session(
        session_id=session_id,
        teacher=request.user,
        checkin_window_minutes=serializer.validated_data["checkin_window_minutes"],
        clock=DefaultClock(),
    )

    return Response(SessionSerializer(session).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsTeacher])
def close_session_view(request: Request, session_id: str) -> Response:
    serializer = CloseSessionSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    session = close_session(
        session_id=session_id,
        teacher=request.user,
        headcount=serializer.validated_data["headcount"],
        clock=DefaultClock(),
    )

    return Response(SessionSerializer(session).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsTeacher])
def reopen_session_view(request: Request, session_id: str) -> Response:
    session = reopen_session(session_id, request.user, DefaultClock())
    return Response(SessionSerializer(session).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsTeacher])
def extend_session_view(request: Request, session_id: str) -> Response:
    serializer = ExtendSessionSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    session = extend_session(
        session_id=session_id,
        teacher=request.user,
        extra_minutes=serializer.validated_data["extra_minutes"],
        clock=DefaultClock(),
    )
    return Response(SessionSerializer(session).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsTeacher])
def finalize_session_view(request: Request, session_id: str) -> Response:
    session = finalize_session(session_id, request.user, DefaultClock())

    return Response(SessionSerializer(session).data)


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsTeacher])
def qr_token_view(request: Request, session_id: str) -> Response:
    token = generate_qr_token(
        session_id=session_id,
        teacher=request.user,
        max_age_seconds=settings.QR_TOKEN_MAX_AGE_SECONDS,
    )
    checkin_url = request.build_absolute_uri(
        reverse("public_session_checkin", kwargs={"session_id": session_id})
    )
    qr_svg = generate_qr_svg_data_uri(f"{checkin_url}?{urlencode({'t': token})}")

    return Response({"token": token, "qr_svg": qr_svg})


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsStudent])
def begin_checkin_view(request: Request) -> Response:
    serializer = BeginCheckInSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    attempt = begin_checkin(
        session_id=str(serializer.validated_data["session_id"]),
        student=request.user,
        qr_token=serializer.validated_data["qr_token"],
        device_hint=serializer.validated_data.get("device_hint", ""),
        clock=DefaultClock(),
        max_age_seconds=settings.QR_TOKEN_MAX_AGE_SECONDS,
    )

    credentials = list_passkeys(request.user)

    return Response(
        {
            "attempt_id": str(attempt.id),
            "challenge": attempt.challenge,
            "expires_at": attempt.expires_at.isoformat(),
            "rp_id": settings.WEBAUTHN_RP_ID,
            "timeout": 60000,
            "allow_credentials": [credential.credential_id for credential in credentials],
        }
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsStudent])
def complete_checkin_view(request: Request) -> Response:
    serializer = CompleteCheckInSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    location = serializer.validated_data.get("location")

    checkin = complete_checkin(
        attempt_id=str(serializer.validated_data["attempt_id"]),
        student=request.user,
        assertion=serializer.validated_data["assertion"],
        location=location,
        clock=DefaultClock(),
    )

    return Response(CheckInSerializer(checkin).data)

