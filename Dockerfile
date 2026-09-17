# ==========================================
# Stage 1: Build & Dependency Wheel Stage
# ==========================================
FROM python:3.12-slim AS builder

# Prevent Python from writing .pyc files and buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /install

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc python3-dev && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Install dependencies into a localized wheel folder
RUN pip install --no-cache-dir --prefix=/install/deps -r requirements.txt

# ==========================================
# Stage 2: Minimal Distroless/Production Runtime
# ==========================================
FROM python:3.12-slim AS runner

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/install/deps/bin:$PATH" \
    PYTHONPATH="/install/deps/lib/python3.12/site-packages"

WORKDIR /app

# Install curl for Docker HEALTHCHECK directive
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Create dedicated non-root system group and user
RUN groupadd -g 10001 appgroup && \
    useradd -u 10000 -g appgroup -s /sbin/nologin -d /app appuser

# Copy installed dependency artifacts from builder stage
COPY --from=builder /install/deps /install/deps

# Copy application source code
COPY config.py main.py cache.py limiter.py metrics.py ./

# Grant ownership of application directory to appuser
RUN chown -R appuser:appgroup /app

# Switch security context to non-root
USER appuser

# Expose standard application port
EXPOSE 8000

# Native health probe checking the /health endpoint every 15 seconds
HEALTHCHECK --interval=15s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start ASGI server bound to 0.0.0.0
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]