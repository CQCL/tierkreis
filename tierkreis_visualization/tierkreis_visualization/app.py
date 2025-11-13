from pathlib import Path
from sys import argv
from fastapi.responses import FileResponse
from tierkreis_visualization.app_config import App, StorageType, lifespan, assets
from tierkreis_visualization.config import CONFIG
from tierkreis_visualization.storage import file_storage_fn, graph_data_storage_fn
from tierkreis_visualization.routers.workflows import router as workflows_router


def get_app():
    app = App(lifespan=lifespan)
    app.include_router(workflows_router, prefix="/api/workflows")
    app.mount("/assets/", assets, name="frontend_assets")

    @app.get("/{path:path}")
    def read_root():
        return FileResponse(
            Path(__file__).parent / "static" / "dist" / "index.html",
            media_type="text/html",
        )

    return app


def get_filestorage_app():
    app = get_app()
    app.state.get_storage_fn = file_storage_fn(CONFIG.tierkreis_path)
    app.state.storage_type = StorageType.FILESTORAGE
    return app


def get_graph_data_app():
    app = get_app()
    graph_specifier = argv[1] if len(argv) > 1 else CONFIG.graph_specifier

    if graph_specifier is None:
        return app

    app.state.get_storage_fn = graph_data_storage_fn(graph_specifier)[0]
    app.state.storage_type = StorageType.GRAPHDATA
    return app


app = get_filestorage_app()
app_graph_data = get_graph_data_app()
