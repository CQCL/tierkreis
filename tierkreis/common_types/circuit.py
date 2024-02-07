from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
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

from pydantic import field_validator

from tierkreis.core.opaque_model import OpaqueModel

if TYPE_CHECKING:
    from pytket._tket.circuit import Circuit as PytketCircuit
    from pytket.backends.backendresult import BackendResult as PytketResult
    from pytket.circuit import Node
    from typing_extensions import Self


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
        try:
            from pytket.circuit import Node
        except ImportError as err:
            raise PytketDependencyError from err

        return Node.from_list(list(self.to_serializable()))

    def __hash__(self) -> int:
        return hash(str(self))

    def __eq__(self, other: Any) -> bool:
        return str(self) == str(other)


class PytketType(Protocol):
    def to_dict(self) -> dict[str, Any]:
        ...

    @classmethod
    def from_dict(cls, d: dict[str, Any], /) -> "PytketType":
        ...


T = TypeVar("T", bound=PytketType)


class PytketWrapper(OpaqueModel, ABC, Generic[T]):
    json_str: str

    @field_validator("json_str")
    @classmethod
    def validate_inner(cls, raw: str) -> str:
        """Validate a pytket type."""
        PytketType = cls.get_pytket_type()
        PytketType.from_dict(json.loads(raw))
        return raw

    @classmethod
    @abstractmethod
    def get_pytket_type(cls) -> Type[T]:
        raise NotImplementedError

    @classmethod
    def from_pytket_value(cls, pytket_val: T) -> Self:
        """Construct a Circuit from a pytket Circuit."""
        return cls(json_str=json.dumps(pytket_val.to_dict()))

    def to_pytket_value(self) -> T:
        """Construct a pytket Circuit from a Circuit."""
        PytketType = self.get_pytket_type()
        return PytketType.from_dict(json.loads(self.json_str))


class Circuit(PytketWrapper["PytketCircuit"]):
    @classmethod
    def get_pytket_type(cls) -> Type["PytketCircuit"]:
        try:
            from pytket._tket.circuit import Circuit as PytketCircuit
        except ImportError as err:
            raise PytketDependencyError from err
        return PytketCircuit


class BackendResult(PytketWrapper["PytketResult"]):
    @classmethod
    def get_pytket_type(cls) -> Type["PytketResult"]:
        try:
            from pytket.backends.backendresult import BackendResult as PytketResult
        except ImportError as err:
            raise PytketDependencyError from err
        return PytketResult
