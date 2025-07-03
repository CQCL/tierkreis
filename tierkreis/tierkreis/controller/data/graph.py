from dataclasses import dataclass, field
import logging
from typing import Any, Callable, Literal, assert_never
from tierkreis.controller.data.refs import modelref_from_tmodel
from typing_extensions import TypeVar
from pydantic import BaseModel, RootModel
from tierkreis.controller.data.core import (
    EmptyModel,
    Function,
    TModel,
    TType,
    fields_tmodel,
)
from tierkreis.controller.data.core import PortID
from tierkreis.controller.data.core import NodeIndex
from tierkreis.controller.data.core import ValueRef
from tierkreis.controller.data.location import OutputLoc
from tierkreis.exceptions import TierkreisError

logger = logging.getLogger(__name__)


@dataclass
class Func:
    function_name: str
    inputs: dict[PortID, ValueRef]
    type: Literal["function"] = field(default="function")


@dataclass
class Eval:
    graph: ValueRef
    inputs: dict[PortID, ValueRef]
    type: Literal["eval"] = field(default="eval")


@dataclass
class Loop:
    body: ValueRef
    inputs: dict[PortID, ValueRef]
    continue_port: PortID  # The port that specifies if the loop should continue.
    type: Literal["loop"] = field(default="loop")


@dataclass
class Map:
    body: ValueRef
    input_idx: NodeIndex
    in_port: PortID  # Input port for the Map.body
    out_port: PortID  # Output port for the Map.body
    inputs: dict[PortID, ValueRef]
    type: Literal["map"] = field(default="map")


@dataclass
class Const:
    value: Any
    inputs: dict[PortID, ValueRef] = field(default_factory=lambda: {})
    type: Literal["const"] = field(default="const")


@dataclass
class IfElse:
    pred: ValueRef
    if_true: ValueRef
    if_false: ValueRef
    type: Literal["ifelse"] = field(default="ifelse")
    inputs: dict[PortID, ValueRef] = field(default_factory=lambda: {})


@dataclass
class EagerIfElse:
    pred: ValueRef
    if_true: ValueRef
    if_false: ValueRef
    type: Literal["eifelse"] = field(default="eifelse")
    inputs: dict[PortID, ValueRef] = field(default_factory=lambda: {})


@dataclass
class Input:
    name: str
    inputs: dict[PortID, ValueRef] = field(default_factory=lambda: {})
    type: Literal["input"] = field(default="input")


@dataclass
class Output:
    inputs: dict[PortID, ValueRef]
    type: Literal["output"] = field(default="output")


NodeDef = Func | Eval | Loop | Map | Const | IfElse | EagerIfElse | Input | Output
NodeDefModel = RootModel[NodeDef]


class GraphData(BaseModel):
    nodes: list[NodeDef] = []
    node_outputs: list[set[PortID]] = []
    fixed_inputs: dict[PortID, OutputLoc] = {}
    graph_inputs: set[PortID] = set()
    graph_output_idx: NodeIndex | None = None

    def input(self, name: str) -> ValueRef:
        return self.add(Input(name))(name)

    def const(self, value: Any) -> ValueRef:
        return self.add(Const(value))("value")

    def func(
        self, function_name: str, inputs: dict[PortID, ValueRef]
    ) -> Callable[[PortID], ValueRef]:
        return self.add(Func(function_name, inputs))

    def eval(
        self, graph: ValueRef, inputs: dict[PortID, ValueRef]
    ) -> Callable[[PortID], ValueRef]:
        return self.add(Eval(graph, inputs))

    def loop(
        self, body: ValueRef, inputs: dict[PortID, ValueRef], continue_port: PortID
    ) -> Callable[[PortID], ValueRef]:
        return self.add(Loop(body, inputs, continue_port))

    def map(
        self,
        body: ValueRef,
        input_idx: NodeIndex,
        in_port: PortID,
        out_port: PortID,
        inputs: dict[PortID, ValueRef],
    ) -> Callable[[PortID], ValueRef]:
        return self.add(Map(body, input_idx, in_port, out_port, inputs))

    def output(self, inputs: dict[PortID, ValueRef]) -> None:
        self.add(Output(inputs))

    def add(self, node: NodeDef) -> Callable[[PortID], ValueRef]:
        idx = len(self.nodes)
        self.nodes.append(node)
        self.node_outputs.append(set())

        match node.type:
            case "output":
                if self.graph_output_idx is not None:
                    raise TierkreisError(
                        f"Graph already has output at index {self.graph_output_idx}"
                    )

                self.graph_output_idx = idx
            case "ifelse" | "eifelse":
                self.node_outputs[node.pred[0]].add(node.pred[1])
                self.node_outputs[node.if_true[0]].add(node.if_true[1])
                self.node_outputs[node.if_false[0]].add(node.if_false[1])
            case "input":
                self.graph_inputs.add(node.name)
            case "const" | "eval" | "function" | "loop" | "map":
                pass
            case _:
                assert_never(node)

        for i, port in node.inputs.values():
            self.node_outputs[i].add(port)

        return lambda k: (idx, k)

    def output_idx(self) -> NodeIndex:
        idx = self.graph_output_idx
        if idx is None:
            raise TierkreisError("Graph has no output index.")

        node = self.nodes[idx]
        if node.type != "output":
            raise TierkreisError(f"Expected output node at {idx} found {node}")

        return idx

    def remaining_inputs(self, provided_inputs: set[PortID]) -> set[PortID]:
        fixed_inputs = set(self.fixed_inputs.keys())
        if fixed_inputs & provided_inputs:
            raise TierkreisError(
                f"Fixed inputs {fixed_inputs}"
                f" should not intersect provided inputs {provided_inputs}."
            )

        actual_inputs = fixed_inputs.union(provided_inputs)
        return self.graph_inputs - actual_inputs


