# Quantinuum Backend Worker

A Tierkreis worker that provides convenient features to compile and run circuits on Quantinuum backends using `pytket`.

## Installation

```sh
pip install tkr-quantinuum-worker
```

will install an executable Python script `tkr_quantinuum_worker` into your virtual environment.

## Authentication

````{important}
Accessing backends through require authentication.
The worker uses the default mechanisms provided by the `qnexus` Python package.
```bash
uv run python -c "from qnexus.client.auth import login; login()"
```

````

Tasks that require authentication are marked as such in the task list below.

## Elementary tasks

The Quantinuum worker exposes the following elementary tasks to the user:

- `get_backend_info` retrieves the backend info given a configuration dict. **Requires authentication**.
- `backend_pass_from_info` constructs a compilation pass using a backend info object. **Requires authentication**.
- `backend_default_compilation_pass` fetches the default pass given the device name. **Requires authentication**.
- `compile` fetches and applies the default compilation pass. **Requires authentication**.
- `compile_circuit_quantinuum` and `compile_circuits_quantinuum` applies a predefined compilation pass to a (list of) circuits.
- `run_circuit` Runs the circuit on the backend. **Requires authentication**.

## Example

```python
class QuantinuumInput(NamedTuple):
    circuit: TKR[OpaqueType["pytket._tket.circuit.Circuit"]]  # noqa: F821
    n_shots: TKR[int]
    backend: TKR[str]


def compile_run_single():
    g = GraphBuilder(
        QuantinuumInput, TKR[OpaqueType["pytket.backends.backendresult.BackendResult"]]
    )

    compiled_circuit = g.task(
        compile(
            circuit=g.inputs.circuit,
            device_name=g.inputs.backend,
            optimization_level=g.const(2),
        )
    )
    res = g.task(run_circuit(compiled_circuit, g.inputs.n_shots))
    g.outputs(res)
    return g

circuit = ...your circuit here...

storage = InMemoryStorage(UUID(int=109))
executor = InMemoryExecutor(
    Path(__file__).parent.parent / "tierkreis_workers", storage
)
n_shots = 30
run_graph(
    storage,
    executor,
    g,
    {
        "circuit": circuit,
        "n_shots": n_shots,
        "backend": "<ibmq_backend>", # e.g. ibm_pittsburgh
    },
)
res = read_outputs(g, storage)
print(res)
```
