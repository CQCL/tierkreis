from abc import ABC
from dataclasses import dataclass
from typing import Generic
import typing

if typing.TYPE_CHECKING:
    import tierkreis.core.values

class RuntimeStruct(ABC):
    "Abstract base class for classes that should encode structs at runtime."
    pass

In = typing.TypeVar("In", bound=RuntimeStruct)
Out = typing.TypeVar("Out", bound=RuntimeStruct)

@dataclass
class RuntimeGraph(Generic[In, Out]):
    "Graph with a `RuntimeStruct` annotation for inputs and outputs."
    graph: "tierkreis.core.values.Graph"

