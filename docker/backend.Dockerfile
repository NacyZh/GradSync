FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=gradsync.settings.production

WORKDIR /app/backend

COPY backend/ ./
RUN --mount=type=cache,target=/root/.cache/pip \
    addgroup --system gradsync \
    && adduser --system --ingroup gradsync gradsync \
    && pip install --upgrade pip \
    && pip install .

COPY docker/backend-entrypoint.sh /entrypoint.sh

RUN mkdir -p /app/backend/staticfiles /app/backend/media \
    && chown -R gradsync:gradsync /app/backend /entrypoint.sh \
    && chmod +x /entrypoint.sh

USER gradsync

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
CMD ["sh", "-c", "exec gunicorn gradsync.wsgi:application --bind 0.0.0.0:8000 --workers \"${GRADSYNC_GUNICORN_WORKERS:-1}\" --threads \"${GRADSYNC_GUNICORN_THREADS:-2}\" --access-logfile - --error-logfile -"]
