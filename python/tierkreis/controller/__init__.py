from time import sleep

from tierkreis.controller.executor.protocol import ControllerExecutor
from tierkreis.controller.models import NodeLocation, OutputLocation
from tierkreis.controller.start import NodeRunData, start, start_nodes
from tierkreis.controller.storage.protocol import ControllerStorage
from tierkreis.controller.storage.walk import walk_node
from tierkreis.core.function import FunctionName
from tierkreis.core.tierkreis_graph import FunctionNode, PortID, TierkreisGraph

root_loc = NodeLocation(location=[])


def run_graph(
    storage: ControllerStorage,
    executor: ControllerExecutor,
    graph: TierkreisGraph,
    graph_inputs: dict[str, bytes],
    n_iterations: int = 10000,
    polling_interval_seconds: float = 0.01,
) -> None:
    for name, value in graph_inputs.items():
        storage.write_output(root_loc.append_node(-1), name, value)

    inputs: dict[PortID, OutputLocation] = {
        k: (root_loc.append_node(-1), k) for k, v in graph_inputs.items()
    }
    node_run_data = NodeRunData(
        root_loc, FunctionNode(FunctionName("eval")), inputs, graph.outputs()
    )
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
