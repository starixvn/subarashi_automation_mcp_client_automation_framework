FROM python:3.11-slim as builder

WORKDIR /app

COPY pyproject.toml ./

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
    nginx \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY client/ ./client/
COPY config/ ./config/
COPY nginx.conf /etc/nginx/sites-available/default

RUN mkdir -p /app/logs && chmod 755 /app/logs
RUN rm -f /etc/nginx/sites-enabled/default && \
    ln -sf /etc/nginx/sites-available/default /etc/nginx/sites-enabled/default

RUN groupadd -r mcpuser && useradd -r -g mcpuser -d /app -s /bin/bash mcpuser

RUN mkdir -p /app/.streamlit && \
    mkdir -p /root/.streamlit && \
    echo '[server]' > /app/.streamlit/config.toml && \
    echo 'headless = true' >> /app/.streamlit/config.toml && \
    echo 'address = "127.0.0.1"' >> /app/.streamlit/config.toml && \
    echo 'port = 5002' >> /app/.streamlit/config.toml && \
    echo 'enableCORS = false' >> /app/.streamlit/config.toml && \
    echo 'enableXsrfProtection = false' >> /app/.streamlit/config.toml && \
    echo '' >> /app/.streamlit/config.toml && \
    echo '[browser]' >> /app/.streamlit/config.toml && \
    echo 'gatherUsageStats = false' >> /app/.streamlit/config.toml && \
    echo 'serverAddress = "127.0.0.1"' >> /app/.streamlit/config.toml && \
    echo 'serverPort = 5002' >> /app/.streamlit/config.toml && \
    cp /app/.streamlit/config.toml /root/.streamlit/config.toml && \
    touch /app/.streamlit/secrets.toml && \
    touch /root/.streamlit/secrets.toml && \
    chmod 755 /root/.streamlit && \
    chmod 644 /root/.streamlit/config.toml && \
    chmod 644 /root/.streamlit/secrets.toml && \
    chown -R mcpuser:mcpuser /app

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

EXPOSE 5000

ENV ENVIRONMENT=production
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

RUN echo '[supervisord]' > /etc/supervisor/conf.d/mcp-client.conf && \
    echo 'nodaemon=true' >> /etc/supervisor/conf.d/mcp-client.conf && \
    echo 'user=root' >> /etc/supervisor/conf.d/mcp-client.conf && \
    echo 'logfile=/app/logs/supervisord.log' >> /etc/supervisor/conf.d/mcp-client.conf && \
    echo 'pidfile=/var/run/supervisord.pid' >> /etc/supervisor/conf.d/mcp-client.conf && \
    echo '' >> /etc/supervisor/conf.d/mcp-client.conf && \
    echo '[program:nginx]' >> /etc/supervisor/conf.d/mcp-client.conf && \
    echo 'command=nginx -g "daemon off;"' >> /etc/supervisor/conf.d/mcp-client.conf && \
    echo 'autostart=true' >> /etc/supervisor/conf.d/mcp-client.conf && \
    echo 'autorestart=true' >> /etc/supervisor/conf.d/mcp-client.conf && \
    echo 'stdout_logfile=/app/logs/nginx.log' >> /etc/supervisor/conf.d/mcp-client.conf && \
    echo 'stderr_logfile=/app/logs/nginx_error.log' >> /etc/supervisor/conf.d/mcp-client.conf && \
    echo 'user=root' >> /etc/supervisor/conf.d/mcp-client.conf && \
    echo '' >> /etc/supervisor/conf.d/mcp-client.conf && \
    echo '[program:backend]' >> /etc/supervisor/conf.d/mcp-client.conf && \
    echo 'command=python -m client.scripts.start_backend production --host 127.0.0.1 --port 5001' >> /etc/supervisor/conf.d/mcp-client.conf && \
    echo 'directory=/app' >> /etc/supervisor/conf.d/mcp-client.conf && \
    echo 'autostart=true' >> /etc/supervisor/conf.d/mcp-client.conf && \
    echo 'autorestart=true' >> /etc/supervisor/conf.d/mcp-client.conf && \
    echo 'stdout_logfile=/app/logs/backend.log' >> /etc/supervisor/conf.d/mcp-client.conf && \
    echo 'stderr_logfile=/app/logs/backend_error.log' >> /etc/supervisor/conf.d/mcp-client.conf && \
    echo 'user=mcpuser' >> /etc/supervisor/conf.d/mcp-client.conf && \
    echo 'environment=PYTHONPATH=/app,ENVIRONMENT=production' >> /etc/supervisor/conf.d/mcp-client.conf && \
    echo '' >> /etc/supervisor/conf.d/mcp-client.conf && \
    echo '[program:frontend]' >> /etc/supervisor/conf.d/mcp-client.conf && \
    echo 'command=streamlit run /app/client/frontend/app.py --server.port 5002 --server.address 127.0.0.1 --server.headless true --server.enableCORS false --server.enableXsrfProtection false --browser.gatherUsageStats false' >> /etc/supervisor/conf.d/mcp-client.conf && \
    echo 'directory=/app' >> /etc/supervisor/conf.d/mcp-client.conf && \
    echo 'autostart=true' >> /etc/supervisor/conf.d/mcp-client.conf && \
    echo 'autorestart=true' >> /etc/supervisor/conf.d/mcp-client.conf && \
    echo 'stdout_logfile=/app/logs/frontend.log' >> /etc/supervisor/conf.d/mcp-client.conf && \
    echo 'stderr_logfile=/app/logs/frontend_error.log' >> /etc/supervisor/conf.d/mcp-client.conf && \
    echo 'user=root' >> /etc/supervisor/conf.d/mcp-client.conf && \
    echo 'environment=PYTHONPATH=/app,ENVIRONMENT=production' >> /etc/supervisor/conf.d/mcp-client.conf

RUN echo '#!/bin/bash' > /app/start-production.sh && \
    echo 'set -e' >> /app/start-production.sh && \
    echo '' >> /app/start-production.sh && \
    echo 'echo "🚀 Starting MCP Client in Production Mode..."' >> /app/start-production.sh && \
    echo 'echo "=================================="' >> /app/start-production.sh && \
    echo 'echo "Environment: $ENVIRONMENT"' >> /app/start-production.sh && \
    echo 'echo "Single Port: http://0.0.0.0:5000"' >> /app/start-production.sh && \
    echo 'echo "Backend (internal): http://127.0.0.1:5001"' >> /app/start-production.sh && \
    echo 'echo "Frontend (internal): http://127.0.0.1:5002"' >> /app/start-production.sh && \
    echo 'echo "=================================="' >> /app/start-production.sh && \
    echo '' >> /app/start-production.sh && \
    echo 'mkdir -p /app/logs' >> /app/start-production.sh && \
    echo 'chown -R mcpuser:mcpuser /app/logs' >> /app/start-production.sh && \
    echo 'chown -R mcpuser:mcpuser /app/.streamlit' >> /app/start-production.sh && \
    echo '' >> /app/start-production.sh && \
    echo 'exec /usr/bin/supervisord -c /etc/supervisor/conf.d/mcp-client.conf' >> /app/start-production.sh

RUN chmod +x /app/start-production.sh

CMD ["/app/start-production.sh"] 