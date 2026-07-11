#!/bin/sh
set -eu

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 path/to/gradsync-media.tar.gz" >&2
  exit 2
fi

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
COMPOSE_ENV_FILE="${COMPOSE_ENV_FILE:-.env.production}"
BACKUP_PATH="$1"

if [ ! -f "$BACKUP_PATH" ]; then
  echo "Media backup does not exist: $BACKUP_PATH" >&2
  exit 2
fi

docker compose --env-file "$COMPOSE_ENV_FILE" -f "$COMPOSE_FILE" exec -T backend \
  tar -xzf - -C /app/backend/media < "$BACKUP_PATH"
echo "Restored media from $BACKUP_PATH"
