import os
from pathlib import Path

LOCAL_SERVER_PATH = Path(__file__).parent / "../../target/debug/tierkreis-server"
release_tests: bool = os.getenv("TIERKREIS_RELEASE_TESTS") is not None
REASON = "TIERKREIS_RELEASE_TESTS is set."
PYTHON_TESTS_DIR = Path(__file__).parent.parent / "../python/tests"
PYTHON_WORKER = PYTHON_TESTS_DIR / "test_worker"
