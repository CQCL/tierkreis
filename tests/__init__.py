from pathlib import Path
import os

LOCAL_SERVER_PATH = Path(__file__).parent / "../../target/debug/tierkreis-server"
release_tests: bool = os.getenv("TIERKREIS_RELEASE_TESTS") is not None
REASON = "TIERKREIS_RELEASE_TESTS not set."
