from typing import Any, NamedTuple


Jsonable = Any
PortID = str
NodeIndex = int
ValueRef = tuple[NodeIndex, PortID]


class EmptyModel(NamedTuple): ...
