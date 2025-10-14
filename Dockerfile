# Multi-stage build: PyTorch official image + uv
# Stage 1: Get uv binary
FROM ghcr.io/astral-sh/uv:0.9-python3.12-bookworm AS uv

# Stage 2: Official PyTorch image (includes Python, PyTorch, CUDA)
FROM pytorch/pytorch:2.8.0-cuda12.9-cudnn9-runtime

# Copy uv from first stage
COPY --from=uv /usr/local/bin/uv /usr/local/bin/uv

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
