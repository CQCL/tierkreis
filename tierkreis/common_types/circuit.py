from __future__ import annotations

from abc import ABC
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, Union
from uuid import UUID

if TYPE_CHECKING:
    # pylint: disable=E0611
    from pytket.circuit import Circuit as PytketCircuit
    from pytket.circuit import Node  # type: ignore

# pylint: disable=redefined-builtin


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


class Serializable(ABC):
    def to_serializable(self) -> Any:
        pass


@dataclass(frozen=True)
class UnitID(Serializable):
    """Used for BackendResult.{qubits, bits} and also for Node.
    Not serializable on its own. Returns / takes a list."""

    reg_name: str
    index: List[int]

    def to_serializable(self) -> Tuple[str, List[int]]:
        return self.reg_name, self.index

    @classmethod
    def from_serializable(cls, jsonable: Tuple[str, List[int]]) -> "UnitID":
        reg_name = jsonable[0]
        index = jsonable[1]
        return UnitID(reg_name=reg_name, index=index)

    @classmethod
    def from_pytket_node(cls, node: Node) -> "UnitID":
        """Convert a pytket Node object to a UnitID object."""
        return UnitID.from_serializable(node.to_list())

    def to_pytket_node(self) -> Node:
        """Convert a UnitID object to a pytket Node object."""
        try:
            # pylint: disable=E0611
            from pytket.circuit import Node  # type: ignore
        except ImportError as err:
            raise PytketDependencyError from err

        return Node.from_list(list(self.to_serializable()))

    def __hash__(self) -> int:
        return hash(str(self))

    def __eq__(self, other: Any) -> bool:
        return str(self) == str(other)


@dataclass(frozen=True)
class BitRegister:
    """A series of Registers with the same name"""

    name: str
    size: int

    def to_serializable(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "size": self.size,
        }

    @classmethod
    def from_serializable(cls, jsonable: Dict[str, Any]) -> "BitRegister":
        return BitRegister(name=jsonable["name"], size=jsonable["size"])


@dataclass(frozen=True)
class ComplexNumber:
    """Used in various matrices."""

    real: float
    imag: float

    def to_serializable(self) -> Tuple[float, float]:
        return self.real, self.imag

    @classmethod
    def from_serializable(cls, jsonable: Tuple[float, float]) -> "ComplexNumber":
        return ComplexNumber(real=jsonable[0], imag=jsonable[1])


@dataclass(frozen=True)
class Permutation:
    """Used in Circuit.implicit_permutation."""

    x: UnitID
    y: UnitID

    def to_serializable(self) -> Tuple[Tuple[str, List[int]], Tuple[str, List[int]]]:
        return self.x.to_serializable(), self.y.to_serializable()

    @classmethod
    def from_serializable(
        cls, jsonable: Tuple[Tuple[str, List[int]], Tuple[str, List[int]]]
    ) -> "Permutation":
        register_x = UnitID.from_serializable(jsonable[0])
        register_y = UnitID.from_serializable(jsonable[1])
        return Permutation(x=register_x, y=register_y)


@dataclass(frozen=True)
class CircBox(Serializable):
    id: UUID
    circuit: "Circuit"

    def to_serializable(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "circuit": self.circuit.to_serializable(),
            "type": "CircBox",
        }

    @classmethod
    def from_serializable(cls, jsonable: Dict[str, Any]) -> "CircBox":
        assert jsonable["type"] == "CircBox"
        id = jsonable["id"]
        circuit = Circuit.from_serializable(jsonable["circuit"])
        return CircBox(
            id=id,
            circuit=circuit,
        )


@dataclass(frozen=True)
class Unitary1qBox(Serializable):
    id: UUID
    matrix: List[List[ComplexNumber]]  # 2 x 2 unitary matrix of complex numbers.

    def to_serializable(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "matrix": [
                [entry.to_serializable() for entry in row] for row in self.matrix
            ],
            "type": "Unitary1qBox",
        }

    @classmethod
    def from_serializable(cls, jsonable: Dict[str, Any]) -> "Unitary1qBox":
        assert jsonable["type"] == "Unitary1qBox"
        id = jsonable["id"]
        matrix = [
            [ComplexNumber.from_serializable(entry) for entry in row]
            for row in jsonable["matrix"]
        ]
        return Unitary1qBox(
            id=id,
            matrix=matrix,
        )


