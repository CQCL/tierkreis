"""Common compound type aliases."""

from collections import Counter
from dataclasses import dataclass
from importlib import import_module
from typing import TYPE_CHECKING, Any, Dict, Tuple

from .circuit import CircuitWrapper, UnitID

if TYPE_CHECKING:
    from pytket.backends.backendresult import BackendResult

    # use obscure names for following imports to make linting happy
    from pytket.partition import MeasurementBitMap as _PMBP
    from pytket.partition import MeasurementSetup as _PMS
    from pytket.pauli import QubitPauliString as PytketQubitPauliString

Distribution = Dict[str, float]


def _try_pytket_import(mod: str, obj: str) -> Any:
    try:
        module = import_module(mod)
        loaded = getattr(module, obj)
    except ModuleNotFoundError as e:
        raise ImportError("This function requires pytket installed.") from e

    return loaded


QubitPauliString = list[tuple[UnitID, str]]


def _qps_to_pytket(qps: QubitPauliString) -> "PytketQubitPauliString":
    PytketQubitPauliString = _try_pytket_import("pytket.pauli", "QubitPauliString")
    # Pauli = _try_pytket_import("pytket.pauli", "Pauli")
    # Qubit = _try_pytket_import("pytket.circuit", "Qubit")
    if not qps:
        return PytketQubitPauliString()
    return PytketQubitPauliString.from_list(
        [[uid.to_serializable(), pauli] for uid, pauli in qps]
    )


def _qps_from_pytket(tkqps: "PytketQubitPauliString") -> QubitPauliString:
    lst = tkqps.to_list()
    if not lst:
        return []
    return [(UnitID.from_serializable(qb), pauli) for qb, pauli in lst]


@dataclass(frozen=True)
class MeasurementBitMap:
    circ_index: int
    bits: list[int]
    invert: bool

    def to_pytket(self) -> "_PMBP":
        PytketMeasurementBitMap = _try_pytket_import(
            "pytket.partition", "MeasurementBitMap"
        )
        return PytketMeasurementBitMap(self.circ_index, self.bits, self.invert)

    @classmethod
    def from_pytket(cls, py_map: "_PMBP") -> "MeasurementBitMap":
        return cls(py_map.circ_index, py_map.bits, py_map.invert)


@dataclass(frozen=True)
class MeasurementSetup:
    measurement_circs: list[CircuitWrapper]  # using the wrapper to avoid pytket import
    results: list[tuple[QubitPauliString, list[MeasurementBitMap]]]

    def to_pytket(self) -> "_PMS":
        PytketMeasurementSetup = _try_pytket_import(
            "pytket.partition", "MeasurementSetup"
        )
        ms = PytketMeasurementSetup()
        for circ in self.measurement_circs:
            ms.add_measurement_circuit(circ.from_tierkreis_compatible())
        for qps, mbms in self.results:
            tkqps = _qps_to_pytket(qps)
            for mbm in mbms:
                ms.add_result_for_term(tkqps, mbm.to_pytket())

        return ms

    @classmethod
    def from_pytket(cls, py_map: "_PMS") -> "MeasurementSetup":
        return cls(
            [
                CircuitWrapper.new_tierkreis_compatible(c)
                for c in py_map.measurement_circs
            ],
            [
                (
                    _qps_from_pytket(tkqps),
                    [MeasurementBitMap.from_pytket(tkmbm) for tkmbm in tkmbms],
                )
                for tkqps, tkmbms in py_map.results.items()
            ],
        )
