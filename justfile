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

[working-directory: 'tierkreis/tierkreis/builtins']
generate:
	{{uvrun}} main.py --stubs-path ./stubs.py
	{{uvrun}} ruff format stubs.py
	{{uvrun}} ruff check --fix stubs.py
