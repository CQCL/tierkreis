from pathlib import Path

from tierkreis.controller.executor.protocol import ControllerExecutor
from tierkreis.exceptions import TierkreisError


class MultipleExecutor:
    def __init__(
        self,
        default: ControllerExecutor,
        executors: dict[str, ControllerExecutor],
        assignments: dict[str, str],
    ) -> None:
        self.default = default
        self.executors = executors
        self.assignments = assignments

    def run(self, launcher_name: str, node_definition_path: Path) -> None:
        executor_name = self.assignments.get(launcher_name, None)
        # If there is no assignment for the worker, use the default.
        if executor_name is None:
            return self.default.run(launcher_name, node_definition_path)

        executor = self.executors.get(executor_name)
        if executor is None:
            raise TierkreisError(
                f"{launcher_name} is assigned to non-existent executor name: {executor_name}."
            )

        return executor.run(launcher_name, node_definition_path)
