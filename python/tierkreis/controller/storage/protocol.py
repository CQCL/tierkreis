from pathlib import Path
from typing import Protocol

from tierkreis.controller.data.location import (
    NodeDefinition,
    NodeLocation,
    OutputLocation,
)
from tierkreis.core.tierkreis_graph import PortID


class ControllerStorage(Protocol):
    def write_node_definition(
        self,
        node_location: NodeLocation,
        function_name: str,
        inputs: dict[PortID, OutputLocation],
        output_list: list[PortID],
    ) -> Path: ...

    def read_node_definition(self, node_location: NodeLocation) -> NodeDefinition: ...

    def mark_node_finished(self, node_location: NodeLocation) -> None: ...

    def is_node_finished(self, node_location: NodeLocation) -> bool: ...

    def link_outputs(
        self,
        new_location: NodeLocation,
        new_port: PortID,
        old_location: NodeLocation,
        old_port: PortID,
    ) -> None: ...

    def write_output(
        self, node_location: NodeLocation, output_name: PortID, value: bytes
    ) -> Path: ...

    def read_output(
        self, node_location: NodeLocation, output_name: PortID
    ) -> bytes: ...

    def read_output_ports(self, node_location: NodeLocation) -> list[PortID]: ...

    def is_node_started(self, node_location: NodeLocation) -> bool: ...
