import contextvars
import logging
import re
import uuid

from apps.common.error_reporting import capture_exception

request_id_var = contextvars.ContextVar("request_id", default="-")
_SAFE_REQUEST_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{7,63}$")


class RequestIDMiddleware:
    header_name = "HTTP_X_REQUEST_ID"
    response_header = "X-Request-ID"

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        supplied = str(request.META.get(self.header_name, "")).strip()
        request_id = supplied if _SAFE_REQUEST_ID.fullmatch(supplied) else uuid.uuid4().hex
        token = request_id_var.set(request_id)
        request.request_id = request_id
        try:
            try:
                response = self.get_response(request)
            except Exception as exc:
                capture_exception(exc)
                raise
            response[self.response_header] = request_id
            return response
        finally:
            request_id_var.reset(token)


class RequestIDLogFilter(logging.Filter):
    def filter(self, record):
        record.request_id = request_id_var.get()
        return True
