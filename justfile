uvrun := "uv run"

default:
  @just --list

setup:
    uv sync --all-extras

test:
    {{uvrun}} pytest python --doctest-modules --cov=. --cov-report=html --cov-report=term

lint:
	{{uvrun}} ruff format --check
	{{uvrun}} ruff check
	{{uvrun}} pyright .

fix:
	{{uvrun}} ruff format
	{{uvrun}} ruff check --fix

serve:
	cd tierkreis_visualization && {{uvrun}} fastapi dev tierkreis_visualization/main.py