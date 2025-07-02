import json

from pydantic import BaseModel
from tierkreis.controller.data.core import EmptyModel, NodeIndex, TModel
from tierkreis.controller.data.graph import Func, GraphData, Output
from tierkreis.controller.data.refs import inputs_from_modelref, modelref_from_tmodel


class TFunc[Out: TModel](BaseModel):
    @property
    def namespace(self) -> str: ...

    @staticmethod
    def out(idx: NodeIndex) -> Out: ...


class TBuilder[Inputs: TModel, Outputs: TModel]:
    outputs_type: type
    inputs: Inputs

    def __init__(self, inputs_type: type[Inputs] = EmptyModel):
        self.data = GraphData()
        self.inputs_type = inputs_type

    def get_data(self) -> GraphData:
        return self.data

    def outputs[Out: TModel](self, outputs: Out) -> "TBuilder[Inputs, Out]":
        ref = modelref_from_tmodel(self.data, outputs)
        self.data.add(Output(inputs=inputs_from_modelref(ref)))

        builder = TBuilder[self.inputs_type, Out](self.inputs_type)
        builder.data = GraphData(**json.loads(self.data.model_dump_json()))
        builder.outputs_type = type(outputs)
        return builder

    def fn[Out: TModel](self, f: TFunc[Out]) -> Out:
        name = f"{f.namespace}.{f.__class__.__name__}"
        ins = {k: v for k, v in f.model_dump().items() if k not in ["namespace", "out"]}
        idx, _ = self.data.add(Func(name, ins))("dummy")
        return f.out(idx)
