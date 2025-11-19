from sys import argv

import uvicorn


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


if __name__ == "__main__":
    start()
