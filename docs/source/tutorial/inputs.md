---
file_format: mystnb
kernelspec:
  name: python3
---

# Graph inputs and outputs

To create this graph we need only to install the `tierkreis` package:

```
pip install tierkreis
```

# Graph

Like Python functions, Tierkreis graphs can have input and output arguments.
We use the constructor of `GraphBuilder` to indicate that our function takes a single integer to a single integer:

```{code-cell} ipython3
from tierkreis.builder import GraphBuilder
from tierkreis.models import TKR

# f(x) = 2x + 1
f = GraphBuilder(TKR[int], TKR[int])
```

The implementation of this graph can be done entirely using Tierkreis built-in functions:

```{code-cell} ipython3
from tierkreis.builtins.stubs import iadd, itimes

double = f.task(itimes(f.const(2), f.inputs))
f_out = f.task(iadd(double, f.const(1)))
f.outputs(f_out)
```

However a Tierkreis graph can also have multiple inputs and multiple outputs.
To indicate that more than one input/output is required we use the `@portmapping` decorator applied to a Python `NamedTuple`.
This tells Tierkreis to interpret the different attributes of the `NamedTuple` as different inputs/outputs, rather than attributes of a nested structure within the same input/output.

```{code-cell} ipython3
from typing import NamedTuple

from tierkreis.builder import GraphBuilder
from tierkreis.builtins.stubs import iadd
from tierkreis.models import portmapping, TKR


@portmapping
class FibData(NamedTuple):
    a: TKR[int]
    b: TKR[int]


fib_step = GraphBuilder(FibData, FibData)
sum = fib_step.task(iadd(fib_step.inputs.a, fib_step.inputs.b))
fib_step.outputs(FibData(fib_step.inputs.b, sum))

```

If we omitted the `@portmapping` decorator then the graph would run the same in this example.
This is because we are running this graph in isolation from other graphs.
The difference becomes apparent when we start creating [Nested graphs with Eval](eval.md), which is next in the tutorial.

We can combine the various types of inputs and outputs in the natural way.
For instance the following are all valid ways to construct a `GraphBuilder` object:

```{code-cell} ipython3
@portmapping
class MultiPortInputData(NamedTuple):
    a: TKR[int]
    b: TKR[str]

@portmapping
class MultiPortOutputData(NamedTuple):
    a: TKR[str]
    b: TKR[list[int]]

g = GraphBuilder(TKR[int], TKR[str])
g = GraphBuilder(MultiPortInputData, MultiPortOutputData)
g = GraphBuilder(TKR[str], MultiPortOutputData)
g = GraphBuilder(MultiPortInputData, TKR[str])
```

# Execution

Since we still only use built-in functions, we execute the graph in the same way as before.

```{code-cell} ipython3
from uuid import UUID
from pathlib import Path

from tierkreis import run_graph
from tierkreis.storage import FileStorage, read_outputs
from tierkreis.executor import ShellExecutor

storage = FileStorage(UUID(int=99), name="My first graph")
executor = ShellExecutor(Path("."), logs_path=storage.logs_path)

storage.clean_graph_files()
run_graph(storage, executor, f.get_data(), 10)
print(read_outputs(storage))

storage.clean_graph_files()
run_graph(storage, executor, fib_step.get_data(), {'a': 0, 'b': 1})
print(read_outputs(storage))
```