@dataclass(frozen=True)
class Unitary2qBox(Serializable):
    id: UUID
    matrix: List[List[ComplexNumber]]  # 4 x 4 unitary matrix of complex numbers.

    def to_serializable(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "matrix": [
                [entry.to_serializable() for entry in row] for row in self.matrix
            ],
            "type": "Unitary2qBox",
        }

    @classmethod
    def from_serializable(cls, jsonable: Dict[str, Any]) -> "Unitary2qBox":
        assert jsonable["type"] == "Unitary2qBox"
        id = jsonable["id"]
        matrix = [
            [ComplexNumber.from_serializable(entry) for entry in row]
            for row in jsonable["matrix"]
        ]
        return Unitary2qBox(
            id=id,
            matrix=matrix,
        )


@dataclass(frozen=True)
class ExpBox(Serializable):
    id: UUID
    matrix: List[List[ComplexNumber]]  # 2 x 2 hermitian matrix of complex numbers.
    phase: float

    def to_serializable(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "matrix": [
                [entry.to_serializable() for entry in row] for row in self.matrix
            ],
            "phase": self.phase,
            "type": "ExpBox",
        }

    @classmethod
    def from_serializable(cls, jsonable: Dict[str, Any]) -> "ExpBox":
        assert jsonable["type"] == "ExpBox"
        id = jsonable["id"]
        matrix = [
            [ComplexNumber.from_serializable(entry) for entry in row]
            for row in jsonable["matrix"]
        ]
        phase = jsonable["phase"]
        return ExpBox(
            id=id,
            matrix=matrix,
            phase=phase,
        )


@dataclass(frozen=True)
class PauliExpBox(Serializable):
    id: UUID
    paulis: List[str]
    phase: str  # symengine Expr

    def to_serializable(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "paulis": self.paulis,
            "phase": self.phase,
            "type": "PauliExpBox",
        }

    @classmethod
    def from_serializable(cls, jsonable: Dict[str, Any]) -> "PauliExpBox":
        assert jsonable["type"] == "PauliExpBox"
        id = jsonable["id"]
        paulis = jsonable["paulis"]
        phase = jsonable["phase"]
        return PauliExpBox(
            id=id,
            paulis=paulis,
            phase=phase,
        )


@dataclass(frozen=True)
class PhasePolyBox(Serializable):
    id: UUID
    n_qubits: int
    qubit_indices: Dict[UnitID, int]  # map from qubit register to polynomial index
    phase_polynomial: Dict[Tuple[bool, ...], float]  # map from bitstring to phase
    linear_transformation: List[List[bool]]  # boolean matrix

    def to_serializable(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "n_qubits": self.n_qubits,
            "qubit_indices": [
                [register.to_serializable(), index]
                for register, index in self.qubit_indices.items()
            ],
            "phase_polynomial": [
                [list(bitstring), phase]
                for bitstring, phase in self.phase_polynomial.items()
            ],
            "linear_transformation": self.linear_transformation,
            "type": "PhasePolyBox",
        }

    @classmethod
    def from_serializable(cls, jsonable: Dict[str, Any]) -> "PhasePolyBox":
        assert jsonable["type"] == "PhasePolyBox"
        id = jsonable["id"]
        n_qubits = jsonable["n_qubits"]
        linear_transformation = jsonable["linear_transformation"]
        qubit_indices = {
            UnitID.from_serializable(map_elem[0]): map_elem[1]
            for map_elem in jsonable["qubit_indices"]
        }
        phase_polynomial = {
            tuple(map(bool, map_elem[0])): float(map_elem[1])
            for map_elem in jsonable["phase_polynomial"]
        }
        return PhasePolyBox(
            id=id,
            n_qubits=n_qubits,
            qubit_indices=qubit_indices,
            phase_polynomial=phase_polynomial,
            linear_transformation=linear_transformation,
        )


@dataclass(frozen=True)
class CompositeGate(Serializable):
    args: List[str]
    definition: "Circuit"
    name: str

    def to_serializable(self) -> Dict[str, Any]:
        return {
            "args": self.args,
            "definition": self.definition.to_serializable(),
            "name": self.name,
        }

    @classmethod
    def from_serializable(cls, jsonable: Dict[str, Any]) -> "CompositeGate":
        args = jsonable["args"]
        definition = Circuit.from_serializable(jsonable["definition"])
        name = jsonable["name"]
        return CompositeGate(
            args=args,
            definition=definition,
            name=name,
        )


