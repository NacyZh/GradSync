from rest_framework.response import Response


def ok(data=None, status=200):
    return Response(data if data is not None else {}, status=status)
