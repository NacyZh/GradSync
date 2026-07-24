#!/bin/sh
set -eu

DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-gradsync.settings.production}"
export DJANGO_SETTINGS_MODULE
python3 scripts/check-spec-acceptance.py --mode enforce --scope production
cd backend
python manage.py ensure_notification_schedule
python manage.py reclassify_workspace_boundaries --dry-run
python manage.py check --deploy
python manage.py check_production_readiness --repo-root ..
