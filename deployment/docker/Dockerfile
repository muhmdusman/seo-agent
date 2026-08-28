# Multi-stage build for optimized image size
FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv for faster dependency resolution
RUN pip install --no-cache-dir uv

# Copy dependency files
WORKDIR /build
COPY backend/pyproject.toml backend/uv.lock ./

# Install dependencies
RUN uv pip install --system --no-cache -r pyproject.toml

# Final stage
FROM python:3.11-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    redis-server \
    supervisor \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Create app user
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app /var/log/supervisor && \
    chown -R appuser:appuser /app /var/log/supervisor

WORKDIR /app

# Copy application code
COPY --chown=appuser:appuser backend/ .

# Copy supervisor configuration
COPY --chown=appuser:appuser deployment/docker/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run as non-root user
USER appuser

# Start supervisor (manages all services)
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
