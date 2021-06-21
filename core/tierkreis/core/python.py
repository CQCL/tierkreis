from __future__ import annotations
from abc import ABC
from dataclasses import dataclass
from typing import Generic
import typing

from tierkreis.core.tierkreis_struct import TierkreisStruct
if typing.TYPE_CHECKING:
    from tierkreis.core.tierkreis_graph import TierkreisGraph



In = typing.TypeVar("In", bound=TierkreisStruct)
Out = typing.TypeVar("Out", bound=TierkreisStruct)


@dataclass
class RuntimeGraph(Generic[In, Out]):
    "Graph with a `RuntimeStruct` annotation for inputs and outputs."
    graph: TierkreisGraph
