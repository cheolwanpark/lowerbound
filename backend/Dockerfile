# Multi-stage Dockerfile using uv for fast dependency installation

FROM python:3.11-slim AS builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set working directory
WORKDIR /app

# Copy project files for dependency installation
COPY pyproject.toml README.md ./
COPY src ./src

# Install dependencies using uv
RUN uv pip install --system --no-cache .

# Production image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY src ./src
COPY pyproject.toml ./

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Default command (can be overridden in docker-compose)
CMD ["uvicorn", "src.server:app", "--host", "0.0.0.0", "--port", "8000"]
