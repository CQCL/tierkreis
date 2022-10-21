# pylint: disable=protected-access
"""Common compound type aliases."""

from collections import Counter
from dataclasses import dataclass
from importlib import import_module
from typing import TYPE_CHECKING, Any, Dict, Tuple

from .circuit import Circuit as CircStruct
from .circuit import UnitID

if TYPE_CHECKING:
    from pytket.backends.backendresult import BackendResult

    # use obscure names for following imports to make isort, black and mypy happy
    from pytket.partition import MeasurementBitMap as _PMBP  # type: ignore
    from pytket.partition import MeasurementSetup as _PMS  # type: ignore
    from pytket.pauli import QubitPauliString as PytketQubitPauliString  # type: ignore

Distribution = Dict[str, float]


def _try_pytket_import(mod: str, obj: str) -> Any:
    try:
        module = import_module(mod)
        loaded = getattr(module, obj)
    except ModuleNotFoundError as e:
        raise ImportError("This function requires pytket installed.") from e

    return loaded


@dataclass(frozen=True)
class SampledDistribution:
    distribution: Distribution
    n_samples: int


def backres_to_sampleddist(backres: "BackendResult") -> SampledDistribution:
    """Convert pytket BackendResult to Tierkreis type."""
    assert backres.contains_measured_results
    if backres._counts is not None:
        total_shots = int(sum(backres._counts.values()))
    else:
        assert backres._shots is not None
        total_shots = len(backres._shots)
    return SampledDistribution(
        {
            "".join(map(str, key)): val
            for key, val in backres.get_distribution().items()
        },
        total_shots,
    )


def _bitstring_to_tuple(bitstr: str) -> Tuple[int, ...]:
    return tuple(map(int, bitstr))


def sampleddist_to_backres(dist: SampledDistribution) -> "BackendResult":
    """Convert Tierkreis type to pytket backend result"""
    BackendResult = _try_pytket_import("pytket.backends.backendresult", "BackendResult")
    OutcomeArray = _try_pytket_import("pytket.utils.outcomearray", "OutcomeArray")

    counts = {
        OutcomeArray.from_readouts([_bitstring_to_tuple(key)]): int(
            val * dist.n_samples
        )
        for key, val in dist.distribution.items()
    }

    return BackendResult(counts=Counter(counts))


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
    measurement_circs: list[CircStruct]
    results: list[tuple[QubitPauliString, list[MeasurementBitMap]]]

    def to_pytket(self) -> "_PMS":
        PytketMeasurementSetup = _try_pytket_import(
            "pytket.partition", "MeasurementSetup"
        )
        ms = PytketMeasurementSetup()
        for circ in self.measurement_circs:
            ms.add_measurement_circuit(circ.to_pytket_circuit())
        for qps, mbms in self.results:
            tkqps = _qps_to_pytket(qps)
            for mbm in mbms:
                ms.add_result_for_term(tkqps, mbm.to_pytket())

        return ms

    @classmethod
    def from_pytket(cls, py_map: "_PMS") -> "MeasurementSetup":
        return cls(
            [CircStruct.from_pytket_circuit(c) for c in py_map.measurement_circs],
            [
                (
                    _qps_from_pytket(tkqps),
                    [MeasurementBitMap.from_pytket(tkmbm) for tkmbm in tkmbms],
                )
                for tkqps, tkmbms in py_map.results.items()
            ],
        )
