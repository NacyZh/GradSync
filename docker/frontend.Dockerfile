FROM node:22-slim AS build

WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

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
