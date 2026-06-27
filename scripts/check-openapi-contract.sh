#!/usr/bin/env bash
set -euo pipefail

CONTRACT="specs/001-research-group-ops/contracts/openapi.yaml"
GENERATED="$(mktemp)"
DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-gradsync.settings.test}"
PYTHON="${PYTHON:-}"
export DJANGO_SETTINGS_MODULE

test -f "$CONTRACT"
if [ -z "$PYTHON" ]; then
  if [ -x ".venv/bin/python" ]; then
    PYTHON=".venv/bin/python"
  else
    PYTHON="python3"
  fi
fi
(
  cd backend
  "../$PYTHON" manage.py spectacular --format openapi-json --file "$GENERATED" >/dev/null
)

"$PYTHON" - "$CONTRACT" "$GENERATED" <<'PY'
import json
import sys

import yaml

contract_path, generated_path = sys.argv[1:3]
with open(contract_path) as handle:
    contract = yaml.safe_load(handle)
with open(generated_path) as handle:
    generated = json.load(handle)


def normalize(path: str) -> str:
    path = path.removeprefix("/api")
    if path != "/" and path.endswith("/"):
        path = path[:-1]
    path = path.replace("{project_id}", "{projectId}").replace("{pk}", "{id}")
    parts = path.split("/")
    normalized = []
    previous = ""
    for part in parts:
        if part == "{id}":
            if previous == "projects":
                normalized.append("{projectId}")
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
            else:
                normalized.append(part)
        else:
            normalized.append(part)
        if part:
            previous = part
    return "/".join(normalized)


def operations(doc):
    result = set()
    for path, methods in doc.get("paths", {}).items():
        for method in methods:
            if method.lower() in {"get", "post", "put", "patch", "delete"}:
                result.add((normalize(path), method.lower()))
    return result


contract_ops = operations(contract)
generated_ops = operations(generated)
missing = sorted(contract_ops - generated_ops)
if missing:
    for path, method in missing:
        print(f"Missing generated operation for contract: {method.upper()} {path}")
    raise SystemExit(1)
print(f"OpenAPI contract drift check passed ({len(contract_ops)} contract operations covered).")
PY
