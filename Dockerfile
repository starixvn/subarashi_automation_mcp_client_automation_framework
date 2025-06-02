FROM python:3.11-slim as builder

WORKDIR /app

COPY pyproject.toml ./
COPY uv.lock ./ 2>/dev/null || echo "No uv.lock file found"

RUN pip install --no-cache-dir uv

RUN uv pip install --system --no-cache-dir \
    fastapi>=0.115.12 \
    google-genai>=1.18.0 \
    mcp[cli]>=1.9.2 \
    streamlit>=1.45.1 \
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

RUN mkdir -p /app/logs && chmod 755 /app/logs

RUN groupadd -r mcpuser && useradd -r -g mcpuser -d /app -s /bin/bash mcpuser
RUN chown -R mcpuser:mcpuser /app
USER mcpuser

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:5001/api/v1/health/health || exit 1

EXPOSE 5001 5002

ENV ENVIRONMENT=production
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

USER root
RUN cat > /app/start-production.sh << 'EOF'
set -e

echo "🚀 Starting MCP Client in Production Mode..."
echo "=================================="
echo "Environment: $ENVIRONMENT"
echo "Backend: http://0.0.0.0:5001"
echo "Frontend: http://0.0.0.0:5002"
echo "=================================="

echo "🔧 Starting Backend API..."
python -m client.scripts.start_backend production --host 0.0.0.0 --port 5001 &
BACKEND_PID=$!
echo "Backend PID: $BACKEND_PID"

echo "⏳ Waiting for backend to be ready..."
for i in {1..30}; do
    if curl -sf http://localhost:5001/api/v1/health/health > /dev/null 2>&1; then
        echo "✅ Backend is ready!"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ Backend failed to start within 30 seconds"
        kill $BACKEND_PID 2>/dev/null || true
        exit 1
    fi
    sleep 1
done

echo "🎨 Starting Frontend..."
python -m client.scripts.start_frontend production --host 0.0.0.0 --port 5002 --headless &
FRONTEND_PID=$!
echo "Frontend PID: $FRONTEND_PID"

cleanup() {
    echo "🛑 Shutting down services..."
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
    wait $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
    echo "👋 Shutdown complete"
}

trap cleanup SIGTERM SIGINT

echo "✅ All services started successfully!"
echo "📊 Backend Health: http://localhost:5001/api/v1/health/health"
echo "📊 Frontend UI: http://localhost:5002"

wait
EOF

RUN chmod +x /app/start-production.sh
RUN chown mcpuser:mcpuser /app/start-production.sh
USER mcpuser

CMD ["/app/start-production.sh"] 