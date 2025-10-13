from dataclasses import dataclass
from tierkreis.controller.executor.shell_executor import ShellExecutor
from tierkreis.controller.executor.uv_executor import UvExecutor
from tierkreis.controller.executor.multiple import MultipleExecutor
from tierkreis.controller.executor.hpc.pjsub import PJSUBExecutor


@dataclass
class BuiltInExecutor:
    pass


Executor = ShellExecutor | UvExecutor | BuiltInExecutor
__all__ = [
    "BuiltInExecutor",
    "ShellExecutor",
    "UvExecutor",
    "MultipleExecutor",
    "PJSUBExecutor",
    "Executor",
]
