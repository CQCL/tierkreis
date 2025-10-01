# ruff: noqa: F821
from typing import NamedTuple, Union
from tierkreis.builder import GraphBuilder
from tierkreis.controller.data.models import TKR, OpaqueType
from tierkreis.builtins.stubs import zip_impl, untuple
from tierkreis.aer_worker import get_compiled_circuit, run_circuit

type AerConfig = OpaqueType["quantinuum_schemas.models.backend_config.AerConfig"]
type BackendResult = OpaqueType["pytket.backends.backendresult.BackendResult"]
type Circuit = OpaqueType["pytket._tket.circuit.Circuit"]


class AerJobInputs(NamedTuple):
    circuits: TKR[list[Circuit]]
    n_shots: TKR[list[int]]
    config: TKR[AerConfig]
    optimisation_level: TKR[Union[int, None]]
    timeout: TKR[Union[int, None]]


class CompileCircuitInputs(NamedTuple):
    circuit: TKR[Circuit]
    config: TKR[AerConfig]
    optimisation_level: TKR[Union[int, None]]
    timeout: TKR[Union[int, None]]


class SimulateCircuitInputs(NamedTuple):
    circuit_shots: TKR[tuple[Circuit, int]]
    config: TKR[AerConfig]


def aer_compile():
    g = GraphBuilder(CompileCircuitInputs, TKR[Circuit])
    compiled_circuit = g.task(
        get_compiled_circuit(
            circuit=g.inputs.circuit,
            optimisation_level=g.inputs.optimisation_level,
            timeout=g.inputs.timeout,
            config=g.inputs.config,
        )
    )
    g.outputs(compiled_circuit)
    return g


def aer_run():
    g = GraphBuilder(SimulateCircuitInputs, TKR[BackendResult])
    f = g.task(untuple(g.inputs.circuit_shots))
    res = g.task(run_circuit(f.a, f.b, g.inputs.config))
    g.outputs(res)
    return g


def aer_compile_run():
    g = GraphBuilder(AerJobInputs, TKR[list[BackendResult]])

    compile_inputs = g.map(
        lambda x: CompileCircuitInputs(
            circuit=x,
            config=g.inputs.config,
            timeout=g.inputs.timeout,
            optimisation_level=g.inputs.optimisation_level,
        ),
        g.inputs.circuits,
    )
    compiled = g.map(aer_compile(), compile_inputs)

    circuits_shots = g.task(zip_impl(compiled, g.inputs.n_shots))

    run_inputs = g.map(
        lambda circuit_shots: SimulateCircuitInputs(
            circuit_shots=circuit_shots, config=g.inputs.config
        ),
        circuits_shots,
    )
    res = g.map(aer_run(), run_inputs)

    g.outputs(res)
    return g
