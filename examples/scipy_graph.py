from pathlib import Path
from typing import NamedTuple
from uuid import UUID
from tierkreis.builder import GraphBuilder
from tierkreis.consts import PACKAGE_PATH
from tierkreis.controller.data.core import EmptyModel
from tierkreis.controller.data.models import TKR, OpaqueType
from example_workers.scipy_worker.stubs import (
    transpose,
    reshape,
    linspace,
    add_point,
    eval_point,
)
from tierkreis.storage import FileStorage, read_outputs
from tierkreis.executor import UvExecutor
from tierkreis import run_graph

NDArray = OpaqueType["numpy.ndarray"]


class ScipyOutputs(NamedTuple):
    a: TKR[NDArray]
    p: TKR[float]


g = GraphBuilder(EmptyModel, ScipyOutputs)
onedim = g.task(linspace(g.const(0), g.const(10)))

pointed = g.task(add_point(onedim, g.const(0)))
scalar = g.task(eval_point(pointed))

twodim = g.task(reshape(onedim, g.const([5, 10])))
a = g.task(transpose(twodim))
g.outputs(ScipyOutputs(a, scalar))


if __name__ == "__main__":
    storage = FileStorage(UUID(int=207), do_cleanup=True, name="scipy_graph")
    executor = UvExecutor(Path(__file__).parent / "example_workers", storage.logs_path)
    run_graph(storage, executor, g, {})

    outputs = read_outputs(g, storage)
    print(outputs)
