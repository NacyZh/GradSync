#!/bin/sh
set -eu

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
COMPOSE_ENV_FILE="${COMPOSE_ENV_FILE:-.env.production}"
BACKUP_DIR="${BACKUP_DIR:-./backups/media}"
RETENTION_DAYS="${MEDIA_BACKUP_RETENTION_DAYS:-14}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP_PATH="$BACKUP_DIR/gradsync-media-$STAMP.tar.gz"

mkdir -p "$BACKUP_DIR"
docker compose --env-file "$COMPOSE_ENV_FILE" -f "$COMPOSE_FILE" exec -T backend \
  tar -C /app/backend/media -czf - . > "$BACKUP_PATH"
find "$BACKUP_DIR" -type f -name 'gradsync-media-*.tar.gz' -mtime +"$RETENTION_DAYS" -delete
echo "$BACKUP_PATH"
