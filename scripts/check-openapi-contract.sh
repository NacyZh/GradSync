#!/usr/bin/env bash
set -euo pipefail

STRICT_SHAPES="${OPENAPI_STRICT_SHAPES:-false}"
if [ "${1:-}" = "--strict-shapes" ]; then
  STRICT_SHAPES="true"
  shift
fi

CONTRACT="${1:-specs/001-research-group-ops/contracts/openapi.yaml}"
GENERATED="$(mktemp)"
DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-gradsync.settings.test}"
PYTHON="${PYTHON:-}"
export DJANGO_SETTINGS_MODULE

if [ ! -f "$CONTRACT" ]; then
  echo "OpenAPI contract file not found: $CONTRACT" >&2
  exit 1
fi
if [ -z "$PYTHON" ]; then
  if [ -x ".venv/bin/python" ]; then
    PYTHON=".venv/bin/python"
  else
    PYTHON="python3"
  fi
fi
if [ "$PYTHON" = "python" ] && ! command -v python >/dev/null 2>&1; then
  if [ -x ".venv/bin/python" ]; then
    PYTHON=".venv/bin/python"
  else
    PYTHON="python3"
  fi
fi
case "$PYTHON" in
  /*) BACKEND_PYTHON="$PYTHON" ;;
  */*) BACKEND_PYTHON="../$PYTHON" ;;
  *) BACKEND_PYTHON="$PYTHON" ;;
esac
(
  cd backend
  "$BACKEND_PYTHON" manage.py spectacular --format openapi-json --file "$GENERATED" >/dev/null
)

"$PYTHON" - "$CONTRACT" "$GENERATED" "$STRICT_SHAPES" <<'PY'
import json
import sys

import yaml

contract_path, generated_path, strict_shapes = sys.argv[1:4]
strict_shapes = strict_shapes.lower() in {"1", "true", "yes", "on"}
with open(contract_path) as handle:
    contract = yaml.safe_load(handle)
with open(generated_path) as handle:
    generated = json.load(handle)


def resolve_ref(doc: dict, value):
    while isinstance(value, dict) and "$ref" in value:
        target = doc
        for part in value["$ref"].removeprefix("#/").split("/"):
            target = target[part]
        value = target
    return value


def normalize(path: str) -> str:
    path = path.removeprefix("/api")
    if path != "/" and path.endswith("/"):
        path = path[:-1]
    path = (
        path.replace("{project_id}", "{projectId}")
        .replace("{artifact_id}", "{artifactId}")
        .replace("{batch_id}", "{batchId}")
        .replace("{document_id}", "{documentId}")
        .replace("{feedback_id}", "{feedbackId}")
        .replace("{paper_id}", "{paperId}")
        .replace("{import_job_id}", "{importJobId}")
        .replace("{submission_id}", "{submissionId}")
        .replace("{writing_project_id}", "{writingProjectId}")
        .replace("{writing_version_id}", "{writingVersionId}")
        .replace("{version_id}", "{versionId}")
        .replace("{membership_id}", "{membershipId}")
        .replace("{material_id}", "{materialId}")
        .replace("{pk}", "{id}")
    )
    parts = path.split("/")
    normalized = []
    previous = ""
    for part in parts:
        if part == "{id}":
            if previous == "projects":
                normalized.append("{projectId}")
            elif previous == "role-activations":
                normalized.append("{activationId}")
            elif previous == "resource-use-submissions":
                normalized.append("{submissionId}")
            elif previous == "resources":
                normalized.append("{resourceId}")
            elif previous == "tasks":
                normalized.append("{taskId}")
            elif previous == "drafts":
                normalized.append("{draftId}")
            elif previous == "bookings":
                normalized.append("{bookingId}")
            elif previous == "comments":
                normalized.append("{commentId}")
            elif previous == "reports":
                normalized.append("{reportId}")
            elif previous == "papers":
                normalized.append("{paperId}")
            elif previous == "imports":
                normalized.append("{batchId}")
            elif previous == "code-artifacts":
                normalized.append("{artifactId}")
            elif previous == "versions":
                normalized.append("{versionId}")
            else:
                normalized.append(part)
        else:
            normalized.append(part)
        if part:
            previous = part
    return "/".join(normalized)


def normalize_parameter_name(name: str) -> str:
    return (
        name.replace("project_id", "projectId")
        .replace("artifact_id", "artifactId")
        .replace("batch_id", "batchId")
        .replace("document_id", "documentId")
        .replace("feedback_id", "feedbackId")
        .replace("paper_id", "paperId")
        .replace("submission_id", "submissionId")
        .replace("writing_project_id", "writingProjectId")
        .replace("writing_version_id", "writingVersionId")
        .replace("version_id", "versionId")
        .replace("membership_id", "membershipId")
        .replace("material_id", "materialId")
        .replace("actor_id", "actorId")
        .replace("target_type", "targetType")
        .replace("category_id", "categoryId")
    )


def operations(doc):
    result = {}
    for path, methods in doc.get("paths", {}).items():
        for method in methods:
            if method.lower() in {"get", "post", "put", "patch", "delete"}:
                result[(normalize(path), method.lower())] = methods[method]
    return result


contract_ops = operations(contract)
generated_ops = operations(generated)
missing = sorted(set(contract_ops) - set(generated_ops))
if missing:
    for path, method in missing:
        print(f"Missing generated operation for contract: {method.upper()} {path}")
    raise SystemExit(1)


def query_parameters(doc: dict, operation: dict) -> set[tuple[str, str]]:
    parameters = [resolve_ref(doc, item) for item in operation.get("parameters", [])]
    return {
        (parameter.get("in", ""), normalize_parameter_name(parameter.get("name", "")))
        for parameter in parameters
        if parameter.get("in") == "query"
    }


def request_content_types(doc: dict, operation: dict) -> set[str]:
    request_body = resolve_ref(doc, operation.get("requestBody") or {})
    return set((request_body.get("content") or {}).keys())


def response_statuses(operation: dict) -> set[str]:
    return {str(status) for status in (operation.get("responses") or {}).keys()}


shape_issues: list[str] = []
for key in sorted(set(contract_ops) & set(generated_ops)):
    contract_operation = contract_ops[key]
    generated_operation = generated_ops[key]
    path, method = key

    missing_query_parameters = query_parameters(contract, contract_operation) - query_parameters(
        generated, generated_operation
    )
    for location, name in sorted(missing_query_parameters):
        shape_issues.append(f"Missing {location} parameter for contract: {method.upper()} {path} {name}")

    contract_request_content = request_content_types(contract, contract_operation)
    generated_request_content = request_content_types(generated, generated_operation)
    if contract_request_content and not (contract_request_content & generated_request_content):
        shape_issues.append(
            "Missing request body content type for contract: "
            f"{method.upper()} {path} expected one of {sorted(contract_request_content)}"
        )

    missing_statuses = response_statuses(contract_operation) - response_statuses(generated_operation)
    for status in sorted(missing_statuses):
        shape_issues.append(
            f"Missing response status for contract: {method.upper()} {path} {status}"
        )

if shape_issues:
    for issue in shape_issues:
        print(issue)
    if strict_shapes:
        raise SystemExit(1)
    print(
        "OpenAPI shape drift warnings are non-blocking. "
        "Set OPENAPI_STRICT_SHAPES=1 or pass --strict-shapes to fail on them."
    )

print(f"OpenAPI contract drift check passed ({len(contract_ops)} contract operations covered).")
PY
