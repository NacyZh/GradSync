#!/bin/sh
set -eu

: "${GRADSYNC_DEPLOY_PATH:?GRADSYNC_DEPLOY_PATH is required}"

BRANCH="${GRADSYNC_DEPLOY_BRANCH:-master}"
COMPOSE_FILE="${GRADSYNC_COMPOSE_FILE:-docker-compose.prod.yml}"
COMPOSE_ENV_FILE="${GRADSYNC_COMPOSE_ENV_FILE:-.env.production}"
PUBLIC_URL="${GRADSYNC_PUBLIC_URL:-https://120021123.xyz}"
PRUNE_BUILDER_CACHE="${GRADSYNC_PRUNE_BUILDER_CACHE:-true}"
PRUNE_DANGLING_IMAGES="${GRADSYNC_PRUNE_DANGLING_IMAGES:-true}"

COMPOSE_PARALLEL_LIMIT="${COMPOSE_PARALLEL_LIMIT:-1}"
DOCKER_BUILDKIT="${DOCKER_BUILDKIT:-1}"
export COMPOSE_PARALLEL_LIMIT DOCKER_BUILDKIT

cd "$GRADSYNC_DEPLOY_PATH"

if [ ! -d .git ]; then
  echo "Deployment path is not a git repository: $GRADSYNC_DEPLOY_PATH" >&2
  exit 2
fi

if [ ! -f "$COMPOSE_ENV_FILE" ]; then
  echo "$COMPOSE_ENV_FILE is missing on the production host" >&2
  exit 2
fi

compose() {
  docker compose --env-file "$COMPOSE_ENV_FILE" -f "$COMPOSE_FILE" "$@"
}

echo "Fetching ${BRANCH}"
git fetch origin "$BRANCH"
git checkout "$BRANCH"
git pull --ff-only origin "$BRANCH"

echo "Stopping application services before image build to reduce memory pressure"
compose stop backend frontend worker scheduler || true
compose rm -f backend frontend worker scheduler || true

wait_for_service() {
  service="$1"
  expected="${2:-healthy}"
  container_id="$(compose ps -q "$service")"
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
  compose logs "$service" --tail=120 >&2
  exit 1
}

prune_builder_cache() {
  label="$1"
  if [ "$PRUNE_BUILDER_CACHE" = "true" ]; then
    echo "Pruning Docker builder cache ${label}"
    docker builder prune -af || true
  fi
}

prune_builder_cache "before image build"

echo "Building backend production image"
compose build --pull backend
prune_builder_cache "after backend image build"

echo "Building frontend production image"
compose build --pull frontend
prune_builder_cache "after frontend image build"

if [ "$PRUNE_DANGLING_IMAGES" = "true" ]; then
  echo "Pruning dangling Docker images after image build"
  docker image prune -f || true
fi

echo "Starting PostgreSQL"
compose up -d db
wait_for_service db healthy

echo "Starting Redis"
compose up -d redis
wait_for_service redis healthy

echo "Running database migrations"
compose run --rm migrate

echo "Starting backend"
compose up -d --no-deps --remove-orphans backend
wait_for_service backend healthy

echo "Running production readiness checks"
compose exec -T backend python manage.py check --deploy
compose exec -T backend python manage.py check_production_readiness --skip-repo-files

echo "Starting frontend"
compose up -d --no-deps --remove-orphans frontend
wait_for_service frontend healthy

echo "Starting worker"
compose up -d --no-deps --remove-orphans worker
wait_for_service worker healthy

echo "Starting scheduler"
compose up -d --no-deps --remove-orphans scheduler
wait_for_service scheduler running

if command -v curl >/dev/null 2>&1; then
  curl -fsS "$PUBLIC_URL/" >/dev/null
  curl -fsS "$PUBLIC_URL/healthz/" >/dev/null
  curl -fsS "$PUBLIC_URL/readyz/" >/dev/null
  curl -fsS "$PUBLIC_URL/api/schema/" >/dev/null
fi

compose ps
echo "Deployment completed"
