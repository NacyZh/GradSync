#!/bin/sh
set -eu

: "${GRADSYNC_DEPLOY_PATH:?GRADSYNC_DEPLOY_PATH is required}"

BRANCH="${GRADSYNC_DEPLOY_BRANCH:-master}"
REVISION="${GRADSYNC_DEPLOY_REVISION:-}"
COMPOSE_FILE="${GRADSYNC_COMPOSE_FILE:-docker-compose.prod.yml}"
COMPOSE_ENV_FILE="${GRADSYNC_COMPOSE_ENV_FILE:-.env.production}"
PUBLIC_URL="${GRADSYNC_PUBLIC_URL:-https://120021123.xyz}"
USE_PREBUILT_IMAGES="${GRADSYNC_USE_PREBUILT_IMAGES:-false}"
IMAGE_SOURCE="${GRADSYNC_IMAGE_SOURCE:-}"
PRUNE_BUILDER_CACHE="${GRADSYNC_PRUNE_BUILDER_CACHE:-true}"
BUILDER_CACHE_MAX_AGE="${GRADSYNC_BUILDER_CACHE_MAX_AGE:-720h}"
PRUNE_DANGLING_IMAGES="${GRADSYNC_PRUNE_DANGLING_IMAGES:-true}"
STRICT_UPLOAD_PROXY_CHECK="${GRADSYNC_STRICT_UPLOAD_PROXY_CHECK:-false}"
GIT_FETCH_TIMEOUT_SECONDS="${GRADSYNC_GIT_FETCH_TIMEOUT_SECONDS:-120}"
IMAGE_PULL_TIMEOUT_SECONDS="${GRADSYNC_IMAGE_PULL_TIMEOUT_SECONDS:-900}"
IMAGE_BUILD_TIMEOUT_SECONDS="${GRADSYNC_IMAGE_BUILD_TIMEOUT_SECONDS:-1200}"
MIGRATION_TIMEOUT_SECONDS="${GRADSYNC_MIGRATION_TIMEOUT_SECONDS:-900}"
PRUNE_TIMEOUT_SECONDS="${GRADSYNC_PRUNE_TIMEOUT_SECONDS:-300}"
PUBLIC_CHECK_TIMEOUT_SECONDS="${GRADSYNC_PUBLIC_CHECK_TIMEOUT_SECONDS:-30}"

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

compose_timed() {
  limit="$1"
  shift
  timeout --foreground "${limit}s" \
    docker compose --env-file "$COMPOSE_ENV_FILE" -f "$COMPOSE_FILE" "$@"
}

echo "Fetching ${BRANCH}"
timeout --foreground "${GIT_FETCH_TIMEOUT_SECONDS}s" git fetch origin "$BRANCH"
if [ -n "$REVISION" ]; then
  if ! git cat-file -e "${REVISION}^{commit}" 2>/dev/null; then
    timeout --foreground "${GIT_FETCH_TIMEOUT_SECONDS}s" git fetch origin "$REVISION"
  fi
  git checkout --detach "$REVISION"
  test "$(git rev-parse HEAD)" = "$REVISION"
  echo "Deploying validated revision ${REVISION}"
else
  git checkout "$BRANCH"
  git merge --ff-only "origin/$BRANCH"
  echo "WARNING: GRADSYNC_DEPLOY_REVISION is unset; deploying the branch head." >&2
fi

DEPLOYED_REVISION="$(git rev-parse HEAD)"
case "$DEPLOYED_REVISION" in
  *[!0-9a-f]*)
    echo "Resolved deployment revision is not a full Git commit SHA: $DEPLOYED_REVISION" >&2
    exit 2
    ;;
esac
if [ "${#DEPLOYED_REVISION}" -ne 40 ]; then
  echo "Resolved deployment revision is not a full Git commit SHA: $DEPLOYED_REVISION" >&2
  exit 2
fi
GRADSYNC_BUILD_REVISION="$DEPLOYED_REVISION"
GRADSYNC_IMAGE_SOURCE="$IMAGE_SOURCE"
export GRADSYNC_BUILD_REVISION GRADSYNC_IMAGE_SOURCE

echo "Enforcing production specification acceptance"
python3 scripts/check-spec-acceptance.py --mode enforce --scope production

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
    echo "Pruning Docker builder cache older than ${BUILDER_CACHE_MAX_AGE} ${label}"
    timeout --foreground "${PRUNE_TIMEOUT_SECONDS}s" \
      docker builder prune -af --filter "until=$BUILDER_CACHE_MAX_AGE" || true
  fi
}

verify_image_revision() {
  image="$1"
  service="$2"
  revision="$(
    docker image inspect -f '{{ index .Config.Labels "org.opencontainers.image.revision" }}' \
      "$image"
  )"
  if [ "$revision" != "$DEPLOYED_REVISION" ]; then
    echo "${service} image revision mismatch." >&2
    echo "Expected: $DEPLOYED_REVISION" >&2
    echo "Image:    $revision" >&2
    exit 1
  fi
}

