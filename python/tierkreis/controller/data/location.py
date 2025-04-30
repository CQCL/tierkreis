from dataclasses import dataclass
from enum import Enum
from logging import getLogger
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel
from typing_extensions import assert_never

from tierkreis.controller.data.graph import NodeDef, NodeIndex
from tierkreis.core.tierkreis_graph import PortID

logger = getLogger(__name__)


class WorkerCallArgs(BaseModel):
    function_name: str
    inputs: dict[str, Path]
    outputs: dict[str, Path]
    output_dir: Path
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

    @staticmethod
    def from_steps(steps: list[NodeStep]) -> "Loc":
        loc = ""
        for step in steps.copy():
            match step:
                case "-":
                    loc += "-"
                case (node_type, idx):
                    loc += f".{node_type}{idx}"
        return Loc(loc)

    def parent(self) -> "Loc | None":
        if not self.steps:
            return None

        steps = self.steps()
        last_step = steps.pop()
        match last_step:
            case "-":
                return Loc.from_steps([])
            case ("L", 0):
                return Loc.from_steps(steps)
            case ("L", idx):
                return Loc.from_steps(steps).L(idx - 1)
            case ("N", idx) | ("M", idx):
                return Loc.from_steps(steps)
            case _:
                assert_never(last_step)

    def steps(self) -> list[NodeStep]:
        steps = []
        for step_str in self.split("."):
            if step_str == "-":
                steps.append("-")
            else:
                steps.append((step_str[0], int(step_str[1:])))

        return steps


OutputLoc = tuple[Loc, PortID]


@dataclass
class NodeRunData:
    node_location: Loc
    node: NodeDef
    output_list: list[PortID]
