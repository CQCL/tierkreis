from time import sleep

from tierkreis.controller.data.graph import Eval, GraphData
from tierkreis.controller.executor.protocol import ControllerExecutor
from tierkreis.controller.data.location import NodeLocation, OutputLocation
from tierkreis.controller.start import NodeRunData, start, start_nodes
from tierkreis.controller.storage.protocol import ControllerStorage
from tierkreis.controller.storage.walk import walk_node
from tierkreis.core import Labels
from tierkreis.core.function import FunctionName
from tierkreis.core.tierkreis_graph import FunctionNode, PortID, TierkreisGraph

root_loc = NodeLocation(location=[])


def run_graph(
    storage: ControllerStorage,
    executor: ControllerExecutor,
    g: GraphData,
    graph_inputs: dict[str, bytes],
    n_iterations: int = 10000,
    polling_interval_seconds: float = 0.01,
) -> None:
    for name, value in graph_inputs.items():
        storage.write_output(root_loc.append_node(-2), name, value)

    inputs: dict[PortID, OutputLocation] = {
        k: (root_loc.append_node(-2), k) for k, v in graph_inputs.items()
    }
    node_run_data = NodeRunData(
        root_loc,
        Eval((0, Labels.THUNK), {}),
        inputs,
        list(g.outputs[-1]),  # TODO: remove magic value -1
    )  # TODO: put inputs in Eval
    start(storage, executor, node_run_data)
    resume_graph(storage, executor, n_iterations, polling_interval_seconds)


def resume_graph(
    storage: ControllerStorage,
    executor: ControllerExecutor,
    n_iterations: int = 10000,
    polling_interval_seconds: float = 0.01,
) -> None:
    for i in range(n_iterations):
        walk_results = walk_node(storage, root_loc)
        start_nodes(storage, executor, walk_results.inputs_ready)
        if storage.is_node_finished(root_loc):
            break
        sleep(polling_interval_seconds)
