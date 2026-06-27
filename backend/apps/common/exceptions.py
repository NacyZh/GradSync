from rest_framework.views import exception_handler


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is not None and isinstance(response.data, dict):
        detail = response.data.get("detail")
        if detail is not None:
            response.data = {"message": str(detail)}
    return response