@dataclass(frozen=True)
class Composite(Serializable):
    id: UUID
    gate: CompositeGate
    params: List[str]

    def to_serializable(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "gate": self.gate.to_serializable(),
            "params": self.params,
            "type": "Composite",
        }

    @classmethod
    def from_serializable(cls, jsonable: Dict[str, Any]) -> "Composite":
        assert jsonable["type"] == "Composite"
        id = jsonable["id"]
        gate = CompositeGate.from_serializable(jsonable["gate"])
        params = jsonable["params"]
        return Composite(
            id=id,
            gate=gate,
            params=params,
        )


@dataclass(frozen=True)
class QControlBox(Serializable):
    id: UUID
    n_controls: int
    op: "Operation"

    def to_serializable(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "n_controls": self.n_controls,
            "op": self.op.to_serializable(),
            "type": "QControlBox",
        }

    @classmethod
    def from_serializable(cls, jsonable: Dict[str, Any]) -> "QControlBox":
        assert jsonable["type"] == "QControlBox"
        id = jsonable["id"]
        n_controls = jsonable["n_controls"]
        op = Operation.from_serializable(jsonable["op"])
        return QControlBox(
            id=id,
            n_controls=n_controls,
            op=op,
        )


@dataclass(frozen=True)
class ClassicalExp(Serializable):
    args: List[Union[int, UnitID, BitRegister, "ClassicalExp"]]
    op: str

    def to_formatted_string(self) -> str:
        f_args = [
            (
                str(arg)
                if isinstance(arg, int)
                else f"{arg.reg_name}{str(arg.index)}"
                if isinstance(arg, UnitID)
                else f"{arg.name}{str(range(arg.size))}"
                if isinstance(arg, BitRegister)
                else arg.to_formatted_string()  # nested expression
            )
            for arg in self.args
        ]

        op = self.op.split(".")
        if len(op) > 1:
            operation = op[1]
        else:
            operation = op[0]

        n = len(f_args)
        # Display the operation differently based on the number of arguments
        # This is so we can write binary operations infix,
        # and omit the brackets for unary or constant operations
        if n == 0:
            return operation  # -> op
        elif n == 1:
            return f"{operation} {f_args[0]}"  # -> op exp
        elif n == 2:
            return f"({f_args[0]} {operation} {f_args[1]})"  # -> (exp op exp)
        else:
            return f"{operation}({str(f_args)})"  # -> op(exp, ... exp)

    def to_serializable(self) -> Dict[str, Any]:
        return {
            "args": [
                arg if isinstance(arg, int) else arg.to_serializable()
                for arg in self.args
            ],
            "op": self.op,
        }

    @classmethod
    def from_serializable(cls, jsonable: Dict[str, Any]) -> "ClassicalExp":
        args: List[Union[int, UnitID, BitRegister, "ClassicalExp"]] = [
            arg
            if isinstance(arg, int)
            else UnitID.from_serializable(arg)  # type:ignore
            if isinstance(arg, (tuple, list))
            else BitRegister.from_serializable(arg)
            if isinstance(arg, dict) and "name" in arg and "size" in arg
            else ClassicalExp.from_serializable(arg)
            for arg in jsonable["args"]
        ]
        op = jsonable["op"]
        return ClassicalExp(
            args=args,
            op=op,
        )


@dataclass(frozen=True)
class ClassicalExpBox(Serializable):
    id: UUID
    n_i: int
    n_io: int
    n_o: int
    exp: ClassicalExp

    def to_serializable(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "n_i": self.n_i,
            "n_io": self.n_io,
            "n_o": self.n_o,
            "exp": self.exp.to_serializable(),
            "type": "ClassicalExpBox",
        }

    @classmethod
    def from_serializable(cls, jsonable: Dict[str, Any]) -> "ClassicalExpBox":
        assert jsonable["type"] == "ClassicalExpBox"
        id = jsonable["id"]
        n_i = jsonable["n_i"]
        n_io = jsonable["n_io"]
        n_o = jsonable["n_o"]
        exp = ClassicalExp.from_serializable(jsonable["exp"])
        return ClassicalExpBox(
            id=id,
            n_i=n_i,
            n_io=n_io,
            n_o=n_o,
            exp=exp,
        )


Box = Union[
    CircBox,
    Unitary1qBox,
    Unitary2qBox,
    ExpBox,
    PauliExpBox,
    PhasePolyBox,
    Composite,
    QControlBox,
    ClassicalExpBox,
]
box_name_to_class: Dict[str, Box] = {box_type.__name__: box_type for box_type in Box.__args__}  # type: ignore


