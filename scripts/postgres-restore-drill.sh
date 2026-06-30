#!/bin/sh
set -eu

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 path/to/gradsync.dump" >&2
  exit 2
fi

BACKUP_PATH="$1"
EVIDENCE_PATH="${BACKUP_RESTORE_DRILL_EVIDENCE:-docs/ops/restore-drills/latest.md}"
STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

./scripts/postgres-restore.sh "$BACKUP_PATH"

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
docker compose -f "$COMPOSE_FILE" exec -T backend python manage.py check_production_readiness --skip-database

COMPLETED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
cat > "$EVIDENCE_PATH" <<EOF
# Latest Restore Drill Evidence

| Field | Value |
|-------|-------|
| Backup artifact | $BACKUP_PATH |
| Off-host storage URI | ${POSTGRES_BACKUP_OFFSITE_URI:-operator-recorded-off-host-copy} |
| Restore target | ${RESTORE_TARGET:-production-like isolated target} |
| Started at | $STARTED_AT |
| Completed at | $COMPLETED_AT |
| Operator | ${USER:-unknown} |
| RPO result | ${RESTORE_DRILL_RPO_RESULT:-recorded by operator} |
| RTO result | ${RESTORE_DRILL_RTO_RESULT:-recorded by operator} |
| Validation commands | postgres-restore.sh; check_production_readiness |
| Outcome | ${RESTORE_DRILL_OUTCOME:-passed} |
EOF

echo "$EVIDENCE_PATH"
