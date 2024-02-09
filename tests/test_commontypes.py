# ruff: noqa: E402
from typing import Type

import numpy as np
import pytest

from tierkreis.core.types import MapType, StructType, TierkreisType, VecType
from tierkreis.core.values import TierkreisValue

pytket = pytest.importorskip("pytket")
from pytket._tket.circuit import Circuit
from pytket.backends.backendresult import BackendResult
from pytket.circuit import Qubit
from pytket.partition import MeasurementBitMap, MeasurementSetup
from pytket.pauli import Pauli, QubitPauliString
from pytket.utils.outcomearray import OutcomeArray

import tierkreis.common_types as common
from tierkreis.common_types import _qps_from_pytket, _qps_to_pytket
from tierkreis.common_types.circuit import (
    CircuitWrapper,
    ResultWrapper,
    register_pytket_types,
)


@pytest.mark.parametrize(
    "qps",
    [
        QubitPauliString({Qubit(0): Pauli.I, Qubit(1): Pauli.Z, Qubit(2): Pauli.X}),
        QubitPauliString({Qubit(1): Pauli.Y, Qubit(3): Pauli.Z, Qubit(2): Pauli.X}),
        QubitPauliString({Qubit(2): Pauli.X, Qubit(1): Pauli.Y, Qubit(0): Pauli.Y}),
    ],
)
def test_qps(qps: QubitPauliString):
    assert _qps_to_pytket(_qps_from_pytket(qps)) == qps


@pytest.mark.parametrize(
    "mbm",
    [
        MeasurementBitMap(2, [0, 1, 2], True),
        MeasurementBitMap(0, [0], False),
        MeasurementBitMap(0, [0], True),
    ],
)
def test_measurementbitmap(mbm: MeasurementBitMap):
    first_ser = common.MeasurementBitMap.from_pytket(mbm)
    deser = first_ser.to_pytket()
    assert first_ser == common.MeasurementBitMap.from_pytket(deser)


def test_measurementsetup():
    circ = Circuit(1, 1)
    circ.X(0)
    circ.Measure(0, 0)
    ms = MeasurementSetup()
    ms.add_measurement_circuit(circ)

    tensor = dict()
    tensor[Qubit(0)] = Pauli.Z

    mbm = MeasurementBitMap(0, [0], True)
    string = QubitPauliString(tensor)
    ms.add_result_for_term(string, mbm)
    assert ms.verify()

    ms2 = MeasurementSetup()
    circ2 = Circuit(2, 2)
    circ2.X(0)
    circ2.Measure(0, 0)
    circ2.V(1)
    circ2.Measure(1, 1)
    ms2.add_measurement_circuit(circ)
    zi = QubitPauliString()
    zi[Qubit(0)] = Pauli.Z
    mbm2 = MeasurementBitMap(0, [0], False)
    ms2.add_result_for_term(zi, mbm2)

    for m in (ms, ms2):
        first_ser = common.MeasurementSetup.from_pytket(m)
        deser = first_ser.to_pytket()
        assert first_ser == common.MeasurementSetup.from_pytket(deser)


def test_registered_conversions():
    register_pytket_types()
    tk_circ = TierkreisType.from_python(Circuit)
    assert isinstance(tk_circ, StructType)
    assert tk_circ == TierkreisType.from_python(CircuitWrapper)
    tk_res = TierkreisType.from_python(BackendResult)
    assert tk_res == TierkreisType.from_python(ResultWrapper)

    circ = Circuit(2, 2).H(0).CX(0, 1).Measure(0, 0).Measure(1, 1)
    assert TierkreisValue.from_python(circ).to_python(Circuit) == circ

    res = BackendResult(
        shots=OutcomeArray(np.array([[2, 3], [4, 5]], dtype=np.uint8), 15)
    )
    assert TierkreisValue.from_python(res).to_python(BackendResult) == res


@pytest.mark.parametrize(
    "t,expected_tk_ty",
    [
        (common.MeasurementSetup, StructType),
        (common.Distribution, MapType),
        (common.QubitPauliString, VecType),
        (common.UnitID, StructType),
    ],
)
def test_type_conversions(t: Type, expected_tk_ty: type[TierkreisType]):
    tk_ty = TierkreisType.from_python(t)
    assert isinstance(tk_ty, expected_tk_ty)
