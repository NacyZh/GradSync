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
