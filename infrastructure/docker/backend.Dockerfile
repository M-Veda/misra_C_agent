FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

FROM base AS development

COPY backend/pyproject.toml backend/README.md /app/backend/
COPY rule-engine/pyproject.toml /app/rule-engine/pyproject.toml
COPY rule-engine/src /app/rule-engine/src
RUN pip install --upgrade pip && pip install -e "/app/rule-engine" && pip install -e "/app/backend[dev]"

COPY backend /app/backend
COPY shared /app/shared
COPY infrastructure/scripts/backend-entrypoint.sh /app/backend-entrypoint.sh

ENV PYTHONPATH=/app/backend/src

WORKDIR /app/backend
RUN chmod +x /app/backend-entrypoint.sh
EXPOSE 8000

CMD ["/app/backend-entrypoint.sh"]

FROM base AS production

COPY backend/pyproject.toml backend/README.md /app/backend/
COPY rule-engine/pyproject.toml /app/rule-engine/pyproject.toml
COPY rule-engine/src /app/rule-engine/src
RUN pip install --upgrade pip && pip install -e "/app/rule-engine" && pip install -e "/app/backend"

COPY backend /app/backend
COPY shared /app/shared

ENV PYTHONPATH=/app/backend/src

WORKDIR /app/backend
EXPOSE 8000

CMD ["uvicorn", "misra_platform.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