@dataclass
class TypedGraphRef[Inputs: TModel, Outputs: TModel]:
    graph_ref: ValueRef
    inputs_type: type[Inputs]
    outputs_type: type[Outputs]


In = TypeVar("In", bound=tuple[TType, ...], contravariant=True)


def ref_from_ttype(g: GraphData, t: TType) -> ValueRef:
    if isinstance(t, tuple) and not hasattr(t, "_fields"):
        return t  # type: ignore
    return g.add(Const(t))("value")


def inputs_from_tmodel(g: GraphData, t: TModel) -> dict[PortID, ValueRef]:
    if isinstance(t, tuple) and not hasattr(t, "_fields"):
        return {"value": ref_from_ttype(g, t)}
    match t:
        case tuple():
            as_dict = getattr(t, "_asdict", None)
            if as_dict is None:
                raise TierkreisError("TModel should be NamedTuple.")
            return {k: ref_from_ttype(g, v) for k, v in as_dict().items()}
        case _:
            return {"value": ref_from_ttype(g, t)}


class GraphBuilder[Inputs: TModel, Outputs: TModel]:
    outputs_type: type
    inputs: Inputs

    def __init__(
        self,
        inputs_type: type[Inputs] = EmptyModel,
        outputs_type: type[Outputs] = EmptyModel,
    ):
        self.data = GraphData()
        self.inputs_type = inputs_type
        self.outputs_type = outputs_type

        in_refs = [self.data.add(Input(k))(k) for k in fields_tmodel(self.inputs_type)]
        model_ref = modelref_from_tmodel(inputs_type, in_refs)
        self.inputs = model_ref  # type: ignore # deliberately wrong

    def get_data(self) -> GraphData:
        return self.data

    def outputs(self, outputs: Outputs) -> None:
        self.data.add(Output(inputs=inputs_from_tmodel(self.data, outputs)))

    def graph_const[A: TModel, B: TModel](
        self, graph: "GraphBuilder[A, B]"
    ) -> TypedGraphRef[A, B]:
        idx, port = self.data.add(Const(graph.data))("value")
        return TypedGraphRef[A, B](
            graph_ref=(idx, port),
            inputs_type=graph.inputs_type,
            outputs_type=graph.outputs_type,
        )

    def fn[Out: TModel](self, f: Function[Out]) -> Out:
        name = f"{f.namespace}.{f.__class__.__name__}"
        ins = inputs_from_tmodel(self.data, f)
        idx, _ = self.data.add(Func(name, ins))("dummy")
        return f.out(idx)

    def eval[A: TModel, B: TModel](self, body: TypedGraphRef[A, B], a: A) -> B:
        ins = inputs_from_tmodel(self.data, a)
        g = body.graph_ref
        idx, _ = self.data.add(Eval(g, ins))("dummy")
        Out = body.outputs_type
        model_ref = modelref_from_tmodel(Out, [(idx, k) for k in fields_tmodel(Out)])
        return model_ref  # type: ignore # deliberately wrong

    # def loop[A: TKRModel, B: TKRModel](
    #     self, body: TypedGraphRef[A, B], a: A, continue_port: PortID
    # ) -> B:
    #     ins = {k: (v[0], v[1]) for k, v in annotations_from_tkrref(a).items()}
    #     g = body.graph_ref
    #     Out = body.outputs_type
    #     idx, _ = self.data.add(Loop(g, ins, continue_port))("dummy")
    #     return ref_from_tkr_type(Out, lambda _: idx)

    # def unfold_list[T: TKRType](self, ref: TKRRef[list[T]]) -> TKRList[TKRRef[T]]:
    #     idx, _ = self.data.add(Func("builtins.unfold_values", {"value": ref}))("dummy")
    #     return TKRList(TKRRef[T](idx, "*"))

    # def fold_list[T: TKRType](self, refs: TKRList[TKRRef[T]]) -> TKRRef[list[T]]:
    #     idx, port = refs.t
    #     idx, _ = self.data.add(
    #         Func("builtins.fold_values", {"values_glob": (idx, port)})
    #     )("dummy")
    #     return TKRRef[list[T]](idx, "value")

    # def map[A: TKRModel, B: TKRModel](
    #     self, body: TypedGraphRef[A, B], aes: TKRList[A]
    # ) -> TKRList[B]:
    #     a = aes.t
    #     ins = {k: (v[0], v[1]) for k, v in annotations_from_tkrref(a).items()}
    #     g = body.graph_ref
    #     first_ref = cast(TKRRef[Any], next(x for x in ins.values() if x[1] == "*"))
    #     idx, _ = self.data.add(Map(g, first_ref[0], "dummy", "dummy", ins))("dummy")

    #     Out = body.outputs_type
    #     return TKRList(
    #         ref_from_tkr_type(Out, lambda _: idx, name_fn=lambda s: s + "-*")
    #     )
