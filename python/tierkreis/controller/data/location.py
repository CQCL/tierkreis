from dataclasses import dataclass
from enum import Enum
from logging import getLogger
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, GetCoreSchemaHandler, model_validator
from pydantic_core import CoreSchema, core_schema
from typing_extensions import assert_never

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


class Loc(str):
    def __new__(cls, k: str = "-") -> "Loc":
        return super(Loc, cls).__new__(cls, k)

    def N(self, idx: int) -> "Loc":
        return Loc(str(self) + f".N{idx}")

    def L(self, idx: int) -> "Loc":
        return Loc(str(self) + f".L{idx}")

    def M(self, idx: int) -> "Loc":
        return Loc(str(self) + f".M{idx}")

    def parent(self) -> "Loc | None":
        if not self:
            return None
        return Loc(".".join(self.split(".")[:-1]))

    def __hash__(self) -> int:
        return hash(str(self))

    def __add__(self, other: str) -> "Loc":
        return Loc(str(self) + other[1:])

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        return core_schema.no_info_after_validator_function(cls, handler(str))


OutputLoc = tuple[Loc, PortID]
