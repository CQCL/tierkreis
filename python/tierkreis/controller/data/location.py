from dataclasses import dataclass
from enum import Enum
from logging import getLogger
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel
from typing_extensions import assert_never

from tierkreis.controller.data.graph import NodeDef, NodeIndex
from tierkreis.core.tierkreis_graph import PortID
from tierkreis.exceptions import TierkreisError

logger = getLogger(__name__)


class WorkerCallArgs(BaseModel):
    function_name: str
    inputs: dict[str, Path]
    outputs: dict[str, Path]
    done_path: Path
    logs_path: Optional[Path]


NodeType = Literal["N", "L", "M"]
NodeStep = Literal["-"] | tuple[NodeType, NodeIndex]


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

        step_strs = self.split(".")
        last_step_str = step_strs.pop()
        loc = Loc(".".join(step_strs))
        if not last_step_str.startswith("L"):
            return loc

        idx = int(last_step_str[1:])
        if idx == 0:
            return loc

        return loc.L(idx - 1)


OutputLoc = tuple[Loc, PortID]


@dataclass
class NodeRunData:
    node_location: Loc
    node: NodeDef
    output_list: list[PortID]
