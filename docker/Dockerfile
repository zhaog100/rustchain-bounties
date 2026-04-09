FROM python:3.11-slim

LABEL maintainer="RustChain Community"
LABEL description="RustChain Miner - One Command Setup"

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl jq wget \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt 2>/dev/null || true

# Copy node code
COPY node/ ./node/
COPY scripts/ ./scripts/ 2>/dev/null || true

# Environment variables with defaults
ENV RUSTCHAIN_WALLET="" \
    RUSTCHAIN_NODE_URL="https://api.rustchain.io" \
    RUSTCHAIN_MINER_THREADS=1 \
    RUSTCHAIN_LOG_LEVEL=info

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Entry point
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8080
ENTRYPOINT ["/entrypoint.sh"]
