# Pytket worker

A Tierkreis worker that interacts with the Quantinuums `pytket` toolkit.

The pytket worker largely wraps the functionality from [tket](https://github.com/CQCL/tket).

## Installation

```sh
pip install tkr-pytket-worker
```

will install an executable Python script `tkr_pytket_worker` into your virtual environment.

## Authentication

Certain backends, such as the Quantinnuum backend require authentication.
The worker uses the default mechanisms provided by the `qnexus` Python package.

```bash
uv run python -c "from qnexus.client.auth import login; login()"
```

will put the a token in the appropriate filesystem location for subsequent operations to use.

To use IBMQ services, the credentials are expected to be stored in a file ` $HOME/.qiskit/qiskit-ibm.json` for more see the [Qiskit Documentation](https://quantum.cloud.ibm.com/docs/en/guides/cloud-setup)

## Elementary tasks

The pytket worker exposes the following elementary tasks to the user:

- `get_backend_info` retrieves the backend info given a configuration dict, might require authentication.
- `compile_using_info` compiles a circuit with a default pass for a backend info that was previously acquired.
- `ibmq_offline_pass` gets the offline pass for an IBMQ backend info object. Requires IBMQ authentication.
- `quantinuum_offline_pass` gets the offline pass for an Quantinuum backend info object. Requires IBMQ authentication. Requires Quantinuum Nexus authentication.
- `add_measure_all` adds final measurements to a circuit.
- `append_pauli_measurement_impl` adds measurements according to a Pauli string to a circuit.
- `optimise_phase_gadgets` applies the phase gadget optimization pass to a circuit.
- `apply_pass` applies a user defined optimization pass.
- `compile` generic compile function with a variety of options
- `compile_circuit_quantinuum` and `compile_circuits_quantinuum` apply a predefined level 3 optimization for Quantinuum devices to a (list of) circuit.
- `compile_tket_circuit_ibm` and `compile_tket_circuits_ibm` applies the pytket default pass for IBM devices to a (list of) circuit. Requires IBMQ authentication.
- `compile_tket_circuit_quantinuum` and `compile_tket_circuits_quantinuum` applies the pytket default pass for Quantinuum devices to a (list of) circuit. Requires Quantinuum Nexus authentication.
- `to_qasm_str` and `from_qasm_str` transforms a Circuit to/from QASM 2.
- `to_qir_bytes` and `from_qir_bytes` transforms a Circuit to/from QIR. Requires optional dependencies `uv sync --groups qir`.
- `expectation` estimates the expectation value from shot counts.
- `n_qubits` returns the number of qubits in a const circuit.

The straight forward approach to compiling a circuit with the default pass for a backend is:

1. Construct a `qnx.BackendConfig` object defining the desired backend
2. Get the according `pytket.BackendInfo` object
3. Provide both together with a circuit to immediately compile the circuit for the backend.

## Example

An example use is in `examples/pytket_graph.py` in the [Tierkreis repo](https://github.com/CQCL/tierkreis), which runs on a named IBM backend, e.g. `"ibm_torino"`.
For debugging purposes this also showcases how to use the `InMemoryExecutor` which only works in conjunction with the `InMemoryStorage`.

```python
class IBMInput(NamedTuple):
    circuit: TKR[OpaqueType["pytket._tket.circuit.Circuit"]]  # noqa: F821
    n_shots: TKR[int]
    backend: TKR[str]


def compile_run_single():
    g = GraphBuilder(
        IBMInput, TKR[OpaqueType["pytket.backends.backendresult.BackendResult"]]
    )

    compiled_circuit = g.task(
        compile_tket_circuit_ibm(
            circuit=g.inputs.circuit,
            backend_name=g.inputs.backend,
            optimization_level=g.const(2),
        )
    )
    res = g.task(submit_single(compiled_circuit, g.inputs.n_shots))
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
        "circuit": ghz(),
        "n_shots": n_shots,
        "backend": "<ibm_backend>", # e.g. ibm_torino
    },
)
res = read_outputs(g, storage)
print(res)
```
