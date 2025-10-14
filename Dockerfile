# Multi-stage build: PyTorch official image + uv
# Stage 1: Official PyTorch image (includes Python, PyTorch, CUDA)
FROM pytorch/pytorch:2.8.0-cuda12.9-cudnn9-runtime

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
# Set working directory
WORKDIR /app

# Copy project files
COPY pyproject.toml README.md ./
COPY src/ ./src/
COPY tests/ ./tests/

# Sync dependencies (CUDA libraries already present, only need PyTorch CPU bindings)
RUN uv sync

# Default command - run bash
CMD ["/bin/bash"]
