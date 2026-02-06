FROM python:3.12-slim-bookworm

# Install uv provided by Astral
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Install system dependencies
# R2R requires these for PDF parsing (poppler) and other tasks
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ musl-dev curl libffi-dev gfortran libopenblas-dev \
    poppler-utils \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1
# Copy from the cache instead of linking since it's a mounted volume
ENV UV_LINK_MODE=copy

# Place executables in the environment at the front of the path
WORKDIR /app
ENV PATH="/app/.venv/bin:$PATH"

# Install system dependencies if needed (e.g. for building packages)
# RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

# Copy the file(s) separately to prevent invalidating the cache
COPY pyproject.toml uv.lock ./

# Install the project's dependencies using the lockfile
RUN uv sync --frozen --no-install-project

# Copy the rest of the project
COPY . .

# Install the project itself
RUN uv sync --frozen

# Default command
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
