from sys import argv

import uvicorn
from tierkreis.builder import GraphBuilder
from tierkreis.controller.data.graph import GraphData

from tierkreis_visualization.app import app_from_graph_data


def start() -> None:
    uvicorn.run("tierkreis_visualization.app:get_filestorage_app")


def dev() -> None:
    uvicorn.run("tierkreis_visualization.app:get_filestorage_app", reload=True)


def graph() -> None:
    """Visualize a computation graph in a web browser.

    Entrypoint for the project script tkr-vis-graph.
    """
    reload_path = argv[1].split(":", 1)[0]
    uvicorn.run(
        "tierkreis_visualization.app:get_graph_data_app",
        reload=True,
        reload_includes=reload_path,
    )


def visualize_graph(graph_data: GraphData | GraphBuilder) -> None:
    """Visualize a computation graph in a web browser.

    :param graph_data: The computation graph to visualize.
    :type graph_data: GraphData | GraphBuilder
    """
    if isinstance(graph_data, GraphBuilder):
        graph_data = graph_data.get_data()
    app = app_from_graph_data(graph_data)
    uvicorn.run(app)


if __name__ == "__main__":
    start()
