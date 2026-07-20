DELETE_REQUEST_BODY_EXTENSION = "x-gradsync-delete-request-body"


def delete_json_request_body(schema: dict) -> dict:
    return {
        DELETE_REQUEST_BODY_EXTENSION: {
            "required": True,
            "content": {"application/json": {"schema": schema}},
        }
    }


def include_delete_request_bodies(result, generator, request, public):
    del generator, request, public
    for path_item in result.get("paths", {}).values():
        for operation in path_item.values():
            if not isinstance(operation, dict):
                continue
            request_body = operation.pop(DELETE_REQUEST_BODY_EXTENSION, None)
            if request_body is not None:
                operation["requestBody"] = request_body
    return result
