from uuid import UUID
import logging
import os

from tierkreis.controller.data.graph import GraphData
from tierkreis.controller.storage.protocol import ControllerStorage
from tierkreis.controller.storage.graphdata import GraphDataStorage
from tierkreis_visualization.main import start_with_storage_fn

logger = logging.getLogger(__name__)


def visualize_graph(
    graph: GraphData,
) -> None:
    """Visualize a computation graph in a web browser.

    :param graph: The computation graph to visualize.
    :type graph: GraphData
    """
    storage = GraphDataStorage(UUID(int=0), graph=graph)
    os.environ["TKR_STORAGE"] = "GraphDataStorage"

    def get_storage(workflow_id: UUID) -> ControllerStorage:
        return storage

    start_with_storage_fn(get_storage)
    os.environ["TKR_STORAGE"] = "FileStorage"
