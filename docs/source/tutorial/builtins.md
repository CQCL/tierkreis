---
file_format: mystnb
kernelspec:
  name: python3
---

# Graph using built-in tasks

To create this graph we need only to install the `tierkreis` package:

```
pip install tierkreis
```

## Constructing the graph

First we instantiate a `GraphBuilder` object.
The arguments to the constructor describe the inputs and outputs of the graph respectively.
This graph has no inputs and outputs a single integer.

```{code-cell} ipython3
from tierkreis.builder import GraphBuilder
from tierkreis.controller.data.core import EmptyModel
from tierkreis.controller.data.models import TKR

g = GraphBuilder(EmptyModel, TKR[int])
```

In general a graph can have a multiple inputs and multiple outputs
but for now we keep things simple.

```{note}
In order to keep a clear separation between the types used in the Tierkreis graph and the types already present in the Python language we wrap the former with `TKR`.
For more information please see [types in Tierkreis]().
```

We can add constants to a graph using `GraphBuilder.const`.

```{code-cell} ipython3
one: TKR[int] = g.const(1)
two: TKR[int] = g.const(2)
```

The constants will be added into the data structure defining the graph.
In particular if the graph is ever serialised then these constants will be hard-coded into that serialisation.

We can add tasks using `GraphBuilder.task`:

```{code-cell} ipython3
from tierkreis.builtins.stubs import iadd

three: TKR[int] = g.task(iadd(g.const(1), g.const(2)))
```

In this example we import the type stubs provided by the Tierkreis library for the built-in functions.
This allows us to use the [pyright](https://github.com/microsoft/pyright) static analysis tool to check that the input and outputs types of the tasks are what we expect them to be.

To finish, we specify the output of the graph.

```{code-cell} ipython3
g.outputs(three)
```

## Running the graph

```{code-cell} ipython3
from pathlib import Path
from uuid import UUID

from tierkreis.controller import run_graph
from tierkreis.controller.data.location import Loc
from tierkreis.controller.executor.shell_executor import ShellExecutor
from tierkreis.controller.storage.filestorage import ControllerFileStorage

storage = ControllerFileStorage(UUID(int=99), name="My first graph")
executor = ShellExecutor(Path("."), logs_path=storage.logs_path)
storage.clean_graph_files()
run_graph(storage, executor, g.get_data(), {})
output = storage.read_output(Loc(), "value")
print(output)
```
