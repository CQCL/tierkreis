from tierkreis.consts import PACKAGE_PATH
from tierkreis.worker.codegen import format_schema
from tierkreis.controller.builtins.main import worker
from tierkreis.worker.schema import schema_from_namespace, write_schema


def test_schema():
    nsp = schema_from_namespace("Builtins", worker.namespace)
    hints = format_schema("Builtins", nsp)
    print(hints)
    assert False


if __name__ == "__main__":
    write_schema(worker, PACKAGE_PATH / "tests" / "codegen" / "builtins.py")
