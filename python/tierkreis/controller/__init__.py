import json
import logging
from time import sleep

from tierkreis.controller.data.graph import Eval, GraphData, ValueRef
from tierkreis.controller.data.location import Loc
from tierkreis.controller.executor.protocol import ControllerExecutor
from tierkreis.controller.start import NodeRunData, start, start_nodes
from tierkreis.controller.storage.protocol import ControllerStorage
from tierkreis.controller.storage.walk import walk_node
from tierkreis.controller.data.graph import PortID

root_loc = Loc("")
logger = logging.getLogger(__name__)


def run_graph(
    storage: ControllerStorage,
    executor: ControllerExecutor,
    g: GraphData,
    graph_inputs: dict[str, bytes],
    n_iterations: int = 10000,
    polling_interval_seconds: float = 0.01,
) -> None:
    storage.write_metadata(Loc(""))
    for name, value in graph_inputs.items():
        storage.write_output(root_loc.N(-1), name, value)

    storage.write_output(root_loc.N(-1), "body", g.model_dump_json().encode())

    inputs: dict[PortID, ValueRef] = {
        k: (-1, k) for k, _ in graph_inputs.items() if k != "body"
    }
    node_run_data = NodeRunData(Loc(), Eval((-1, "body"), inputs), [])
    start(storage, executor, node_run_data)
    resume_graph(storage, executor, n_iterations, polling_interval_seconds)


def resume_graph(
    storage: ControllerStorage,
    executor: ControllerExecutor,
    n_iterations: int = 10000,
    polling_interval_seconds: float = 0.01,
) -> None:
    message = storage.read_output(Loc().N(-1), "body")
    graph = GraphData(**json.loads(message))

    for _ in range(n_iterations):
        walk_results = walk_node(storage, Loc(), graph.output_idx(), graph)
        if walk_results.errored != []:
            node_errors = "\n".join(x for x in walk_results.errored)
            storage.write_node_errors(Loc(), node_errors)
            print("Graph finished with errors.")
            break
        start_nodes(storage, executor, walk_results.inputs_ready)
        if storage.is_node_finished(Loc()):
            break
        sleep(polling_interval_seconds)
