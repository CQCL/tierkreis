from typing import Any, NamedTuple


Jsonable = Any
PortID = str
NodeIndex = int
ValueRef = tuple[NodeIndex, PortID]
TKR = bytes | bool | str | int | float | list["TKR"] | dict[str, "TKR"]


class TypedValueRef[T](NamedTuple):
    node_index: NodeIndex
    port: PortID


TKRRef = (
    TypedValueRef[bytes]
    | TypedValueRef[bool]
    | TypedValueRef[str]
    | TypedValueRef[int]
    | TypedValueRef[float]
    | list["TKRRef"]
    | dict[str, "TKRRef"]
)