if [ "$USE_PREBUILT_IMAGES" = "true" ]; then
  : "${BACKEND_IMAGE:?BACKEND_IMAGE is required for prebuilt deployment}"
  : "${FRONTEND_IMAGE:?FRONTEND_IMAGE is required for prebuilt deployment}"
  export BACKEND_IMAGE FRONTEND_IMAGE

  echo "Pulling CI-validated production images"
  compose_timed "$IMAGE_PULL_TIMEOUT_SECONDS" pull backend frontend
  verify_image_revision "$BACKEND_IMAGE" "Backend"
  verify_image_revision "$FRONTEND_IMAGE" "Frontend"
else
  echo "WARNING: prebuilt images are disabled; building on the production host." >&2
  echo "Building backend production image"
  compose_timed "$IMAGE_BUILD_TIMEOUT_SECONDS" build --pull backend

  echo "Building frontend production image"
  compose_timed "$IMAGE_BUILD_TIMEOUT_SECONDS" build --pull frontend
  prune_builder_cache "after image builds"
fi

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
compose_timed "$MIGRATION_TIMEOUT_SECONDS" run --rm -T migrate </dev/null

echo "Starting backend"
compose up -d --no-deps --remove-orphans backend
wait_for_service backend healthy

echo "Running production readiness checks"
compose exec -T backend python manage.py check --deploy </dev/null
compose exec -T backend python manage.py check_production_readiness --skip-repo-files </dev/null

echo "Starting frontend"
compose up -d --no-deps --remove-orphans frontend
wait_for_service frontend healthy
frontend_container_id="$(compose ps -q frontend)"
frontend_image_revision="$(
  docker inspect -f '{{ index .Config.Labels "org.opencontainers.image.revision" }}' \
    "$frontend_container_id"
)"
if [ "$frontend_image_revision" != "$DEPLOYED_REVISION" ]; then
  echo "Frontend container revision mismatch." >&2
  echo "Expected: $DEPLOYED_REVISION" >&2
  echo "Running:  $frontend_image_revision" >&2
  exit 1
fi

echo "Starting worker"
compose up -d --no-deps --remove-orphans worker
wait_for_service worker healthy

echo "Starting scheduler"
compose up -d --no-deps --remove-orphans scheduler
wait_for_service scheduler running

if command -v curl >/dev/null 2>&1; then
  curl -fsS --connect-timeout 10 --max-time "$PUBLIC_CHECK_TIMEOUT_SECONDS" "$PUBLIC_URL/" >/dev/null
  curl -fsS --connect-timeout 10 --max-time "$PUBLIC_CHECK_TIMEOUT_SECONDS" "$PUBLIC_URL/healthz/" >/dev/null
  curl -fsS --connect-timeout 10 --max-time "$PUBLIC_CHECK_TIMEOUT_SECONDS" "$PUBLIC_URL/readyz/" >/dev/null
  curl -fsS --connect-timeout 10 --max-time "$PUBLIC_CHECK_TIMEOUT_SECONDS" "$PUBLIC_URL/api/schema/" >/dev/null
  public_frontend_revision="$(
    curl -fsS --connect-timeout 10 --max-time "$PUBLIC_CHECK_TIMEOUT_SECONDS" \
      "$PUBLIC_URL/version.txt" |
      tr -d '\r\n'
  )"
  if [ "$public_frontend_revision" != "$DEPLOYED_REVISION" ]; then
    echo "Public frontend revision mismatch." >&2
    echo "Expected: $DEPLOYED_REVISION" >&2
    echo "Public:   $public_frontend_revision" >&2
    echo "The public proxy is still serving an older frontend container or cached response." >&2
    exit 1
  fi

  upload_limit="$(
    compose exec -T backend python -c \
      'from django.conf import settings; print(settings.GRADSYNC_UPLOAD_MAX_BYTES)' \
      </dev/null
  )"
  upload_probe_size=$((3 * 1024 * 1024))
  if [ "$upload_limit" -gt "$upload_probe_size" ]; then
    upload_probe_status="$(
      head -c "$upload_probe_size" /dev/zero |
        curl -sS -o /dev/null -w '%{http_code}' \
          --connect-timeout 10 \
          --max-time "$PUBLIC_CHECK_TIMEOUT_SECONDS" \
          -X POST \
          -H 'Content-Type: application/octet-stream' \
          --data-binary @- \
          "$PUBLIC_URL/api/library/papers/"
    )"
    if [ "$upload_probe_status" = "413" ]; then
      echo "WARNING: The public proxy rejected a 3 MiB request before Django." >&2
      echo "Set client_max_body_size 0 in the host TLS proxy and reload it." >&2
      if [ "$STRICT_UPLOAD_PROXY_CHECK" = "true" ]; then
        exit 1
      fi
    fi
  fi
fi

compose ps
echo "Deployment completed"
