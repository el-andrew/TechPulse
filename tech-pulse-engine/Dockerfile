ARG PYTHON_VERSION=3.11
FROM python:${PYTHON_VERSION}-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    APP_HOME=/app

WORKDIR ${APP_HOME}

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./requirements.txt
RUN python -m pip install --upgrade pip \
    && python -m pip install -r requirements.txt

COPY app ./app
COPY docker ./docker
COPY README.md ./README.md
COPY docker-compose.yml ./docker-compose.yml

RUN mkdir -p /app/logs /data \
    && addgroup --system techpulse \
    && adduser --system --ingroup techpulse --home /app techpulse \
    && chown -R techpulse:techpulse /app /data \
    && chmod +x /app/docker/entrypoint.sh

USER techpulse

ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["python", "-m", "app.main", "run-daily"]
