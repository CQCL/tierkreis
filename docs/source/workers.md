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

The qiskit simulation backend aer for local simulation of quantum circuits.

**Installation**

```sh
pip install tkr-aer-worker
```

will install an executable Python script `tkr_aer_worker` into your virtual environment.

**Example**

See the example `hamiltonian_graph.py`.

## Pytket

The pytket compiler suite to optimize circuits.
The worker only contains a subset of common operations.
For a custom compilation pipeline it is advised to build your own worker.

**Installation**

```sh
pip install tkr-pytket-worker
```

will install an executable Python script `tkr_pytket_worker` into your virtual environment.

**Authentication**
Certain backends, such as the IBMQ backend require authentication.
The worker uses the default mechanism provided by the service.
For example, to use IBMQ services, the credentials are expected to be stored in a file ` $HOME/.qiskit/qiskit-ibm.json` for more see the [Qiskit Documentation](https://quantum.cloud.ibm.com/docs/en/guides/cloud-setup)

**Example**

See the example `hamiltonian_graph.py`.

## Quantinuum Nexus

Interface to the Quantinuum Nexus platform.
More detailed docs [here](worker/nexus_worker.md).
