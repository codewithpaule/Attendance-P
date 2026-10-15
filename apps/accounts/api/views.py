from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from apps.accounts.adapters.webauthn import WebAuthnAdapterImpl
from apps.accounts.api.serializers import (
    ActivationRequestSerializer,
    IssueRecoveryCodeSerializer,
    LoginRequestSerializer,
    PasskeySerializer,
    RegisterPasskeyRequestSerializer,
    UseRecoveryCodeSerializer,
    UserSerializer,
)
from apps.accounts.domain.webauthn import (
    PasskeyAuthenticationResponse,
    PasskeyRegistrationResponse,
)
from apps.accounts.models import User
from apps.accounts.selectors.functions import list_passkeys as list_passkeys_selector
from apps.accounts.services.activate import activate_user
from apps.accounts.services.import_users import import_users_from_csv
from apps.accounts.services.login import login_with_passkey
from apps.accounts.services.passkeys import (
    register_passkey as register_passkey_service,
)
from apps.accounts.services.passkeys import (
    revoke_passkey as revoke_passkey_service,
)
from apps.accounts.services.recovery import (
    issue_recovery_code as issue_recovery_code_service,
)
from apps.accounts.services.recovery import (
    use_recovery_code as use_recovery_code_service,
)
from apps.core.clock import DefaultClock


@api_view(["POST"])
@permission_classes([AllowAny])
def login(request: Request) -> Response:
    serializer = LoginRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    data = serializer.validated_data
    response = PasskeyAuthenticationResponse(
        credential_id=data["credential_id"],
        client_data_json=data["client_data_json"],
        authenticator_data=data["authenticator_data"],
        signature=data["signature"],
        user_handle=data.get("user_handle"),
    )

    clock = DefaultClock()
    webauthn = WebAuthnAdapterImpl(
        rp_id=settings.WEBAUTHN_RP_ID,
        rp_name=settings.WEBAUTHN_RP_NAME,
        origin=settings.WEBAUTHN_ORIGIN,
    )

    user = login_with_passkey(
        request=request,
        credential_id=data["credential_id"],
        response=response,
        expected_challenge=data["challenge"],
        clock=clock,
        webauthn_adapter=webauthn,
        origin=webauthn.origin,
    )

    return Response(UserSerializer(user).data)


@api_view(["POST"])
@permission_classes([AllowAny])
def activate(request: Request) -> Response:
    serializer = ActivationRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    data = serializer.validated_data
    PasskeyRegistrationResponse(
        credential_id=data["credential_id"],
        client_data_json=data["client_data_json"],
        attestation_object=data["attestation_object"],
        label=data["label"],
    )

    clock = DefaultClock()
    webauthn = WebAuthnAdapterImpl(
        rp_id=settings.WEBAUTHN_RP_ID,
        rp_name=settings.WEBAUTHN_RP_NAME,
        origin=settings.WEBAUTHN_ORIGIN,
    )

    user = activate_user(
        student_number=data["student_number"],
        code=data["code"],
        password=data["password"],
        webauthn_response={
            "credential_id": data["credential_id"],
            "client_data_json": data["client_data_json"],
            "attestation_object": data["attestation_object"],
            "challenge": data.get("challenge", ""),
        },
        clock=clock,
        webauthn_adapter=webauthn,
        origin=webauthn.origin,
    )

    return Response(UserSerializer(user).data)


