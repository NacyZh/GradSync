FROM node:22-slim AS build

WORKDIR /app/frontend

ARG NPM_CONFIG_REGISTRY=https://registry.npmjs.org
ARG NPM_CONFIG_FETCH_RETRIES=2
ARG NPM_CONFIG_FETCH_RETRY_MINTIMEOUT=5000
ARG NPM_CONFIG_FETCH_RETRY_MAXTIMEOUT=30000
ARG NPM_CONFIG_FETCH_TIMEOUT=120000
ARG NPM_CONFIG_MAXSOCKETS=8
ARG NPM_CI_TIMEOUT_SECONDS=600

COPY frontend/package.json frontend/package-lock.json ./
RUN --mount=type=cache,id=gradsync-frontend-npm,target=/root/.npm \
    echo "Using npm registry: $(npm config get registry)" && \
    timeout "${NPM_CI_TIMEOUT_SECONDS}s" \
    npm ci --prefer-offline --no-audit --no-fund --loglevel=http

COPY frontend/ ./
ARG VITE_API_BASE_URL=""
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN npm run build

FROM nginx:1.27-alpine AS runtime

COPY docker/nginx.conf /etc/nginx/nginx.conf.template
COPY --from=build /app/frontend/dist /usr/share/nginx/html

USER nginx
EXPOSE 8080

CMD ["/bin/sh", "-c", "upload_max=${GRADSYNC_UPLOAD_MAX_BYTES:-104857600}; export GRADSYNC_HTTP_UPLOAD_MAX_BYTES=$((upload_max + 1048576)); envsubst '${GRADSYNC_HTTP_UPLOAD_MAX_BYTES}' < /etc/nginx/nginx.conf.template > /tmp/nginx.conf; exec nginx -c /tmp/nginx.conf -g 'daemon off;'"]
