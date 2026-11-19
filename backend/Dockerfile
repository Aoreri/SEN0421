# syntax=docker/dockerfile:1
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app

COPY requirements.txt ./
# Optional CA bundle for builds behind a TLS-inspecting development proxy.
RUN --mount=type=secret,id=proxy_ca \
    if [ -f /run/secrets/proxy_ca ]; then export PIP_CERT=/run/secrets/proxy_ca; fi; \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        libpangoft2-1.0-0 \
        libcairo2 \
        libgdk-pixbuf-2.0-0 \
        libffi8 \
        shared-mime-info \
        fonts-dejavu-core && \
    rm -rf /var/lib/apt/lists/* && \
    python -m pip install --no-cache-dir -r requirements.txt && \
    useradd --create-home --uid 10001 app

COPY --chown=app:app . .
USER app

EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]
