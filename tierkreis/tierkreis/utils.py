from datetime import datetime
from uuid import UUID
from unittest.mock import MagicMock, patch
import logging
import os

from tierkreis.controller.data.graph import GraphData
from tierkreis.controller.storage.graphdata import GraphDataStorage
from tierkreis_visualization.data.workflows import WorkflowDisplay
from tierkreis_visualization.main import start

logger = logging.getLogger(__name__)


@patch("tierkreis_visualization.routers.workflows.get_storage")
@patch("tierkreis_visualization.routers.workflows.get_workflows")
def visualize_graph(
    graph: GraphData,
    get_workflows: MagicMock,
    get_storage: MagicMock,
) -> None:
    """Visualize a computation graph in a web browser.

    :param graph: The computation graph to visualize.
    :type graph: GraphData
    :param get_workflows: Internal; Used to inject the workflow retrieval mock.
    :type get_workflows: MagicMock
    :param get_storage: Internal; Used to inject the storage mock.
    :type get_storage: MagicMock
    """
    storage = GraphDataStorage(UUID(int=0), graph=graph)
    os.environ["TKR_STORAGE"] = "GraphDataStorage"
    get_workflows.return_value = [
        WorkflowDisplay(id=UUID(int=0), id_int=0, name="tmp", start=str(datetime.now()))
    ]
    get_storage.return_value = storage

    start()
