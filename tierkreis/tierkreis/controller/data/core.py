from typing import NamedTuple, Protocol, SupportsIndex, runtime_checkable


PortID = str
NodeIndex = int
ValueRef = tuple[NodeIndex, PortID]


class EmptyModel(NamedTuple): ...


@runtime_checkable
class RestrictedNamedTuple[T](Protocol):
    """A NamedTuple whose members are restricted to being of type T."""

    def _asdict(self) -> dict[str, T]: ...
    def __getitem__(self, key: SupportsIndex, /) -> T: ...
