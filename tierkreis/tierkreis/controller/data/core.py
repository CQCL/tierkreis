from typing import NamedTuple


PortID = str
NodeIndex = int
ValueRef = tuple[NodeIndex, PortID]


class EmptyModel(NamedTuple): ...
