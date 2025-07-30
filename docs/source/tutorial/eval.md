---
file_format: mystnb
kernelspec:
  name: python3
---

# Nested graphs using Eval

To create this graph we need only to install the `tierkreis` package:

```
pip install tierkreis
```

## Graph

We can run graphs from within other graphs by using `GraphBuilder.eval`.
Recall the `fib_step` graph that we wrote last time:

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

We create a graph `fib4` that calls `fib_step` three times.

```{code-cell} ipython3
from tierkreis.models import EmptyModel

fib4 = GraphBuilder(EmptyModel, TKR[int])
init = FibData(a=fib4.const(0), b=fib4.const(1))
two = fib4.eval(fib_step, init)
three = fib4.eval(fib_step, two)
four = fib4.eval(fib_step, three)
fib4.outputs(four.b)
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
run_graph(storage, executor, fib4.get_data(), {})
print(read_outputs(storage))
```
