from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from importlib.util import find_spec
from typing import (
    TYPE_CHECKING,
    Any,
    Generic,
    Iterable,
    List,
    Protocol,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
)

from tierkreis.core.opaque_model import OpaqueModel

if TYPE_CHECKING:
    from pytket._tket.circuit import Circuit
    from pytket.backends.backendresult import BackendResult
    from pytket.circuit import Node
    from typing_extensions import Self


_PYTKET = find_spec("pytket") is not None


def _pytket():
    if not _PYTKET:
        raise PytketDependencyError
    import pytket

    return pytket


class PytketDependencyError(Exception):
    """Exception for pytket import error"""

    def __init__(
        self,
        msg="pytket is not installed. "
        "Install optional feature tierkreis['common_types']",
        *args,
        **kwargs,
    ) -> None:
        super().__init__(msg, *args, **kwargs)


@dataclass(frozen=True)
class UnitID:
    """Used for BackendResult.{qubits, bits} and also for Node.
    Not serializable on its own. Returns / takes a list."""

    reg_name: str
    index: List[int]

    def to_serializable(self) -> Tuple[str, List[int]]:
        return self.reg_name, self.index

    @classmethod
    def from_serializable(cls, jsonable: Iterable[Union[str, List[int]]]) -> "UnitID":
        reg_name, index = jsonable
        return UnitID(reg_name=cast(str, reg_name), index=cast(List[int], index))

    @classmethod
    def from_pytket_node(cls, node: Node) -> "UnitID":
        """Convert a pytket Node object to a UnitID object."""
        return UnitID.from_serializable(node.to_list())

    def to_pytket_node(self) -> Node:
        """Convert a UnitID object to a pytket Node object."""
        _pytket().circuit.Node  # type: ignore

        return Node.from_list(list(self.to_serializable()))

    def __hash__(self) -> int:
        return hash(str(self))

    def __eq__(self, other: Any) -> bool:
        return str(self) == str(other)


class PytketType(Protocol):
    """Many pytket types define to_dict and from_dict for serialization."""

    def to_dict(self) -> dict[str, Any]:
        ...

    @classmethod
    def from_dict(cls, d: dict[str, Any], /) -> "PytketType":
        ...


T = TypeVar("T", bound=PytketType)


class PytketWrapper(OpaqueModel, ABC, Generic[T]):
    json_str: str

    @classmethod
    @abstractmethod
    def get_pytket_type(cls) -> Type[T]:
        raise NotImplementedError

    @classmethod
    def new_tierkreis_compatible(cls, value: T) -> Self:
        return cls(json_str=json.dumps(value.to_dict()))

    def from_tierkreis_compatible(self) -> T:
        return self.get_pytket_type().from_dict(json.loads(self.json_str))  # type: ignore


class CircuitWrapper(PytketWrapper["Circuit"]):
    @classmethod
    def get_pytket_type(cls) -> Type["Circuit"]:
        return _pytket().circuit.Circuit  # type: ignore


class ResultWrapper(PytketWrapper["BackendResult"]):
    @classmethod
    def get_pytket_type(cls) -> Type["BackendResult"]:
        return _pytket().backends.backendresult.BackendResult  # type: ignore


def register_pytket_types():
    """Register conversions for pytket types with Tierkreis."""
    if _PYTKET:
        from pytket._tket.circuit import Circuit
        from pytket.backends.backendresult import BackendResult

        from tierkreis.core.types import TierkreisType

        TierkreisType.register_alternative(Circuit, CircuitWrapper)
        TierkreisType.register_alternative(BackendResult, ResultWrapper)
    else:
        raise PytketDependencyError
