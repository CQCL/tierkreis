"""Code generated from pytket_worker namespace. Please do not edit."""

# ruff: noqa: F821
from typing import NamedTuple, Sequence
from tierkreis.controller.data.models import TKR, OpaqueType


class add_measure_all(NamedTuple):
    circuit: TKR[OpaqueType["pytket._tket.circuit.Circuit"]]

    @staticmethod
    def out() -> type[TKR[OpaqueType["pytket._tket.circuit.Circuit"]]]:
        return TKR[OpaqueType["pytket._tket.circuit.Circuit"]]

    @property
    def namespace(self) -> str:
        return "pytket_worker"


class append_pauli_measurement_impl(NamedTuple):
    circuit: TKR[OpaqueType["pytket._tket.circuit.Circuit"]]
    pauli_string: TKR[OpaqueType["pytket._tket.pauli.QubitPauliString"]]

    @staticmethod
    def out() -> type[TKR[OpaqueType["pytket._tket.circuit.Circuit"]]]:
        return TKR[OpaqueType["pytket._tket.circuit.Circuit"]]

    @property
    def namespace(self) -> str:
        return "pytket_worker"


class optimise_phase_gadgets(NamedTuple):
    circuit: TKR[OpaqueType["pytket._tket.circuit.Circuit"]]

    @staticmethod
    def out() -> type[TKR[OpaqueType["pytket._tket.circuit.Circuit"]]]:
        return TKR[OpaqueType["pytket._tket.circuit.Circuit"]]

    @property
    def namespace(self) -> str:
        return "pytket_worker"


class apply_pass(NamedTuple):
    circuit: TKR[OpaqueType["pytket._tket.circuit.Circuit"]]
    compiler_pass: TKR[OpaqueType["pytket._tket.passes.BasePass"]]

    @staticmethod
    def out() -> type[TKR[OpaqueType["pytket._tket.circuit.Circuit"]]]:
        return TKR[OpaqueType["pytket._tket.circuit.Circuit"]]

    @property
    def namespace(self) -> str:
        return "pytket_worker"


class compile_circuit_quantinuum(NamedTuple):
    circuit: TKR[OpaqueType["pytket._tket.circuit.Circuit"]]

    @staticmethod
    def out() -> type[TKR[OpaqueType["pytket._tket.circuit.Circuit"]]]:
        return TKR[OpaqueType["pytket._tket.circuit.Circuit"]]

    @property
    def namespace(self) -> str:
        return "pytket_worker"


class compile_circuits_quantinuum(NamedTuple):
    circuits: TKR[Sequence[OpaqueType["pytket._tket.circuit.Circuit"]]]

    @staticmethod
    def out() -> type[TKR[Sequence[OpaqueType["pytket._tket.circuit.Circuit"]]]]:
        return TKR[Sequence[OpaqueType["pytket._tket.circuit.Circuit"]]]

    @property
    def namespace(self) -> str:
        return "pytket_worker"


class expectation(NamedTuple):
    backend_result: TKR[OpaqueType["pytket.backends.backendresult.BackendResult"]]

    @staticmethod
    def out() -> type[TKR[float]]:
        return TKR[float]

    @property
    def namespace(self) -> str:
        return "pytket_worker"
