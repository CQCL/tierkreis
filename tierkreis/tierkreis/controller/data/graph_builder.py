from tierkreis.controller.data.graph import (
    Const,
    EagerIfElse,
    Eval,
    Func,
    GraphData,
    IfElse,
    Input,
    Loop,
    Map,
    Output,
    ValueRef,
)
from tierkreis import Labels
from tierkreis.controller.data.core import Jsonable, PortID


class AutoGraphBuilder:
    def __init__(self):
        self._graph_data = GraphData()
        self._value_refs = []

    def _inputs(
        self, inputs: dict[str, int] | int | None = None
    ) -> dict[str, ValueRef]:
        n_inputs = len(inputs) if isinstance(inputs, dict) else inputs or 0
        if len(self._value_refs) < n_inputs:
            raise ValueError("Cannot add an eval, not enough nodes.")
        if inputs is None:
            inputs = {}
        if isinstance(inputs, dict):
            return {k: self._value_refs[v] for k, v in inputs.items()}
        return {f"{x}": self._value_refs[-(n_inputs + x) - 1] for x in range(n_inputs)}

    def func(self, name: str, inputs: dict[str, int] | int | None = None) -> None:
        inputs = self._inputs(inputs)
        self._value_refs.append(self._graph_data.add(Func(name, inputs))(Labels.VALUE))

    def eval(self, body: GraphData, inputs: dict[str, int] | int | None = None) -> None:
        inputs = self._inputs(inputs)
        self._value_refs.append(self._graph_data.add(Eval(body, inputs))(Labels.VALUE))

    def loop(
        self,
        body: GraphData,
        loop_condition: str,
        inputs: dict[str, int] | int | None = None,
    ) -> None:
        l_body = self._graph_data.add(Const(body))(Labels.VALUE)
        inputs = self._inputs(inputs)
        self._value_refs.append(
            self._graph_data.add(Loop(l_body, inputs, loop_condition))(Labels.VALUE)
        )

    def map(
        self,
        body: GraphData,
        inputs: dict[str, int] | int | None = None,
    ) -> None:
        inputs = self._inputs(inputs)
        m_body = self.const(body)
        map_def = Map(
            m_body, self._value_refs[-1][0], Labels.VALUE, Labels.VALUE, inputs
        )
        self._value_refs.append(self._graph_data.add(map_def)(Labels.VALUE))

    def const(self, value: Jsonable) -> None:
        self._value_refs.append(self._graph_data.add(Const(value))(Labels.VALUE))

    def ifelse(self, indices: tuple[int, int, int] = (-3, -2, -1)) -> "GraphData":
        if len(self._value_refs) < 3:
            raise ValueError("Cannot add an eifelse, not enough nodes.")
        self._value_refs.append(
            self._graph_data.add(
                IfElse(
                    self._value_refs[indices[0]],
                    self._value_refs[indices[1]],
                    self._value_refs[indices[2]],
                )
            )(Labels.VALUE)
        )
        return self

    def efelse(self, indices: tuple[int, int, int] = (-3, -2, -1)) -> None:
        if len(self._value_refs) < 3:
            raise ValueError("Cannot add an eifelse, not enough nodes.")
        self._value_refs.append(
            self._graph_data.add(
                EagerIfElse(
                    self._value_refs[indices[0]],
                    self._value_refs[indices[1]],
                    self._value_refs[indices[2]],
                )
            )(Labels.VALUE)
        )

    def input(self, name: str = Labels.VALUE) -> None:
        self._value_refs.append(self._graph_data.add(Input(name))(name))

    def output(self, outputs: str | dict[str, int] = Labels.VALUE) -> None:
        # multi outputs not supported yet
        if len(self._value_refs) == 0:
            raise ValueError("Cannot add an output to an empty graph.")
        if isinstance(outputs, dict):
            outputs = {k: self._value_refs[v] for k, v in outputs.items()}
            self._value_refs.append(self._graph_data.add(Output(outputs)))
        else:
            self._value_refs.append(
                self._graph_data.add(Output({outputs: self._value_refs[-1]}))
            )

    def instantiate_graph(self) -> GraphData:
        return self._graph_data


class GraphBuilder(GraphData):
    def func(
        self,
        name: str,
        inputs: dict[PortID, ValueRef] | ValueRef,
        ref: str = Labels.VALUE,
    ) -> ValueRef:
        if not isinstance(inputs, dict):
            inputs = {Labels.VALUE: inputs}
        return self.add(Func(name, inputs))(ref)

    def eval(
        self,
        body: GraphData,
        inputs: dict[PortID, ValueRef] | ValueRef,
        ref: str = Labels.VALUE,
    ) -> ValueRef:
        if not isinstance(inputs, dict):
            inputs = {Labels.VALUE: inputs}
        return self.add(Eval(body, inputs))(ref)

    def loop(
        self,
        body: GraphData,
        loop_condition: str,
        inputs: dict[PortID, ValueRef] | ValueRef,
        ref: str = Labels.VALUE,
    ) -> ValueRef:
        if not isinstance(inputs, dict):
            inputs = {Labels.VALUE: inputs}
        l_body = self.add(Const(body))(Labels.VALUE)
        return self.add(Loop(l_body, inputs, loop_condition))(ref)

    def map(
        self,
        body: GraphData,
        inputs: dict[PortID, ValueRef] | ValueRef,
        index: int,
        in_port: str = Labels.VALUE,
        out_port: str = Labels.VALUE,
        ref: str = Labels.VALUE,
    ) -> ValueRef:
        if not isinstance(inputs, dict):
            inputs = {Labels.VALUE: inputs}
        m_body = self.add(Const(body))(in_port)
        map_def = Map(m_body, index, in_port, out_port, inputs)
        return self.add(map_def)(ref)

    def const(self, value: Jsonable, ref: str = Labels.VALUE) -> ValueRef:
        return self.add(Const(value))(ref)

    def ifelse(
        self,
        inputs: tuple[ValueRef, ValueRef, ValueRef] = (-3, -2, -1),
        ref: str = Labels.VALUE,
    ) -> ValueRef:
        return self.add(IfElse(inputs))(ref)

    def efelse(
        self,
        inputs: tuple[ValueRef, ValueRef, ValueRef],
        ref: str = Labels.VALUE,
    ) -> ValueRef:
        return self.add(EagerIfElse(inputs))(ref)

    def input(self, name: str = Labels.VALUE) -> ValueRef:
        return self.add(Input(name))(name)

    def output(self, outputs: dict[PortID, ValueRef] | ValueRef) -> None:
        if isinstance(outputs, dict):
            self.add(Output(outputs))
        else:
            self.add(Output({Labels.VALUE: outputs}))