def deserialize_box(jsonable: Dict[str, Any]) -> Box:
    """Deserialize something that should be a Box based on a tag."""
    box_type = jsonable["type"]
    if box_type in box_name_to_class.keys():
        box_class = box_name_to_class[box_type]
        return box_class.from_serializable(jsonable)
    raise ValueError(
        f"Cannot deserialize as {box_type}, no known class matches that tag."
    )


@dataclass(frozen=True)
class Conditional(Serializable):
    """Used in Operation.
    Defines gate operation conditionally on classical registers."""

    op: "Operation"
    width: int
    value: int

    def to_serializable(self) -> Dict[str, Any]:
        return {
            "op": self.op.to_serializable(),
            "width": self.width,
            "value": self.value,
        }

    @classmethod
    def from_serializable(cls, jsonable: Dict[str, Any]) -> "Conditional":
        op = Operation.from_serializable(jsonable["op"])
        width = jsonable["width"]
        value = jsonable["value"]
        return Conditional(
            op=op,
            width=width,
            value=value,
        )


@dataclass(frozen=True)
class GenericClassical(Serializable):
    n_i: Optional[int]
    n_io: Optional[int]
    name: Optional[str]
    values: Optional[Union[List[int], List[bool]]]
    upper: Optional[int]
    lower: Optional[int]

    def to_serializable(self) -> Dict[str, Any]:
        jsonable: Dict[str, Any] = {}

        if self.n_i is not None:
            jsonable["n_i"] = self.n_i

        if self.n_io is not None:
            jsonable["n_io"] = self.n_io

        if self.name is not None:
            jsonable["name"] = self.name

        if self.values is not None:
            jsonable["values"] = self.values

        if self.upper is not None:
            jsonable["upper"] = self.upper

        if self.lower is not None:
            jsonable["lower"] = self.lower

        return jsonable

    @classmethod
    def from_serializable(cls, jsonable: Dict[str, Any]) -> "GenericClassical":
        n_i = jsonable.get("n_i")
        n_io = jsonable.get("n_io")
        name = jsonable.get("name")
        values = jsonable.get("values")
        upper = jsonable.get("upper")
        lower = jsonable.get("lower")
        return GenericClassical(
            n_i=n_i,
            n_io=n_io,
            name=name,
            values=values,
            upper=upper,
            lower=lower,
        )


@dataclass(frozen=True)
class MultiBit(Serializable):
    n: int
    op: "Operation"  # The classical operation to apply multiple times

    def to_serializable(self) -> Dict[str, Any]:
        return {
            "n": self.n,
            "op": self.op.to_serializable(),
        }

    @classmethod
    def from_serializable(cls, jsonable: Dict[str, Any]) -> "MultiBit":
        n = jsonable["n"]
        op = Operation.from_serializable(jsonable["op"])
        assert op.op_type in generic_classical_types + ["MultiBit"]
        return MultiBit(
            n=n,
            op=op,
        )


Classical = Union[
    GenericClassical,
    MultiBit,
]
generic_classical_types = [
    "ClassicalTransform",
    "SetBits",
    "CopyBits",
    "RangePredicate",
    "ExplicitPredicate",
    "ExplicitModifier",
]
classical_name_to_class: Dict[str, Classical] = {
    **{
        class_name: GenericClassical  # type:ignore
        for class_name in generic_classical_types
    },
    **{"MultiBit": MultiBit},  # type:ignore
}


def deserialize_classical(box_type: str, jsonable: Dict[str, Any]) -> Classical:
    """Deserialize something that should be a Classical based on the box type."""
    if box_type in classical_name_to_class.keys():
        classical_class = classical_name_to_class[box_type]
        return classical_class.from_serializable(jsonable)
    raise ValueError(
        f"Cannot deserialize {box_type} as a classical box, "
        "no known classical class matches that tag."
    )


