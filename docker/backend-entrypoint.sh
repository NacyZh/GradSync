#!/bin/sh
set -eu

if [ "${GRADSYNC_COLLECT_STATIC:-false}" = "true" ]; then
  python manage.py collectstatic --noinput
fi

exec "$@"
