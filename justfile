uvrun := "uv run"

default:
  @just --list

setup:
    uv sync --all-extras

test:
    {{uvrun}} pytest tierkreis --doctest-modules --cov=. --cov-report=html --cov-report=term

test-slow:
    {{uvrun}} pytest tierkreis --doctest-modules --cov=. --cov-report=html --cov-report=term --runslow

lint:
  {{uvrun}} ruff format --check
  {{uvrun}} ruff check
  {{uvrun}} pyright .

fix:
  {{uvrun}} ruff format
  {{uvrun}} ruff check --fix

docs:
  just docs/build	

[working-directory:'tierkreis_visualization']
serve:
	{{uvrun}} fastapi dev tierkreis_visualization/main.py

[working-directory:'tierkreis_visualization']
prod:
	bunx --bun vite build frontend
	cp -r frontend/dist tierkreis_visualization/static


examples:
  {{uvrun}} examples/hello_world_graph.py
  {{uvrun}} examples/error_handling_graph.py
  {{uvrun}} examples/symbolic_circuits.py
  {{uvrun}} examples/hamiltonian_graph.py
  {{uvrun}} examples/qsci_graph.py

stubs-generate dir:
  #!/usr/bin/env bash
  cd {{dir}}
  uv run main.py --stubs-path ./stubs.py
  uv run ruff format stubs.py
  uv run ruff check --fix stubs.py

generate: 
  just stubs-generate 'tierkreis/tierkreis/builtins'
  just stubs-generate 'tierkreis_workers/pytket_worker'
  just stubs-generate 'examples/example_workers/hello_world_worker'
  just stubs-generate 'examples/example_workers/error_worker'
