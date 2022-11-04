from __future__ import annotations

import typing
from dataclasses import dataclass
from typing import Generic

import tierkreis.core.protos.tierkreis.v1alpha.graph as pg
from tierkreis.core.tierkreis_struct import TierkreisStruct

if typing.TYPE_CHECKING:
    from tierkreis.core.tierkreis_graph import TierkreisGraph


In = typing.TypeVar("In", bound=TierkreisStruct)
Out = typing.TypeVar("Out", bound=TierkreisStruct)


@dataclass
class RuntimeGraph(Generic[In, Out]):
    "Graph with a `RuntimeStruct` annotation for inputs and outputs."
    graph: TierkreisGraph

    def to_proto(self) -> pg.Value:
        return pg.Value(graph=self.graph.to_proto())
