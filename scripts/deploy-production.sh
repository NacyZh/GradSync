#!/bin/sh
set -eu

: "${GRADSYNC_DEPLOY_PATH:?GRADSYNC_DEPLOY_PATH is required}"

BRANCH="${GRADSYNC_DEPLOY_BRANCH:-master}"
COMPOSE_FILE="${GRADSYNC_COMPOSE_FILE:-docker-compose.prod.yml}"
PUBLIC_URL="${GRADSYNC_PUBLIC_URL:-https://120021123.xyz}"

cd "$GRADSYNC_DEPLOY_PATH"

if [ ! -d .git ]; then
  echo "Deployment path is not a git repository: $GRADSYNC_DEPLOY_PATH" >&2
  exit 2
fi

if [ ! -f .env.production ]; then
  echo ".env.production is missing on the production host" >&2
  exit 2
fi

echo "Fetching ${BRANCH}"
git fetch origin "$BRANCH"
git checkout "$BRANCH"
git pull --ff-only origin "$BRANCH"

echo "Building production images"
docker compose -f "$COMPOSE_FILE" build backend frontend

echo "Starting data services"
docker compose -f "$COMPOSE_FILE" up -d db redis

echo "Running database migrations"
docker compose -f "$COMPOSE_FILE" run --rm migrate

echo "Starting application services"
docker compose -f "$COMPOSE_FILE" up -d --remove-orphans backend frontend worker scheduler

wait_for_service() {
  service="$1"
  expected="${2:-healthy}"
  container_id="$(docker compose -f "$COMPOSE_FILE" ps -q "$service")"
  if [ -z "$container_id" ]; then
    echo "Service has no container: $service" >&2
    exit 1
  fi

  for _ in $(seq 1 40); do
    status="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$container_id")"
    if [ "$status" = "$expected" ]; then
      echo "$service is $status"
      return 0
    fi
    sleep 3
  done

  echo "$service did not reach ${expected}" >&2
  docker compose -f "$COMPOSE_FILE" logs "$service" --tail=120 >&2
  exit 1
}

wait_for_service db healthy
wait_for_service redis healthy
wait_for_service backend healthy
wait_for_service frontend healthy
wait_for_service worker healthy
wait_for_service scheduler running

echo "Running production readiness checks"
docker compose -f "$COMPOSE_FILE" run --rm backend python manage.py check --deploy

if command -v curl >/dev/null 2>&1; then
  curl -fsS "$PUBLIC_URL/" >/dev/null
  curl -fsS "$PUBLIC_URL/healthz/" >/dev/null
  curl -fsS "$PUBLIC_URL/readyz/" >/dev/null
  curl -fsS "$PUBLIC_URL/api/schema/" >/dev/null
fi

docker compose -f "$COMPOSE_FILE" ps
echo "Deployment completed"
