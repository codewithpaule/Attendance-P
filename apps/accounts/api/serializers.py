from rest_framework import serializers


class LoginRequestSerializer(serializers.Serializer):
    credential_id = serializers.CharField()
    client_data_json = serializers.CharField()
    authenticator_data = serializers.CharField()
    signature = serializers.CharField()
    user_handle = serializers.CharField(required=False, allow_null=True)
    challenge = serializers.CharField()


class ActivationRequestSerializer(serializers.Serializer):
    student_number = serializers.CharField()
    code = serializers.CharField()
    password = serializers.CharField(min_length=8)
    credential_id = serializers.CharField()
    client_data_json = serializers.CharField()
    attestation_object = serializers.CharField()
    label = serializers.CharField(default="Default")


class RegisterPasskeyRequestSerializer(serializers.Serializer):
    credential_id = serializers.CharField()
    client_data_json = serializers.CharField()
    attestation_object = serializers.CharField()
    label = serializers.CharField(max_length=100)
    challenge = serializers.CharField()


class IssueRecoveryCodeSerializer(serializers.Serializer):
    student_number = serializers.CharField()


class UseRecoveryCodeSerializer(serializers.Serializer):
    student_number = serializers.CharField()
    code = serializers.CharField()
    new_password = serializers.CharField(min_length=8)


class UserSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    email = serializers.EmailField()
    full_name = serializers.CharField()
    role = serializers.CharField()
    student_number = serializers.CharField(allow_null=True)
    is_active = serializers.BooleanField()


class PasskeySerializer(serializers.Serializer):
    id = serializers.UUIDField()
    credential_id = serializers.CharField()
    label = serializers.CharField()
    last_used_at = serializers.DateTimeField(allow_null=True)
    created_at = serializers.DateTimeField()
