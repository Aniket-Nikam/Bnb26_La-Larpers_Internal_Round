FROM ghcr.io/astral-sh/uv:0.8.22 AS uv
FROM python:3.12-slim-bookworm AS runtime
COPY --from=uv /uv /usr/local/bin/uv
WORKDIR /app
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1
COPY backend/app ./app
COPY backend/alembic ./alembic
COPY backend/alembic.ini ./
RUN useradd --create-home --uid 10001 fairdrop && mkdir -p /var/lib/fairdrop/lab /run/secrets/fairdrop-lab && chown -R fairdrop:fairdrop /app /var/lib/fairdrop /run/secrets/fairdrop-lab
USER fairdrop
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM grafana/k6:1.3.0 AS k6
FROM runtime AS lab-runner
COPY --from=k6 /usr/bin/k6 /usr/local/bin/k6
COPY tests/performance/scenarios /app/scenarios
CMD ["python", "-m", "app.lab.worker"]
