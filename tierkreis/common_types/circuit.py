from __future__ import annotations

import json
from dataclasses import dataclass
from typing import (
    TYPE_CHECKING,
    Any,
    Iterable,
    List,
    Tuple,
    Union,
    cast,
)

if TYPE_CHECKING:
    from pytket._tket.circuit import Circuit as PytketCircuit
    from pytket.circuit import Node


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


@dataclass(frozen=True)
class Circuit:
    circuit_json_str: str

    @classmethod
    def from_pytket_circuit(cls, circuit: PytketCircuit) -> Circuit:
        """Construct a Circuit from a pytket Circuit."""
        return Circuit(json.dumps(circuit.to_dict()))

    def to_pytket_circuit(self) -> PytketCircuit:
        """Construct a pytket Circuit from a Circuit."""
        try:
            from pytket._tket.circuit import Circuit as PytketCircuit
        except ImportError as err:
            raise PytketDependencyError from err
        return PytketCircuit.from_dict(json.loads(self.circuit_json_str))
