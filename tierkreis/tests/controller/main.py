# /// script
# requires-python = ">=3.12"
# dependencies = ["pydantic", "tierkreis"]
#
# [tool.uv.sources]
# tierkreis = { path = "../../../tierkreis", editable = true }
# ///
from time import sleep
from sys import argv

from tierkreis import Worker, Value

worker = Worker("tests_worker")


@worker.task()
def sleep_and_return[T](*, output: T) -> Value[T]:
    sleep(10)
    return Value(value=output)


if __name__ == "__main__":
    worker.app(argv)
