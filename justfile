uvrun := "uv run"

setup:
    uv sync --all-extras

default:
  @just --list

test_rust:
    {{uvrun}} cargo test --workspace --all-features

test_python:
    {{uvrun}} pytest python
    cd python && {{uvrun}} ../.github/workflows/run_with_server ../target/debug/tierkreis-server ../.github/workflows/pr_server_config.json pytest --host=localhost --port=8090 --client-only

fix_rust:
    cargo clippy --fix --allow-dirty --allow-staged --workspace --all-features

lint:
	{{uvrun}} ruff format --check
	{{uvrun}} ruff check
	cd python && {{uvrun}} pyright
	cargo fmt --check
	cargo clippy

fix_python:
	{{uvrun}} ruff check --fix

build:
	cargo build