@api_view(["POST"])
@permission_classes([AllowAny])
def register_passkey_begin_for_activation(request: Request) -> Response:
    student_number = request.data.get("student_number")
    if not student_number:
        from apps.core.exceptions import BadRequestError

        raise BadRequestError(code="MISSING_STUDENT_NUMBER", message="Student number required")

    from apps.accounts.selectors.functions import get_user_by_student_number

    user = get_user_by_student_number(student_number)
    if not user:
        from apps.core.exceptions import NotFoundError

        raise NotFoundError(code="USER_NOT_FOUND", message="User not found")

    DefaultClock()
    webauthn = WebAuthnAdapterImpl(
        rp_id=settings.WEBAUTHN_RP_ID,
        rp_name=settings.WEBAUTHN_RP_NAME,
        origin=settings.WEBAUTHN_ORIGIN,
    )

    options = webauthn.generate_registration_options(
        user_id=str(user.id),
        user_name=user.email,
        display_name=user.full_name,
        rp_id=webauthn.rp_id,
        rp_name=webauthn.rp_name,
    )

    return Response(
        {
            "challenge": options.challenge,
            "user_id": options.user_id,
            "user_name": options.user_name,
            "display_name": options.display_name,
            "rp_id": options.rp_id,
            "rp_name": options.rp_name,
            "timeout": options.timeout,
        }
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def register_passkey_begin(request: Request) -> Response:
    user = request.user
    DefaultClock()
    webauthn = WebAuthnAdapterImpl(
        rp_id=settings.WEBAUTHN_RP_ID,
        rp_name=settings.WEBAUTHN_RP_NAME,
        origin=settings.WEBAUTHN_ORIGIN,
    )

    options = webauthn.generate_registration_options(
        user_id=str(user.id),
        user_name=user.email,
        display_name=user.full_name,
        rp_id=webauthn.rp_id,
        rp_name=webauthn.rp_name,
    )

    return Response(
        {
            "challenge": options.challenge,
            "user_id": options.user_id,
            "user_name": options.user_name,
            "display_name": options.display_name,
            "rp_id": options.rp_id,
            "rp_name": options.rp_name,
            "timeout": options.timeout,
        }
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def register_passkey_complete(request: Request) -> Response:
    serializer = RegisterPasskeyRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    data = serializer.validated_data
    response = PasskeyRegistrationResponse(
        credential_id=data["credential_id"],
        client_data_json=data["client_data_json"],
        attestation_object=data["attestation_object"],
        label=data["label"],
    )

    clock = DefaultClock()
    webauthn = WebAuthnAdapterImpl(
        rp_id=settings.WEBAUTHN_RP_ID,
        rp_name=settings.WEBAUTHN_RP_NAME,
        origin=settings.WEBAUTHN_ORIGIN,
    )

    credential = register_passkey_service(
        user=request.user,
        response=response,
        expected_challenge=data["challenge"],
        label=data["label"],
        clock=clock,
        webauthn_adapter=webauthn,
        origin=webauthn.origin,
    )

    return Response(PasskeySerializer(credential).data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_passkeys(request: Request) -> Response:
    passkeys = list_passkeys_selector(request.user)
    return Response(PasskeySerializer(passkeys, many=True).data)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def revoke_passkey(request: Request, credential_id: str) -> Response:
    clock = DefaultClock()
    revoke_passkey_service(request.user, credential_id, clock)
    return Response({"status": "ok"})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def issue_recovery_code(request: Request) -> Response:
    serializer = IssueRecoveryCodeSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    data = serializer.validated_data
    clock = DefaultClock()

    code = issue_recovery_code_service(
        student_number=data["student_number"],
        issuer=request.user,
        clock=clock,
    )

    return Response({"code": code})


@api_view(["POST"])
@permission_classes([AllowAny])
def use_recovery_code(request: Request) -> Response:
    serializer = UseRecoveryCodeSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    data = serializer.validated_data
    clock = DefaultClock()

    user = use_recovery_code_service(
        student_number=data["student_number"],
        code=data["code"],
        new_password=data["new_password"],
        clock=clock,
    )

    return Response(UserSerializer(user).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def import_users(request: Request) -> Response:
    if request.user.role != User.Role.ADMIN:
        from apps.core.exceptions import PermissionDeniedError

        raise PermissionDeniedError(
            code="PERMISSION_DENIED",
            message="Only admins can import users",
        )

    csv_data = request.data.get("csv_data", "")
    clock = DefaultClock()

    result = import_users_from_csv(csv_data, request.user, clock)

    return Response(result)
