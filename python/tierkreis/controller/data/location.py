from dataclasses import dataclass
from enum import Enum
from logging import getLogger
from pathlib import Path
from typing import Optional

from pydantic import BaseModel
from typing_extensions import assert_never

from tierkreis.controller.data.graph import NodeDef
from tierkreis.core.tierkreis_graph import PortID
from tierkreis.exceptions import TierkreisError

logger = getLogger(__name__)


class WorkerCallArgs(BaseModel):
    function_name: str
    inputs: dict[str, Path]
    outputs: dict[str, Path]
    done_path: Path
    logs_path: Optional[Path]


class NodeType(Enum):
    NODE = 0
    LOOP = 1
    MAP = 2

    def __str__(self) -> str:
        match self:
            case NodeType.NODE:
                return "N"
            case NodeType.LOOP:
                return "L"
            case NodeType.MAP:
                return "M"
            case _:
                assert_never(self)

    @staticmethod
    def from_str(node_type: str) -> "NodeType":
        match node_type:
            case "N":
                return NodeType.NODE
            case "L":
                return NodeType.LOOP
            case "M":
                return NodeType.MAP
            case _:
                raise TierkreisError("Unknown node type.")


class NodeStep(BaseModel):
    node_type: NodeType
    idx: int

    def __str__(self) -> str:
        return f"{self.node_type}{self.idx}"

    @staticmethod
    def from_str(frame: str) -> "NodeStep":
        try:
            c, idx = frame[0], int(frame[1:])
            return NodeStep(node_type=NodeType.from_str(c), idx=idx)
        except (IndexError, ValueError) as exc:
            raise TierkreisError(f"Invalid NodeStep {frame}") from exc


class Loc(BaseModel):
    location: list[NodeStep] = []

    def N(self, idx: int) -> "Loc":
        return Loc(
            location=[x for x in self.location]
            + [NodeStep(node_type=NodeType.NODE, idx=idx)]
        )

    def L(self, idx: int) -> "Loc":
        return Loc(
            location=[x for x in self.location]
            + [NodeStep(node_type=NodeType.LOOP, idx=idx)]
        )

    def M(self, idx: int) -> "Loc":
        return Loc(
            location=[x for x in self.location]
            + [NodeStep(node_type=NodeType.MAP, idx=idx)]
        )

    def parent(self) -> "Loc | None":
        if not self.location:
            return None
        return Loc(location=self.location[:-1])

    def __str__(self) -> str:
        frame_strs = [str(x) for x in self.location]
        return ".".join(frame_strs)

    @staticmethod
    def from_str(location: str) -> "Loc":
        if not location:
            return Loc(location=[])
        frames = location.split(".")
        return Loc(location=[NodeStep.from_str(x) for x in frames])


OutputLocation = tuple[Loc, PortID]


@dataclass
class NodeRunData:
    node_location: Loc
    node: NodeDef
    inputs: dict[PortID, OutputLocation]
    output_list: list[PortID]
