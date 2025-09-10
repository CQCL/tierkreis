FROM ghcr.io/astral-sh/uv:bookworm-slim AS builder

RUN apt-get update && apt-get install -y git
RUN uv python install 3.12

COPY pyproject.toml /tierkreis/pyproject.toml
COPY uv.lock /tierkreis/uv.lock
COPY tierkreis /tierkreis/tierkreis
COPY tierkreis_workers/aer_worker /tierkreis/tierkreis_workers/aer_worker
WORKDIR /tierkreis/tierkreis_workers/aer_worker/
RUN uv sync --no-dev

WORKDIR "/tierkreis/tierkreis_workers/aer_worker/"
CMD ["uv", "run", "/tierkreis/tierkreis_workers/aer_worker/main.py"]