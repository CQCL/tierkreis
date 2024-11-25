from __future__ import annotations

import typing
from dataclasses import dataclass
from typing import Generic

import tierkreis.core.protos.tierkreis.v1alpha1.graph as pg
from tierkreis.core.types import UnpackRow

if typing.TYPE_CHECKING:
    from tierkreis.core.tierkreis_graph import TierkreisGraph


In = typing.TypeVar("In", bound=UnpackRow)
Out = typing.TypeVar("Out", bound=UnpackRow)


@dataclass
class RuntimeGraph(Generic[In, Out]):
    "Graph with a `RuntimeStruct` annotation for inputs and outputs."

    graph: TierkreisGraph

    def to_proto(self) -> pg.Value:
        return pg.Value(graph=self.graph.to_proto())
