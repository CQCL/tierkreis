# Workers

A worker implements _atomic_ functionalities that will not be broken further by the controller.
Tierkreis workers come in three flavors:

- Builtin workers, provided by Tierkreis itself
- User defined workers, by using the `@worker.task()` annotation or writing external ones
- Prepackaged workers from the Tierkreis developers

```{toctree}
:maxdepth: 2
complex_types.md
external_workers.md
hello_world.md
native_workers/index
```

## Prepackaged workers

The following outlines the functionality of the prepackaged workers.
Currently the following workers are provided as separate packages on pypi:

- IBMQ
- Qiskit Aer
- Pytket
- Quantinuum Nexus
- Quantinuum Backend

### Qiskit Aer

Compile and run quantum circuits locally with Qiskit Aer.
More detailed docs [here](worker/native_workers/aer_worker.md).

### IBMQ

Compile and run quantum circuits locally with IBMQ.
More detailed docs [here](worker/native_workers/ibmq_worker.md).

### Pytket

The pytket compiler suite to optimize circuits.
The worker only contains a subset of common operations.
For a custom compilation pipeline it is advised to build your own worker.

More detailed docs [here](worker/native_workers/pytket_worker.md).

**Installation**

```sh
pip install tkr-pytket-worker
```

will install an executable Python script `tkr_pytket_worker` into your virtual environment.

**Example**

See the example `hamiltonian_graph.py`.

### Quantinuum Nexus

Interface to the Quantinuum Nexus platform.
More detailed docs [here](worker/native_workers/nexus_worker.md).

### Quantinuum Backend

Compile and run quantum circuits locally with Quantinuum backends.
More detailed docs [here](worker/native_workers/quantinuum_worker.md).

### Qulacs

Compile and run quantum circuits locally with Qulacs.
More detailed docs [here](worker/native_workers/qulacs_worker.md).
