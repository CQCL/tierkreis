from typing import Literal, NamedTuple, Protocol, SupportsIndex, runtime_checkable


PortID = str
NodeIndex = int
ValueRef = tuple[NodeIndex, PortID]
TKR_DEFAULT = "TKR_DEFAULT"
type TKRDefault = Literal["TKR_DEFAULT"]


class EmptyModel(NamedTuple): ...


@runtime_checkable
class RestrictedNamedTuple[T](Protocol):
    """A NamedTuple whose members are restricted to being of type T."""

    def _asdict(self) -> dict[str, T]: ...
    def __getitem__(self, key: SupportsIndex, /) -> T: ...
