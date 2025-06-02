from logging import getLogger
from tierkreis.codegen import format_namespace
from tierkreis.consts import TESTS_PATH
from tierkreis.controller.builtins.main import worker

logger = getLogger(__name__)


def test_codegen():
    print(format_namespace(worker.namespace))
    assert False


if __name__ == "__main__":
    with open(TESTS_PATH / "tkr_builtins.py", "w+") as fh:
        fh.write(format_namespace(worker.namespace))
