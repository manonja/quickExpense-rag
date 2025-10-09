# Use official uv image with Python 3.12
FROM ghcr.io/astral-sh/uv:0.9-python3.12-bookworm

# Set working directory
WORKDIR /app

# Copy project files
COPY pyproject.toml README.md ./
COPY src/ ./src/
COPY tests/ ./tests/

# Sync dependencies (this will install everything including torch)
RUN uv sync

# Default command - run bash
CMD ["/bin/bash"]
