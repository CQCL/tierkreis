FROM python:3.10-slim
RUN apt update && apt install -y protobuf-compiler
RUN pip install build

RUN pip install poetry==1.6.1

WORKDIR /opt/tierkreis/python
COPY tierkreis tierkreis
COPY protos protos
COPY pyproject.toml pyproject.toml

WORKDIR /opt/tierkreis/python/pytket_worker
COPY pytket_worker/pyproject.toml pyproject.toml
COPY pytket_worker/poetry.lock poetry.lock
COPY pytket_worker/pytket_worker/main.py pytket_worker/main.py
RUN poetry install

COPY pytket_worker .
CMD poetry run python -m pytket_worker.main --port 80