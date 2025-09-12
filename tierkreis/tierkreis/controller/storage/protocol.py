from pathlib import Path
from typing import Any, Protocol

from tierkreis.controller.data.core import PortID
from tierkreis.controller.data.graph import NodeDef
from tierkreis.controller.data.location import (
    Loc,
    OutputLoc,
    WorkerCallArgs,
)


class ControllerStorage(Protocol):
    """The storage protocol defines interaction with the *state* of the computation.

    The controller progresses the computation by committing the output values of a computation to the storage.
    They can then in turn be picked up as inputs of dependent calculations.
    For this purpose the protocol exposes *read_...* and *write_...* functions.
    """

    logs_path: Path

    def write_node_def(self, node_location: Loc, node: NodeDef) -> None:
        """Stores the definition of the node defined at the given location.

        Example::

            controller_storage.write_node_def(
                Loc(), Input(name="prediction", inputs={})
            )

        Will store the {"name": "pred", "inputs": {},"type": "input"} at location "-".

        :param node_location: The location of the node.
        :type node_location: Loc
        :param node: The definition of the node.
        :type node: NodeDef
        """
        ...

    def read_node_def(self, node_location: Loc) -> NodeDef:
        """Loads the definition of the node defined at the given location.

        Example::

            controller_storage.read_node_def(Loc())

        Will return the node definition stored at location "-".

        :param node_location: The location of the node.
        :type node_location: Loc
        :return: The definition of the node.
        :rtype: NodeDef
        """
        ...

    def write_worker_call_args(
        self,
        node_location: Loc,
        function_name: str,
        inputs: dict[PortID, OutputLoc],
        output_list: list[PortID],
    ) -> Path:
        """Stores the call arguments for the function node at the given location.

        Function nodes will always be invoked by a worker.
        For example a node `Func("builtins.iadd", {"a": a, "b": b})`
        would be stored as::

            {
                "function_name": "builtins.iadd",
                "inputs": {
                    "a": Loc("a"),
                    "b": Loc("b")
                },
                "outputs": {"value": Loc("value")}
            }

        where inputs and outputs link the ports of different nodes.

        :param node_location: The location of the node.
        :type node_location: Loc
        :param function_name: The name of the function being called.
        :type function_name: str
        :param inputs: The inputs to the function.
        :type inputs: dict[PortID, OutputLoc]
        :param output_list: The list of outputs from the function.
        :type output_list: list[PortID]
        :return: The path to the stored call arguments, such that the worker can find them.
        :rtype: Path
        """
        ...

    def read_worker_call_args(self, node_location: Loc) -> WorkerCallArgs:
        """Loads the call arguments for the function node at the given location.

        :param node_location: The location of the node.
        :type node_location: Loc
        :return: The call arguments for the worker.
        :rtype: WorkerCallArgs
        """
        ...

    def read_errors(self, node_location: Loc) -> str:
        """Loads the error logs for the node at the given location.

        :param node_location: The location of the node.
        :type node_location: Loc
        :return: The error logs for the node.
        :rtype: str
        """
        ...

    def node_has_error(self, node_location: Loc) -> bool:
        """Checks if the node at the given location has encountered an error.

        :param node_location: The location of the node.
        :type node_location: Loc
        :return: True if the node has error logs, False otherwise.
        :rtype: bool
        """
        ...

    def write_node_errors(self, node_location: Loc, error_logs: str) -> None:
        """Writes the error messages for the node at the given location.

        For function nodes this allows workers to forward error messages to the controller.

        :param node_location: The location of the node.
        :type node_location: Loc
        :param error_logs: The error logs to write.
        :type error_logs: str
        """
        ...

    def mark_node_finished(self, node_location: Loc) -> None:
        """Marks the node at the given location as finished.

        :param node_location: The location of the node.
        :type node_location: Loc
        """
        ...

    def is_node_finished(self, node_location: Loc) -> bool:
        """Checks if the node at the given location is finished.

        :param node_location: The location of the node.
        :type node_location: Loc
        :return: True if the node is finished, False otherwise.
        :rtype: bool
        """
        ...

    def link_outputs(
        self,
        new_location: Loc,
        new_port: PortID,
        old_location: Loc,
        old_port: PortID,
    ) -> None:
        """Connects the output port of one node to the output port of another.

        This is useful when unwrapping nodes such that the output of a nested node
        can be reused as the output of the parent node.

        :param new_location: The location of the new node.
        :type new_location: Loc
        :param new_port: The port of the new node.
        :type new_port: PortID
        :param old_location: The location of the old node.
        :type old_location: Loc
        :param old_port: The port of the old node.
        :type old_port: PortID
        """
        ...

    def write_output(
        self, node_location: Loc, output_name: PortID, value: bytes
    ) -> Path:
        """Writes the output value for port of the node at the given location.

        :param node_location: The location of the node.
        :type node_location: Loc
        :param output_name: The name of the output port.
        :type output_name: PortID
        :param value: The value to write to the output port.
        :type value: bytes
        :return: The path to the written output.
        :rtype: Path
        """
        ...

    def read_output(self, node_location: Loc, output_name: PortID) -> bytes:
        """Reads the output value for the port of the node at the given location.

        :param node_location: The location of the node.
        :type node_location: Loc
        :param output_name: The name of the output port.
        :type output_name: PortID
        :return: The output value for the port.
        :rtype: bytes
        """
        ...

    def read_output_ports(self, node_location: Loc) -> list[PortID]:
        """Checks which output ports are available for the node at the given location.

        :param node_location: The location of the node.
        :type node_location: Loc
        :return: The list of output ports for the node.
        :rtype: list[PortID]
        """
        ...

    def is_node_started(self, node_location: Loc) -> bool:
        """Checks if the node at the given location has started.

        :param node_location: The location of the node.
        :type node_location: Loc
        :return: True if the node has started, False otherwise.
        :rtype: bool
        """
        ...

    def read_metadata(self, node_location: Loc) -> dict[str, Any]:
        """Reads the metadata for the node at the given location.

        :param node_location: The location of the node.
        :type node_location: Loc
        :return: The metadata for the node.
        :rtype: dict[str, Any]
        """
        ...

    def write_metadata(self, node_location: Loc) -> None:
        """Writes the metadata for the node at the given location.

        :param node_location: The location of the node.
        :type node_location: Loc
        """
        ...

    def read_started_time(self, node_location: Loc) -> str | None:
        """Reads the start time of a node

        :param node_location: The location of the node
        :type node_location: Loc
        :return: A time string when node has started, else None.
        :rtype: str | None
        """
        ...

    def read_finished_time(self, node_location: Loc) -> str | None:
        """Reads the finish time of a node

        :param node_location: The location of the node
        :type node_location: Loc
        :return: A time string when node is completed, else None.
        :rtype: str | None
        """
        ...
