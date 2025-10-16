# ruff: noqa: F821
from typing import NamedTuple, Union
from tierkreis.builder import GraphBuilder
from tierkreis.controller.data.models import TKR, OpaqueType
from tierkreis.builtins.stubs import zip_impl, untuple
from tierkreis.pytket_simulators_worker import get_compiled_circuit, run_circuit

type AerConfig = OpaqueType["quantinuum_schemas.models.backend_config.AerConfig"]
type QulacsConfig = OpaqueType["quantinuum_schemas.models.backend_config.QulacsConfig"]
type BackendResult = OpaqueType["pytket.backends.backendresult.BackendResult"]
type Circuit = OpaqueType["pytket._tket.circuit.Circuit"]


class AerJobInputs(NamedTuple):
    circuits: TKR[list[Circuit]]
    n_shots: TKR[list[int]]
    config: TKR[AerConfig | QulacsConfig]
    compilation_optimisation_level: TKR[Union[int, None]]


class AerJobInputsSingle(NamedTuple):
    circuit_shots: TKR[tuple[Circuit, int]]
    config: TKR[AerConfig | QulacsConfig]
    compilation_optimisation_level: TKR[Union[int, None]]


def aer_compile_run_single():
    g = GraphBuilder(AerJobInputsSingle, TKR[BackendResult])
    circuit_shots = g.task(untuple(g.inputs.circuit_shots))

    compiled_circuit = g.task(
        get_compiled_circuit(
            circuit=circuit_shots.a,
            optimisation_level=g.inputs.compilation_optimisation_level,
            config=g.inputs.config,
        )
    )
    res = g.task(run_circuit(compiled_circuit, circuit_shots.b, g.inputs.config))
    g.outputs(res)
    return g


def aer_compile_run():
    g = GraphBuilder(AerJobInputs, TKR[list[BackendResult]])

    circuits_shots = g.task(zip_impl(g.inputs.circuits, g.inputs.n_shots))

    inputs = g.map(
        lambda x: AerJobInputsSingle(
            circuit_shots=x,
            config=g.inputs.config,
            compilation_optimisation_level=g.inputs.compilation_optimisation_level,
        ),
        circuits_shots,
    )
    res = g.map(aer_compile_run_single(), inputs)

    g.outputs(res)
    return g
