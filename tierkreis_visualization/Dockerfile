# An example of using standalone Python builds with multistage images.

# First, build the application in the `/tierkreis/tierkreis/controller/builtins` directory
FROM ghcr.io/astral-sh/uv:bookworm-slim AS builder
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# Configure the Python directory so it is consistent
ENV UV_PYTHON_INSTALL_DIR=/python

# Only use the managed Python version
ENV UV_PYTHON_PREFERENCE=only-managed

# Install Python before the project for caching
RUN uv python install 3.12

COPY . /tierkreis
WORKDIR /tierkreis
RUN --mount=type=cache,target=/root/.cache/uv uv sync --no-dev

# Then, use a final image without uv
FROM debian:bookworm-slim

# Copy the Python version
COPY --from=builder --chown=python:python /python /python

# Copy the application from the builder
COPY --from=builder --chown=app:app /tierkreis /tierkreis

# Place executables in the environment at the front of the path
ENV PATH="/tierkreis/.venv/bin:$PATH"

# Run the worker by default
CMD ["sleep", "5m"]