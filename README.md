# tierkreis

Tierkreis is a higher-order dataflow graph program representation and runtime
designed for compositional, quantum-classical hybrid algorithms.

For a detailed introduction read the paper: [Tierkreis: a Dataflow Framework for
Hybrid Quantum-Classical Computing](TODO_LINK).

This repository contains the source for the `tierkreis` python package, and the
protocol buffer definitions for Tierkreis data types and gRPC services (in the `protos` directory) which define the protocols for the system.

The python package provides a complete development and testing evironment for writing and running Tierkreis program, and allows you to write extensions ("workers") in python. By implementing the gRPC services you can also implement runtimes and workers in other languages.

## Getting Started

To install the python package run:
```shell
pip install tierkreis
```

This package is pure python and is compatible with Python 3.9 and above. Tierkreis has a strong, static type system, and full automated type inference is available as an extension on supported platforms via the `typecheck` optional feature. To install that to run:

```shell
pip install tierkreis[typecheck]
```
