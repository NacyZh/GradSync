#!/bin/sh
set -eu

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
BACKUP_DIR="${BACKUP_DIR:-./backups/postgres}"
RETENTION_DAYS="${POSTGRES_BACKUP_RETENTION_DAYS:-14}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$BACKUP_DIR"

docker compose -f "$COMPOSE_FILE" exec -T db pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc > "$BACKUP_DIR/gradsync-$STAMP.dump"
find "$BACKUP_DIR" -type f -name 'gradsync-*.dump' -mtime +"$RETENTION_DAYS" -delete
echo "$BACKUP_DIR/gradsync-$STAMP.dump"
