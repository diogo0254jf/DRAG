# Stage 1: Builder
FROM python:3.13-slim-bookworm AS builder

# Install uv provided by Astral
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Install system dependencies for building
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ musl-dev libffi-dev gfortran libopenblas-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies into virtual environment
RUN uv sync --frozen --no-install-project

# Copy project files
COPY . .

# Install the project itself
RUN uv sync --frozen

# Stage 2: Runtime
FROM python:3.13-slim-bookworm

# Environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Install runtime dependencies
# poppler-utils for R2R, curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    poppler-utils curl libopenblas0 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Create a non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copy application from builder
# We copy the entire /app directory which includes .venv and source code
COPY --from=builder --chown=appuser:appuser /app /app

# Ensure scripts are executable
RUN chmod +x /app/scripts/*.sh

# Switch to non-root user
USER appuser

# Healthcheck
HEALTHCHECK --interval=30s --timeout=3s \
  CMD curl -f http://localhost:8000/ || exit 1

# Default command
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
