FROM python:3.11-slim as builder

WORKDIR /app

COPY pyproject.toml ./

RUN pip install --no-cache-dir uv

RUN uv pip install --system --no-cache-dir \
    fastapi>=0.115.12 \
    google-genai>=1.18.0 \
    mcp[cli]>=1.9.2 \
    httpx \
    uvicorn[standard] \
    pydantic \
    asyncio

FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    wget \
    ca-certificates \
    procps \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY client/ ./client/
COPY config/ ./config/

RUN mkdir -p /app/logs && chmod 777 /app/logs

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:5001/api/v1/health/health || exit 1

EXPOSE 5001

ENV ENVIRONMENT=production
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

CMD ["python", "-m", "client.scripts.start_backend", "production", "--host", "0.0.0.0", "--port", "5001"] 