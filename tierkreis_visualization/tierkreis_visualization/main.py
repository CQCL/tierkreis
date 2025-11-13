import os
from sys import argv
from uuid import UUID

from tierkreis_visualization.config import CONFIG
import uvicorn


def start() -> None:
    uvicorn.run("tierkreis_visualization.app:app")


def dev() -> None:
    uvicorn.run("tierkreis_visualization.app:app", reload=True)


def graph() -> None:
    """Visualize a computation graph in a web browser.

    :param graph: The computation graph to visualize.
    :type graph: GraphData
    :param storage: The storage backend to use for the visualization.
    :type storage: ControllerStorage | None. Defaults to GraphDataStorage.
    """
    reload_path = argv[1].split(":", 1)[0]
    uvicorn.run(
        "tierkreis_visualization.app:app_graph_data",
        reload=True,
        reload_includes=reload_path,
    )


if __name__ == "__main__":
    start()
