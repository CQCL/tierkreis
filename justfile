uvrun := "uv run"

default:
  @just --list

setup:
    uv sync --all-extras

test:
    {{uvrun}} pytest python --doctest-modules --cov-report=html --cov-report=term

lint:
	{{uvrun}} ruff format --check
	{{uvrun}} ruff check
	cd python && {{uvrun}} pyright .

fix:
	{{uvrun}} ruff format
	{{uvrun}} ruff check --fix
