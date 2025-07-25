from pathlib import Path
from uuid import UUID
from typing import Any, Literal
from unittest.mock import MagicMock, patch
import threading
import logging

from playwright.sync_api import sync_playwright, Error

from tierkreis.controller import run_graph
from tierkreis.controller.data.graph import GraphData
from tierkreis.controller.executor.in_memory_executor import InMemoryExecutor
from tierkreis.controller.storage.in_memory import ControllerInMemoryStorage
from tierkreis_visualization.data.workflows import WorkflowDisplay
from tierkreis_visualization.main import start

logger = logging.getLogger(__name__)


@patch("tierkreis_visualization.routers.workflows.get_storage")
@patch("tierkreis_visualization.routers.workflows.get_workflows")
def visualize_graph(
    graph: GraphData,
    inputs: dict[str, Any],
    get_workflows: MagicMock,
    get_storage: MagicMock,
    default_browser: Literal["chromium", "webkit", "firefox"] = "chromium",
) -> None:
    storage = ControllerInMemoryStorage(UUID(int=0), name="tmp")
    executor = InMemoryExecutor(
        registry_path=Path("tierkreis/tierkreis"), storage=storage
    )
    run_graph(
        storage, executor, graph, inputs, n_iterations=50, polling_interval_seconds=0
    )

    get_workflows.return_value = [WorkflowDisplay(id=UUID(int=0), id_int=0, name="tmp")]
    get_storage.return_value = storage

    server_thread = threading.Thread(target=start, daemon=True)
    server_thread.start()
    with sync_playwright() as plw:
        try:
            browser_type = {
                "chromium": plw.chromium,
                "firefox": plw.firefox,
                "webkit": plw.webkit,
            }
            browser = browser_type[default_browser].launch(headless=False)
            page = browser.new_page()
            page.goto("http://127.0.0.1:8000")
            page.evaluate("() => localStorage.clear()")
            page.reload()

            page.wait_for_event("close")

        except Error as e:
            logger.error("Browser was closed prematurely: %s", e)
        finally:
            logger.info("\nBrowser closed! Resuming Python script.")
            server_thread.join(timeout=5)


@patch("tierkreis_visualization.routers.workflows.get_storage")
@patch("tierkreis_visualization.routers.workflows.get_workflows")
def visualize_graph_symbolic(
    graph: GraphData,
    get_workflows: MagicMock,
    get_storage: MagicMock,
    default_browser: Literal["chromium", "webkit", "firefox"] = "chromium",
) -> None:
    storage = ControllerInMemoryStorage(UUID(int=0), name="tmp")
    storage.evaluate_symbolic(graph)
    get_workflows.return_value = [WorkflowDisplay(id=UUID(int=0), id_int=0, name="tmp")]
    get_storage.return_value = storage

    server_thread = threading.Thread(target=start, daemon=True)
    server_thread.start()
    with sync_playwright() as plw:
        try:
            browser_type = {
                "chromium": plw.chromium,
                "firefox": plw.firefox,
                "webkit": plw.webkit,
            }
            browser = browser_type[default_browser].launch(headless=False)
            page = browser.new_page()
            page.goto("http://127.0.0.1:8000")
            page.evaluate("() => localStorage.clear()")
            page.reload()

            page.wait_for_event("close", timeout=0)

        except Error as e:
            logger.error("Browser was closed prematurely: %s", e)
        finally:
            logger.info("\nBrowser closed! Resuming Python script.")
            server_thread.join(timeout=1)
