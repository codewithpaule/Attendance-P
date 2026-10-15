from rest_framework import serializers


class OpenSessionSerializer(serializers.Serializer):
    checkin_window_minutes = serializers.IntegerField(min_value=1, default=15)


class CloseSessionSerializer(serializers.Serializer):
    headcount = serializers.IntegerField(min_value=0)


class QRTokenSerializer(serializers.Serializer):
    session_id = serializers.UUIDField()


class SessionSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    course_id = serializers.UUIDField()
    room_id = serializers.UUIDField()
    status = serializers.CharField()
    opened_at = serializers.DateTimeField(allow_null=True)
    closed_at = serializers.DateTimeField(allow_null=True)
    finalized_at = serializers.DateTimeField(allow_null=True)
    checkin_window_minutes = serializers.IntegerField()
    headcount = serializers.IntegerField(allow_null=True)


class BeginCheckInSerializer(serializers.Serializer):
    session_id = serializers.UUIDField()
    qr_token = serializers.CharField()
    device_hint = serializers.CharField(required=False, allow_blank=True)


class LocationSerializer(serializers.Serializer):
    lat = serializers.FloatField(required=False, allow_null=True)
    lng = serializers.FloatField(required=False, allow_null=True)
    accuracy_m = serializers.FloatField(required=False, allow_null=True)
    timestamp = serializers.FloatField(required=False, allow_null=True)


class CompleteCheckInSerializer(serializers.Serializer):
    attempt_id = serializers.UUIDField()
    assertion = serializers.DictField()
    location = LocationSerializer(required=False, allow_null=True)


class CheckInAttemptSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    session_id = serializers.UUIDField()
    challenge = serializers.CharField()
    expires_at = serializers.DateTimeField()


class CheckInSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    session_id = serializers.UUIDField()
    student_id = serializers.UUIDField()
    status = serializers.CharField()
    latitude = serializers.FloatField(allow_null=True)
    longitude = serializers.FloatField(allow_null=True)
    accuracy_m = serializers.FloatField(allow_null=True)
    distance_m = serializers.FloatField(allow_null=True)
    flag_reasons = serializers.ListField(child=serializers.CharField(), allow_empty=True)
    checked_in_at = serializers.DateTimeField()

