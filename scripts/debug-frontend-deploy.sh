#!/usr/bin/env bash
# Diagnostic script: verify that the frontend container is serving the latest build.
# Run this on the server where docker compose is executed.
set -euo pipefail

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
CONTAINER="${FRONTEND_CONTAINER:-$(docker compose -f "$COMPOSE_FILE" ps -q frontend 2>/dev/null)}"

if [ -z "$CONTAINER" ]; then
  echo "ERROR: frontend container is not running. Start it first:"
  echo "  docker compose -f $COMPOSE_FILE up -d frontend"
  exit 1
fi

echo "=== 1. Check container image digest ==="
docker inspect "$CONTAINER" --format='Image: {{.Config.Image}}' 2>/dev/null || true
docker inspect "$CONTAINER" --format='Created: {{.Created}}' 2>/dev/null || true

echo ""
echo "=== 2. Does the built JS inside the container contain LoginPage ==="
docker exec "$CONTAINER" sh -c 'grep -l "LoginPage\|login\|Sign in to your research" /usr/share/nginx/html/assets/*.js 2>/dev/null || echo "NOT FOUND — container has the OLD build without login code"'

echo ""
echo "=== 3. Check the index.html served by nginx inside the container ==="
docker exec "$CONTAINER" cat /usr/share/nginx/html/index.html 2>/dev/null || echo "Failed to read index.html"

echo ""
echo "=== 4. Verify API routing through nginx ==="
docker exec "$CONTAINER" sh -c 'grep -n "location /api/\|location /login" /etc/nginx/nginx.conf 2>/dev/null || echo "(no /login location — that is expected, SPA handles routing)"'

echo ""
echo "=== 5. Fetch the actual HTTP response (from host, check cache headers) ==="
HTTP_CODE=$(curl -s -o /dev/null -w '%{http_code}' -H 'Accept: text/html' http://127.0.0.1:8080/ 2>/dev/null || echo "FAIL")
echo "GET / => HTTP $HTTP_CODE"

JS_URL=$(curl -s http://127.0.0.1:8080/ 2>/dev/null | grep -oP 'src="[^"]*\.js"' | head -1 || echo "NONE")
echo "JS asset referenced in index.html: $JS_URL"

echo ""
echo "=== 6. Compare container JS hash with local dist JS hash ==="
CONTAINER_HASH=$(docker exec "$CONTAINER" sh -c 'ls /usr/share/nginx/html/assets/index-*.js 2>/dev/null | head -1' || echo "NONE")
echo "Container JS: $CONTAINER_HASH"
if [ -d frontend/dist/assets ]; then
  LOCAL_HASH=$(ls frontend/dist/assets/index-*.js 2>/dev/null | head -1 || echo "NONE")
  echo "Local JS:     $LOCAL_HASH"
  if [ "$CONTAINER_HASH" != "NONE" ] && [ "$LOCAL_HASH" != "NONE" ]; then
    CONTAINER_FILE=$(basename "$CONTAINER_HASH")
    LOCAL_FILE=$(basename "$LOCAL_HASH")
    if [ "$CONTAINER_FILE" = "$LOCAL_FILE" ]; then
      echo "✓ Container and local dist match."
    else
      echo "✗ MISMATCH — container has an older build. Rebuild the image:"
      echo "  docker compose -f $COMPOSE_FILE build --no-cache frontend"
      echo "  docker compose -f $COMPOSE_FILE up -d frontend"
    fi
  fi
fi

echo ""
echo "=== 7. Force-recreate the frontend container ==="
echo "If the image hash above is old, run:"
echo "  docker compose -f $COMPOSE_FILE build --no-cache frontend"
echo "  docker compose -f $COMPOSE_FILE up -d --force-recreate frontend"
echo ""
echo "Then open the browser in an incognito/private window to test."
echo "If using a reverse proxy / CDN in front, purge its cache too."
