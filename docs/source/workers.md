# Worker Libraries

Tierkreis workers come in three flavors:

- Builtin workers, provided by Tierkreis itself
- User defined workers, by using the `@worker.task()` annotation or writing external ones
- Prepackaged workers from the Tierkreis developers

This document outlines the functionality of the prepackaged workers.
Currently there are three workers provided as separate packages on pypi:

- Qiskit Aer
- Pytket
- Quantinuum Nexus

## Qiskit Aer

Compile and run quantum circuits locally with Qiskit Aer.
More detailed docs [here](worker/aer_worker.md).

**Example**

See the example `hamiltonian_graph.py`.

## Pytket

The pytket compiler suite to optimize circuits.
The worker only contains a subset of common operations.
For a custom compilation pipeline it is advised to build your own worker.

More detailed docs [here](worker/pytket_worker.md).

**Installation**

```sh
pip install tkr-pytket-worker
```

will install an executable Python script `tkr_pytket_worker` into your virtual environment.

**Example**

See the example `hamiltonian_graph.py`.

## Quantinuum Nexus

Interface to the Quantinuum Nexus platform.
More detailed docs [here](worker/nexus_worker.md).
