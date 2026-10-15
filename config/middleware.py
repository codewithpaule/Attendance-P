import uuid

from django.utils.deprecation import MiddlewareMixin


class RequestIDMiddleware(MiddlewareMixin):
    def process_request(self, request):
        request.id = str(uuid.uuid4())