@dataclass(frozen=True)
class Operation(Serializable):
    """Used in Command."""

    op_type: str  # Should be from the OpType enum, but a string for now.
    n_qb: Optional[int] = None  # Number of qubits
    params: Optional[List[str]] = None  # A list of angles.
    box: Optional[Box] = None
    signature: Optional[List[str]] = None  # Required if op_type is "Barrier".
    conditional: Optional[Conditional] = None  # Required if op_type is "Condition".
    classical: Optional[Classical] = None  # Required if this is a classical operation.

    def to_serializable(self) -> Dict[str, Any]:
        jsonable: Dict[str, Any] = {
            "type": self.op_type,
        }

        if self.n_qb is not None:
            jsonable["n_qb"] = self.n_qb

        if self.params is not None:
            jsonable["params"] = self.params

        if self.box is not None:
            jsonable["box"] = self.box.to_serializable()

        if self.signature is not None:
            jsonable["signature"] = self.signature

        if self.conditional is not None:
            jsonable["conditional"] = self.conditional.to_serializable()

        if self.classical is not None:
            jsonable["classical"] = self.classical.to_serializable()

        return jsonable

    @classmethod
    def from_serializable(cls, jsonable: Dict[str, Any]) -> "Operation":
        op_type = jsonable["type"]
        n_qb = jsonable.get("n_qb")
        params = jsonable.get("params")

        box = jsonable.get("box")
        if box is not None:
            box = deserialize_box(box)

        signature = jsonable.get("signature")

        conditional = jsonable.get("conditional")
        if conditional is not None:
            conditional = Conditional.from_serializable(conditional)

        classical = jsonable.get("classical")
        if classical is not None:
            classical = deserialize_classical(op_type, classical)

        return Operation(
            op_type=op_type,
            n_qb=n_qb,
            params=params,
            box=box,
            signature=signature,
            conditional=conditional,
            classical=classical,
        )


@dataclass(frozen=True)
class Command(Serializable):
    """Used in Circuit."""

    op: Operation
    args: List[UnitID]  # The qubits and/or classical bits this command affects.
    opgroup: Optional[str]

    def to_serializable(self) -> Dict[str, Any]:
        jsonable: Dict[str, Any] = {
            "op": self.op.to_serializable(),
            "args": [arg.to_serializable() for arg in self.args],
        }

        if self.opgroup is not None:
            jsonable["opgroup"] = self.opgroup

        return jsonable

    @classmethod
    def from_serializable(cls, jsonable: Dict[str, Any]) -> "Command":
        op = Operation.from_serializable(jsonable["op"])
        args = [UnitID.from_serializable(arg) for arg in jsonable["args"]]
        opgroup = jsonable.get("opgroup")
        return Command(op=op, args=args, opgroup=opgroup)


@dataclass(frozen=True)
class Circuit(Serializable):
    """Dataclass encapsulation of a pytket Circuit.
    https://github.com/CQCL/tket/blob/develop/schemas/circuit_v1.json
    """

    name: Optional[str]
    phase: str
    qubits: List[UnitID]
    bits: List[UnitID]
    commands: List[Command]
    implicit_permutation: List[Permutation]

    def to_serializable(self) -> Dict[str, Any]:
        jsonable = {
            "phase": self.phase,
            "qubits": [q.to_serializable() for q in self.qubits],
            "bits": [b.to_serializable() for b in self.bits],
            "commands": [cmd.to_serializable() for cmd in self.commands],
            "implicit_permutation": [
                p.to_serializable() for p in self.implicit_permutation
            ],
        }

        if self.name is not None:
            jsonable["name"] = self.name

        return jsonable

    @classmethod
    def from_serializable(cls, jsonable: Dict[str, Any]) -> "Circuit":
        name = jsonable.get("name")
        phase = jsonable["phase"]
        qubits = [UnitID.from_serializable(q) for q in jsonable["qubits"]]
        bits = [UnitID.from_serializable(b) for b in jsonable["bits"]]
        commands = [Command.from_serializable(cmd) for cmd in jsonable["commands"]]
        implicit_permutation = [
            Permutation.from_serializable(p) for p in jsonable["implicit_permutation"]
        ]
        return Circuit(
            name=name,
            phase=phase,
            qubits=qubits,
            bits=bits,
            commands=commands,
            implicit_permutation=implicit_permutation,
        )

    @classmethod
    def from_pytket_circuit(cls, circuit: PytketCircuit) -> Circuit:
        """Construct a Circuit from a pytket Circuit."""
        return Circuit.from_serializable(circuit.to_dict())

    def to_pytket_circuit(self) -> PytketCircuit:
        """Construct a pytket Circuit from a Circuit."""
        try:
            # pylint: disable=E0611
            from pytket.circuit import Circuit as PytketCircuit
        except ImportError as err:
            raise PytketDependencyError from err
        return PytketCircuit.from_dict(self.to_serializable())
