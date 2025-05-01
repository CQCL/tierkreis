uvrun := "uv run"

setup:
    uv sync --all-extras

default:
  @just --list

test:
    {{uvrun}} pytest python --doctest-modules --cov-report=html --cov-report=term

lint:
	{{uvrun}} ruff format --check
	{{uvrun}} ruff check
	cd python && {{uvrun}} pyright

fix:
	{{uvrun}} ruff check --fix
