#!/bin/sh
set -eu

if [ ! -d .git ]; then
  echo "check-generated-artifacts.sh must run from the repository root" >&2
  exit 2
fi

find_generated_artifacts() {
  action="${1:-print}"

  if [ "$action" = "delete" ]; then
    result_action="-exec rm -rf {} +"
  else
    result_action="-print"
  fi

  if [ -d .vite ]; then
    if [ "$action" = "delete" ]; then
      rm -rf .vite
    else
      echo .vite
    fi
  fi

  # shellcheck disable=SC2086
  find backend frontend \
    -path 'frontend/node_modules' -prune -o \
    \( \
      -path '*/__pycache__' -o \
      -name '*.pyc' -o \
      -name '*.tsbuildinfo' -o \
      -path 'backend/e2e.sqlite3' -o \
      -path 'frontend/dist' -o \
      -path 'frontend/playwright-report' -o \
      -path 'frontend/test-results' -o \
      -path 'frontend/coverage' -o \
      -name 'build-guards.js' -o \
      -name 'build-guards.d.ts' -o \
      -name 'vite.config.js' -o \
      -name 'vite.config.d.ts' -o \
      -name '*.spec.js-snapshots' -o \
      -name '*.snap' \
    \) $result_action
}

check_paper_library_spec_review_artifacts() {
  spec_dir="specs/004-paper-library-workflow"
  [ -d "$spec_dir" ] || return 0

  missing=""
  for path in \
    "$spec_dir/spec.md" \
    "$spec_dir/plan.md" \
    "$spec_dir/research.md" \
    "$spec_dir/data-model.md" \
    "$spec_dir/quickstart.md" \
    "$spec_dir/security-review.md" \
    "$spec_dir/tasks.md" \
    "$spec_dir/contracts/openapi.yaml" \
    "$spec_dir/contracts/frontend-ui.md"
  do
    if [ ! -f "$path" ]; then
      missing="${missing}${path}
"
    fi
  done

  if [ -n "$missing" ]; then
    echo "Paper library spec review artifacts are incomplete:" >&2
    printf '%s' "$missing" >&2
    echo "specs/ is ignored by default; force-add complete review artifacts intentionally." >&2
    exit 1
  fi
}

if [ "${1:-}" = "--clean" ]; then
  find_generated_artifacts delete
elif [ "${1:-}" != "" ]; then
  echo "Usage: sh scripts/check-generated-artifacts.sh [--clean]" >&2
  exit 2
fi

found="$(find_generated_artifacts)"

if [ -n "$found" ]; then
  echo "Generated runtime/build artifacts must not remain in source scope:" >&2
  echo "$found" >&2
  exit 1
fi

check_paper_library_spec_review_artifacts
