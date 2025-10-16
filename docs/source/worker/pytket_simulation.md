# Pytket simulation

We can use the pytket worker to compile and simulate circuits using the Aer or Qulacs simulators.

The Aer worker largely wraps the functionality from [pytket-qiskit](https://github.com/CQCL/pytket-qiskit/).
The Qulacs worker largely wraps the functionality from [pytket-qulacs](https://github.com/CQCL/pytket-qulacs/).

## Backend configuration

We reuse the `AerConfig` and `QulacsConfig` from the [quantinuum schemas repo](https://github.com/quantinuum-dev/quantinuum-schemas).

```python
from quantinuum_schemas.models.backend_config import AerConfig, QulacsConfig
```

At present only the `simulation_method` and `n_qubits` parameters are passed through to the `Aer` simulator.

## Prepackaged graphs

The Tierkreis Python package provides a few of prepackaged graphs to make it easier to compile and simulate circuits.
Note that the same graph can be used to target both `Aer` and `Qulacs`;
the user can configure the backend by passing the appropriate config object to the graph.

`tierkreis.graphs.simulate.compile_run.compile_run` is intended for the common use case of compiling a list of circuits in parallel and then running them in parallel.
It can be included within a custom graph using `GraphBuilder.eval` or run as a standalone graph.

An example use is in `examples/simulate_in_parallel.py` in the [Tierkreis repo](https://github.com/CQCL/tierkreis), which looks like:

```python
config = AerConfig() or QulacsConfig()
circuits = ...your circuits here...

g = compile_run()
storage = FileStorage(UUID(int=107), do_cleanup=True)
executor = UvExecutor(PACKAGE_PATH / ".." / "tierkreis_workers", storage.logs_path)

run_graph(
    storage,
    executor,
    g,
    {
        "circuits": circuits,
        "n_shots": [30] * len(circuits),
        "config": config,
        "compilation_optimisation_level": 2,
    },
    polling_interval_seconds=0.1,
)
res = read_outputs(g, storage)
print(len(res))

```

The subgraph `tierkreis.graphs.simulate.compile_run.compile_run_single` can also be used if the user wants to do additional customisations.
