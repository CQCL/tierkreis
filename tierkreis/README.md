# tierkreis

Tierkreis is a higher-order dataflow graph program representation and runtime
designed for compositional, quantum-classical hybrid algorithms.

For a detailed introduction read the paper:
 [Tierkreis: a Dataflow Framework for Hybrid Quantum-Classical Computing](https://arxiv.org/abs/2211.02350).

This repository contains the source for the `tierkreis` python package, and the
protocol buffer definitions for Tierkreis data types and gRPC services (in the `protos` directory) which define the protocols for the system.

The python package provides a complete development and testing environment for writing and running Tierkreis program, and allows you to write extensions ("workers") in python. By implementing the gRPC services you can also implement runtimes and workers in other languages.

## Getting Started

To install the python package run:
```bash
pip install tierkreis
```

This package is pure python and is compatible with Python 3.10 and above. Tierkreis has a strong, static type system, and full automated type inference is available as an extension on supported platforms via the `typecheck` optional feature. To install that run:

```bash
pip install tierkreis[typecheck]
```

You can now build a graph (Tierkreis program), optionally type check it and execute it. The recommended environment for this is a Jupyter notebook (especially given some operations are async).

First we need the runtime we are going to execute on and a handle to the primitive functions available on that runtime.
The python package comes with the `PyRuntime` which runs locally in your python environment.

```python
from tierkreis.builder import graph, Namespace, Output, ValueSource
from tierkreis.pyruntime import PyRuntime

cl = PyRuntime([]) # empty list for no extra workers
sig = await cl.get_signature()
ns = Namespace(sig) # get a handle to all functions
print(ns.iadd)
print(ns.unpack_pair)
```

The output shows the type signatures of the two functions we will use to add two integers together and unpack a pair. Note Tierkreis functions have named inputs _and_ outputs.
```
iadd(a: Int, b: Int) -> (value: Int)
unpack_pair(pair: Pair[VarType(a), VarType(b)]) -> (first: VarType(a), second: VarType(b))
```

### Build

The `@graph` decorator allows you to build graphs using python functions.

```python
@graph()
def sum_pair(pair: ValueSource) -> Output:
    first, second = ns.unpack_pair(pair) # tierkreis functions can have multiple outputs
    return Output(ns.iadd(first, second))
```

Calling the decorated function with no arguments (`sum_pair()`) returns a `TierkreisGraph`.

### Visualise
In an Jupyter notebook this is immediately visualised, as long as you have [Graphviz](https://graphviz.org/download/) installed. In a script you can write the image to file with `render_graph`:

```python
from tierkreis import render_graph

render_graph(sum_pair, "filename", "pdf")
```

![sum_pair graph](https://user-images.githubusercontent.com/12997250/199997054-8cc815e2-39d3-4a9c-95d0-411510cb5465.svg )

### Type check
If you have the `typecheck` extension installed, you can replace `@graph` with `@graph(type_check_sig=sig)`, providing the signature retrieved from the client as above, and the graph will be type checked when you call the building function. A graph is well-typed if type annotations can be inferred for every edge of the graph. If type check fails, the error message will try to indicate the location of your error.

The type checked version of the graph above looks like:

![sum_pair graph](https://user-images.githubusercontent.com/12997250/199996763-e0431127-1e6d-402c-acde-7711e12eb0ee.svg)


### Run graph

We can now run the graph using the client set up earlier:

```python
from tierkreis.core.types import TierkreisPair

await cl.run_graph(sum_pair, pair=TierkreisPair(1, 2))
```

The inputs to the graph are provided via keyword argument, and most of the time
you can just provide python values that are auto converted (for example
integers, floats, strings).
But here, since there is no exact Python equivalent for "Pair" we use the
tierkreis utility type `TierkreisPair`.
 The output is given
in Tierkreis form:
```
{'value': IntValue(value=3)}
```
## Examples

For a more involved example see [variational.ipynb](examples/variational.ipynb)


## Custom workers

_Workers_ are standalone servers which implement a set of functions which can connect to a Tierkreis runtime to add extra primitives.
They do this by implementing the `worker` gRPC service. The `tierkreis` python package makes it easy to do this by taking care of all the server logic, and the conversion to and from Tierkreis data types. Note that workers are intended to be deployed as part of remote Tierkreis runtimes, but we can use the PyRuntime to test and develop them without any networking code.

For example, we could define a custom function to sum a list:

```python
from tierkreis.worker.namespace import Namespace as WorkerNS
from tierkreis.builder import Const
root = WorkerNS()
custom_ns = root["custom"]

@custom_ns.function()
async def sum_list(lst: list[int]) -> int:
    return sum(lst)

cl = PyRuntime([root])
ns = Namespace(await cl.get_signature())["custom"]

@graph()
def runsum() -> Output:
    return Output(ns.sum_list(Const([1, 2, 3])))
await cl.run_graph(runsum)
```
