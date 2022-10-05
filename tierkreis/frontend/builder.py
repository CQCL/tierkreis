import inspect
from abc import ABC, abstractmethod
from contextlib import AbstractContextManager
from contextvars import ContextVar, Token
from dataclasses import dataclass, field
from functools import update_wrapper, wraps
from itertools import count
from types import TracebackType
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Generic,
    Iterable,
    Iterator,
    Mapping,
    Optional,
    Type,
    TypeVar,
    Union,
    cast,
    get_args,
    get_origin,
    get_type_hints,
    overload,
)

from yachalk import chalk

from tierkreis.core import Labels
from tierkreis.core.function import FunctionDeclaration, FunctionName
from tierkreis.core.signature import Namespace as SigNamespace
from tierkreis.core.signature import Signature
from tierkreis.core.tierkreis_graph import (
    BoxNode,
    FunctionNode,
    IncomingWireType,
    MatchNode,
    NodePort,
    NodeRef,
    OutputNode,
    PortID,
    TagNode,
    TierkreisGraph,
    TierkreisNode,
    to_nodeport,
)
from tierkreis.core.tierkreis_struct import TierkreisStruct
from tierkreis.core.types import TierkreisTypeErrors, TypeScheme
from tierkreis.core.utils import map_vals
from tierkreis.core.values import TierkreisValue, TKVal1, tkvalue_to_tktype
from tierkreis.frontend.type_inference import infer_graph_types

if TYPE_CHECKING:
    from tierkreis.core.types import GraphType, TierkreisType


# magic for lazily creating nodes (and returning ports thereof)
class PortFunc(ABC):
    @abstractmethod
    def resolve(self) -> NodePort:
        """Return a NodePort, creating nodes as necessary in source graph."""

    @abstractmethod
    def source_graph(self) -> TierkreisGraph:
        """The graph the port belongs to (or will)."""


ValueSource = Union[IncomingWireType, PortFunc]


class StablePortFunc(PortFunc):
    """Extends the contract of PortFunc, as documented for the resolve method"""

    @abstractmethod
    def resolve(self) -> NodePort:
        """As superclass, but guarantees that all calls return the same NodePort."""

    def __getitem__(self, field_name: str) -> "Unpack":
        # Syntactic sugar for unpacking structs
        return Unpack(self, field_name)


def _resolve(s: ValueSource) -> NodePort:
    return s.resolve() if isinstance(s, PortFunc) else to_nodeport(s)


def _source_graph(s: ValueSource) -> TierkreisGraph:
    return (
        s.source_graph() if isinstance(s, PortFunc) else to_nodeport(s).node_ref.graph
    )


__state: ContextVar["GraphBuilder"] = ContextVar("state")


class InvalidContext(Exception):
    """Expression not valid outside GraphBuilder `with` context"""


def current_builder() -> "GraphBuilder":
    try:
        return __state.get()
    except LookupError as e:
        raise InvalidContext() from e


def current_graph() -> TierkreisGraph:
    return current_builder().graph


def _set_state(bg: "GraphBuilder") -> Token["GraphBuilder"]:
    return __state.set(bg)


def _reset_state(tok: Token["GraphBuilder"]):
    return __state.reset(tok)


def _capture_label(idx: int) -> PortID:
    return f"_c{idx}"


OptSig = Optional[Signature]


class GraphBuilder(AbstractContextManager):
    graph: TierkreisGraph
    inputs: dict[str, Optional["TierkreisType"]]
    outputs: dict[str, Optional["TierkreisType"]]
    captured: dict[ValueSource, PortID]
    sig: OptSig = None
    _state_token: Token["GraphBuilder"]

    def __init__(
        self,
        inputs: Optional[Dict[str, Optional["TierkreisType"]]] = None,
        outputs: Optional[Dict[str, Optional["TierkreisType"]]] = None,
        name: str = "",
    ) -> None:
        self.graph = TierkreisGraph(name)
        self.inputs = inputs or {}
        self.outputs = outputs or {}
        self.captured = {}
        self.sig = None
        for i, it in self.inputs.items():
            self.graph.discard(self.graph.input[i])
            self.graph.annotate_input(i, it)
            self.graph.input_order.append(i)

    def input(self, name: str) -> NodePort:
        if name in self.inputs:
            return self.graph.input[name]
        raise RuntimeError("Input not declared.")

    def with_type_check(self, signatures: Signature) -> "GraphBuilder":
        self.sig = signatures
        return self

    def __enter__(self) -> "GraphBuilder":
        self._state_token = _set_state(self)
        return self

    def __exit__(
        self,
        __exc_type: Optional[Type[BaseException]],
        __exc_value: Optional[BaseException],
        __traceback: Optional[TracebackType],
    ) -> Optional[bool]:

        _reset_state(self._state_token)
        return super().__exit__(__exc_type, __exc_value, __traceback)

    def capture(
        self, incoming: ValueSource, allow_existing: bool = False
    ) -> ValueSource:
        if _source_graph(incoming) is self.graph:
            return incoming
        if incoming in self.captured and not allow_existing:
            # This would generate two wires from the same NodePort
            raise ValueError(f"Already captured {incoming} as input to {self.graph}")
        in_name = self.captured.setdefault(incoming, _capture_label(len(self.captured)))
        return self.graph.input[in_name]

    def add_node_to_graph(
        self,
        _tk_node: TierkreisNode,
        _type_check: bool = True,
        _tk_node_name: Optional[str] = None,
        /,
        **incoming_wires: ValueSource,
    ) -> NodeRef:
        nr = self.graph.add_node(_tk_node, _tk_node_name)
        for tgt_port, vs in incoming_wires.items():
            self.graph.add_edge(_resolve(self.capture(vs)), nr[tgt_port])
        if _type_check:
            self.type_check()
        return nr

    def set_graph_outputs(self, **incoming_wires: ValueSource) -> None:
        if len(self.graph.outputs()) != 0:
            raise RuntimeError("Outputs set multiple times for same graph.")
        self.graph._graph.remove_node(self.graph.output_node_name)
        self.add_node_to_graph(
            OutputNode(),
            True,
            self.graph.output_node_name,
            **incoming_wires,
        )

    def type_check(self):
        if self.sig is None:
            return
        try:
            self.graph._graph = infer_graph_types(self.graph, self.sig)._graph
        except TierkreisTypeErrors as te:
            raise IncrementalTypeError("Builder expression caused type error.") from te
            # TODO remove final entry in traceback?


def _partial_thunk(
    thunk: Union[GraphBuilder, NodePort], captured: dict[ValueSource, PortID]
) -> NodePort:
    # add the thunk as constant to the current graph and partial up
    bg = current_builder()
    if isinstance(thunk, GraphBuilder):
        thunk = bg.graph.add_const(thunk.graph)[Labels.VALUE]
    if captured:
        return bg.add_node_to_graph(
            FunctionNode(FunctionName("partial")),
            thunk=thunk,
            **{k: v for v, k in captured.items()},
        )[Labels.VALUE]
    return thunk


T = TypeVar("T")


class IncrementalTypeError(Exception):
    pass


class Const(NodePort):
    """"""

    def __init__(
        self,
        val: Union[
            int,
            float,
            bool,
            str,
            dict,
            TierkreisStruct,
            TierkreisValue,
            TierkreisGraph,
            tuple,
            list,
        ],
    ):
        bg = current_builder()
        n = bg.graph.add_const(val)
        super().__init__(n, Labels.VALUE)


@dataclass(frozen=True)
class _CallAddNode:
    node: TierkreisNode
    input_order: list[str]
    output_order: list[str]

    def __call__(self, *args: ValueSource, **kwds: ValueSource) -> NodeRef:
        bg = current_builder()
        kwds = _combine_args_with_kwargs(self.input_order, *args, **kwds)
        n = bg.add_node_to_graph(self.node, **kwds)
        return NodeRef(n.name, n.graph, self.output_order)


class Box(_CallAddNode):
    graph: TierkreisGraph

    def __init__(self, graph: TierkreisGraph):
        self.graph = graph
        super().__init__(BoxNode(graph), graph.input_order, graph.output_order)


def Tag(tag: str, value: ValueSource) -> NodePort:
    return current_builder().add_node_to_graph(TagNode(tag), value=value)[Labels.VALUE]


OutAnnotation = TypeVar(
    "OutAnnotation",
    bound=Union[TierkreisStruct, TierkreisValue],
)


class Output(NodeRef, Generic[OutAnnotation]):
    def __init__(self, *args: ValueSource, **kwargs: ValueSource) -> None:
        s = current_builder()

        g = s.graph

        for o in s.outputs:
            g.output_order.append(o)

        if len(args) == 1 and len(kwargs) == 0:
            kwargs = {Labels.VALUE: args[0]}
        else:
            kwargs = _combine_args_with_kwargs(s.outputs.keys(), *args, **kwargs)

        s.set_graph_outputs(**kwargs)
        for o in kwargs:
            if ot := s.outputs.get(o):
                g.annotate_output(o, ot)

        super().__init__(g.output.name, g)


class _LoopOutput(Output):
    def __init__(self, loopout: ValueSource) -> None:
        super().__init__(value=loopout)


class Continue(_LoopOutput):
    def __init__(self, loopout: ValueSource) -> None:
        super().__init__(Tag(Labels.CONTINUE, loopout))


class Break(_LoopOutput):
    def __init__(self, loopout: ValueSource) -> None:
        super().__init__(Tag(Labels.BREAK, loopout))


def _vals_to_types(
    d: dict[str, Optional[Type["TierkreisValue"]]]
) -> dict[str, Optional["TierkreisType"]]:
    return map_vals(
        d, lambda arg: None if (arg is Any or arg is None) else tkvalue_to_tktype(arg)
    )


def _convert_input(t: Optional[Type["Input[TierkreisValue]"]]) -> Optional[Type]:
    if t is not None:
        if not (get_origin(t) == Input or t == Input):
            raise TypeError(
                "Graph builder function arguments must be ``Input``"
                " with an optional ``TierkreisValue`` argument."
                "For example Input[IntValue]"
            )

        args = get_args(t)
        if args:
            return args[0]
    return None


_RETURN_TYPE_ERROR = TypeError(
    "Graph builder function must be annotated with return type `Output`."
    " Optionally annotate with "
    "`Output[TierkreisValue]` for a single return from port 'value',"
    " or with a `TierkreisStruct` specifying the Row type of the ouput."
)


def _convert_return(ret: Type) -> dict[str, Optional["TierkreisType"]]:
    if not (get_origin(ret) == Output or ret == Output):
        raise _RETURN_TYPE_ERROR
    args = get_args(ret)
    if not args:
        return {}
    ret = args[0]
    subc = get_origin(ret) or ret
    if issubclass(subc, TierkreisStruct):
        return _vals_to_types(get_type_hints(ret))
    if issubclass(subc, TierkreisValue):
        return _vals_to_types({Labels.VALUE: ret})

    raise _RETURN_TYPE_ERROR


class Input(Generic[TKVal1], NodePort):
    def __init__(self, port: PortID) -> None:
        np = current_builder().graph.input[port]
        super().__init__(np.node_ref, np.port)


_GraphDef = Callable[..., Output]
_GraphDecoratorType = Callable[[_GraphDef], Callable[[], TierkreisGraph]]


def _get_edge_annotations(
    f: _GraphDef,
) -> tuple[dict[str, Optional["TierkreisType"]], dict[str, Optional["TierkreisType"]],]:
    f_sig = inspect.signature(f)
    inps = map_vals(
        inspect.signature(f).parameters,
        lambda x: None if x.annotation is inspect.Signature.empty else x.annotation,
    )
    out_types = (
        {}
        if f_sig.return_annotation is inspect.Signature.empty
        else _convert_return(f_sig.return_annotation)
    )
    in_types = _vals_to_types(map_vals(inps, _convert_input))
    return in_types, out_types


class CapturedError(Exception):
    pass


def graph(name: Optional[str] = None, sig: OptSig = None) -> _GraphDecoratorType:
    def decorator_graph(f: _GraphDef) -> Callable[[], TierkreisGraph]:
        in_types, out_types = _get_edge_annotations(f)
        # Use getattr as _GraphDef doesn't specify that it has a __name__
        graph_name = name or getattr(f, "__name__")
        # graph_name = name or f.__name__  # type: ignore  # the alternative

        @wraps(f)
        def wrapper() -> TierkreisGraph:
            gb = GraphBuilder(in_types, out_types, name=graph_name)
            if sig:
                gb = gb.with_type_check(sig)
            with gb as sub_build:
                f(*(Input(port) for port in in_types))
            if sub_build.captured:
                raise CapturedError(
                    "Graph contains inputs captured from other graphs. "
                    "Use @closure if appropriate."
                )
            return sub_build.graph

        wrapper.__annotations__ = {}
        return wrapper

    return decorator_graph


class Thunk(_CallAddNode):
    graph_src: ValueSource

    def __init__(
        self, graph_src: ValueSource, input_order: list[str], output_order: list[str]
    ):
        self.graph_src = graph_src
        super().__init__(FunctionNode(FunctionName("eval")), input_order, output_order)

    def __call__(self, *args: ValueSource, **kwargs: ValueSource) -> NodeRef:
        assert "thunk" not in kwargs
        return super().__call__(*args, thunk=self.graph_src, **kwargs)

    def copyable(self) -> "Thunk":
        self.graph_src = Copyable(self.graph_src)
        return self


def closure(
    name: Optional[str] = None, sig: OptSig = None
) -> Callable[[_GraphDef], Thunk]:
    def decorator_graph(f: _GraphDef) -> Thunk:
        in_types, out_types = _get_edge_annotations(f)
        # Use getattr as _GraphDef doesn't specify that it has a __name__
        graph_name = name or getattr(f, "__name__")
        # graph_name = name or f.__name__  # type: ignore  # the alternative

        gb = GraphBuilder(in_types, out_types, name=graph_name)
        if sig:
            gb = gb.with_type_check(sig)
        with gb as sub_build:
            f(*(Input(port) for port in in_types))
        # Copy docstring, etc., onto the TierkreisGraph.
        # (Of course such will be lost if the graph is serialized.)
        wrapper = sub_build.graph
        update_wrapper(wrapper, f)
        wrapper.__annotations__ = {}
        return Thunk(
            _partial_thunk(sub_build, sub_build.captured),
            list(in_types.keys()),
            list(out_types.keys()),
        )

    return decorator_graph


def loop(name: Optional[str] = None, sig: OptSig = None):
    def decorator_graph(f: _GraphDef):
        in_types, out_types = _get_edge_annotations(f)
        if len(in_types) != 1:
            raise ValueError("Loop body graph can only have one input.")

        # the loop node has input port "value"
        # allow body definitions to use any input names and map it
        in_types = {Labels.VALUE: in_types.popitem()[1]}
        graph_name = name or getattr(f, "__name__")

        @wraps(f)
        def wrapper(initial: ValueSource) -> NodePort:
            gb = GraphBuilder(in_types, out_types, name=graph_name)
            if sig:
                gb = gb.with_type_check(sig)
            with gb as sub_build:
                f(Input(Labels.VALUE))

            loop_node = current_builder().add_node_to_graph(
                FunctionNode(FunctionName("loop")),
                body=_partial_thunk(sub_build, sub_build.captured),
                value=initial,
            )
            return loop_node[Labels.VALUE]

        return wrapper

    return decorator_graph


class If(GraphBuilder):
    def __init__(self) -> None:
        super().__init__()
        self.graph.name = "if"
        Match._add_handler("if", self)


class Else(GraphBuilder):
    def __init__(self) -> None:
        super().__init__()
        self.graph.name = "else"
        Match._add_handler("else", self)


class DuplicateBlock(Exception):
    """Duplicate blocks, avoid multiple If/Else or duplicate Case blocks."""

    block_name: str


class IntermediateNodes(Exception):
    """Adding of nodes not valid in _CaseScope outside child blocks."""


class _CaseScope(GraphBuilder, ABC):
    __variant_handlers: ContextVar[dict[str, GraphBuilder]] = ContextVar(
        "variant_handlers"
    )

    _token: Token[dict[str, GraphBuilder]]
    nref: NodeRef

    @classmethod
    def _get_handlers(cls) -> dict[str, GraphBuilder]:
        return cls.__variant_handlers.get()

    def __enter__(self) -> "_CaseScope":
        super().__enter__()
        self._token = self.__variant_handlers.set({})
        return self

    @classmethod
    def _add_handler(cls, tag: str, handler: GraphBuilder):
        handlers = cls.__variant_handlers.get()
        if tag in handlers:
            raise DuplicateBlock(tag)
        handlers[tag] = handler

    @abstractmethod
    def _get_thunk(self) -> NodePort:
        ...

    @abstractmethod
    def _intermediate_error(self) -> IntermediateNodes:
        ...

    def __exit__(
        self,
        __exc_type: Optional[Type[BaseException]],
        __exc_value: Optional[BaseException],
        __traceback: Optional[TracebackType],
    ) -> None:
        super().__exit__(__exc_type, __exc_value, __traceback)

        if not any((__exc_type, __exc_value, __traceback)):
            # do not perform graph building if error

            if set(self.graph.nodes().keys()) != {
                self.graph.input_node_name,
                self.graph.output_node_name,
            }:
                raise self._intermediate_error()
            handlers = self.__variant_handlers.get()
            thunk_port = self._get_thunk()
            partial_inps = _combine_captures(list(handlers.values()))
            thunk_port = _partial_thunk(thunk_port, partial_inps)

            self.nref = current_builder().add_node_to_graph(
                FunctionNode(FunctionName("eval")), thunk=thunk_port
            )
        self.__variant_handlers.reset(self._token)


class Match(_CaseScope):
    variant_value: ValueSource

    def __init__(self, variant_value: ValueSource):
        super().__init__()
        self.variant_value = variant_value

    def _get_thunk(self) -> NodePort:
        handlers = _CaseScope._get_handlers()
        bg = current_builder()
        return bg.add_node_to_graph(
            MatchNode(),
            False,
            variant_value=self.variant_value,
            **map_vals(handlers, lambda x: bg.graph.add_const(x.graph)),
        )[Labels.THUNK]

    def _intermediate_error(self) -> IntermediateNodes:
        return IntermediateNodes(
            "Graph building operations outside Case blocks not allowed in Match block."
        )


class Case(GraphBuilder):
    var_value: NodePort

    def __init__(self, tag: str) -> None:
        super().__init__()
        self.graph.name = tag
        Match._add_handler(tag, self)

        self.var_value = self.graph.input[Labels.VALUE]

    def __enter__(self) -> "Case":
        return cast(Case, super().__enter__())


class IfElse(_CaseScope):
    predicate: ValueSource

    def __init__(self, predicate: ValueSource):
        super().__init__()
        self.predicate = predicate

    def _get_thunk(self) -> NodePort:
        handlers = _CaseScope._get_handlers()
        assert len(handlers) == 2
        bg = current_builder()
        return bg.add_node_to_graph(
            FunctionNode(FunctionName("switch")),
            False,
            pred=self.predicate,
            if_true=bg.graph.add_const(handlers["if"].graph),
            if_false=bg.graph.add_const(handlers["else"].graph),
        )[Labels.VALUE]

    def _intermediate_error(self) -> IntermediateNodes:
        return IntermediateNodes(
            "Graph building operations outside"
            " If/Else blocks not allowed in IfElse block."
        )


def _combine_captures(thunks: list[GraphBuilder]) -> dict[ValueSource, PortID]:
    """Given a list of thunks with captured inputs, remove their existing input
    names, common up any shared sources (up to == equality), and add all those
    inputs to all graphs, discarding any unused."""
    old_names = frozenset([v for bg in thunks for v in bg.captured.values()])
    # Generate a sparsely numbered list of names that won't conflict:
    names = filter(lambda x: x not in old_names, map(_capture_label, count()))
    # Assign new names in deterministic order of thunks and captures in each
    combined_inputs: dict[ValueSource, str] = {
        vs: next(names) for bg in thunks for vs in bg.captured
    }  # Duplicate ValueSources overwrite earlier entries, making even sparser.
    for vs, nam in combined_inputs.items():
        for bg in thunks:
            if in_name := bg.captured.get(vs):
                in_edge = bg.graph.out_edge_from_port(bg.graph.input[in_name])
                assert in_edge is not None
                bg.graph._graph.remove_edge(*in_edge.to_edge_handle())
                bg.graph.add_edge(bg.graph.input[nam], in_edge.target)
            else:
                bg.graph.discard(bg.graph.input[nam])

    return combined_inputs


def _combine_args_with_kwargs(
    expected: Iterable[str], *args: ValueSource, **kwargs: ValueSource
) -> dict[str, ValueSource]:
    pos_args = dict(zip(expected, args))
    if ints := set(kwargs).intersection(pos_args):
        raise RuntimeError(f"Arguments specified positionally and in keywords: {ints}")
    kwargs.update(pos_args)
    return kwargs


@dataclass(frozen=True)
class Copyable(PortFunc):
    """Inserts a copy of an underlying ValueSource whenever an outgoing edge is added
    unless there are *no* existing uses of the underlying ValueSource
    (=> the wire is routed from the underlying ValueSource)
    """

    src: ValueSource
    target_builder: GraphBuilder = field(default_factory=current_builder, init=False)

    def resolve(self) -> NodePort:
        src = self.src
        while isinstance(src, Copyable) and src.target_builder == self.target_builder:
            src = src.src  # Canonicalize a bit
        # Get a nodeport in our target graph, so copies will go there
        np = self.target_builder.capture(_resolve(src), allow_existing=True)
        assert isinstance(np, NodePort)
        g = np.node_ref.graph
        assert g is self.target_builder.graph
        existing_edge = g.out_edge_from_port(np)
        if existing_edge is None:
            return np
        g._graph.remove_edge(*existing_edge.to_edge_handle())
        c1, c2 = g.copy_value(np)
        g.add_edge(c1, existing_edge.target, existing_edge.type_)
        return c2

    def source_graph(self) -> "TierkreisGraph":
        return self.target_builder.graph


@dataclass(frozen=True)
class Unpack(StablePortFunc):
    src: Union[NodePort, StablePortFunc]
    field_name: str

    def resolve(self) -> NodePort:
        np = _resolve(self.src)
        g = np.node_ref.graph
        existing_edge = g.out_edge_from_port(np)
        if existing_edge is not None:
            target_node = g[existing_edge.target.node_ref]
            if not target_node.is_unpack_node():
                raise ValueError(
                    "Cannot unpack port wired to something "
                    f" other than an unpack_struct: {target_node}"
                )
            unpack_node = existing_edge.target.node_ref
        else:
            unpack_node = g.add_func("unpack_struct", struct=np)
        return unpack_node[self.field_name]

    def source_graph(self) -> "TierkreisGraph":
        return _source_graph(self.src)


def __unpack_nodeport(self: NodePort, field_name: str) -> Unpack:
    return Unpack(self, field_name)


NodePort.__getitem__ = __unpack_nodeport  # type: ignore


def _arg_str(args: Dict[str, "TierkreisType"], order: Iterable[str]) -> str:
    return ", ".join(f"{chalk.yellow(port)}: {args[port]}" for port in order)


# can be inlined inside Function when tksl removed
def _func_sig(name: str, func: FunctionDeclaration):
    graph_type = cast("GraphType", TypeScheme.from_proto(func.type_scheme).body)
    irest = graph_type.inputs.rest
    orest = graph_type.outputs.rest
    irest = f", {chalk.yellow('#')}: {irest}" if irest else ""
    orest = f", {chalk.yellow('#')}: {orest}" if orest else ""
    return (
        f"{chalk.bold.blue(name)}"
        f"({_arg_str(graph_type.inputs.content, func.input_order)}{irest})"
        f" -> ({_arg_str(graph_type.outputs.content, func.output_order)}{orest})"
    )


class Function(_CallAddNode):
    f: FunctionDeclaration
    name: FunctionName

    def __init__(self, f: FunctionDeclaration, name: FunctionName):
        self.f = f
        self.name = name
        super().__init__(FunctionNode(name), f.input_order, f.output_order)

    def signature_string(self) -> str:
        return _func_sig(self.name.name, self.f)


class Namespace(Mapping[str, "Namespace"]):
    @overload
    def __init__(self, args: Signature, /):
        ...

    @overload
    def __init__(self, args: SigNamespace, *, _prefix: list[str]):
        """For internal use only."""
        ...

    def __init__(self, args: Union[Signature, SigNamespace], **kwargs: list[str]):
        if isinstance(args, Signature):
            namespace = args.root
            prefix = []
        else:
            namespace = args
            prefix = kwargs["_prefix"]
        for name, ndef in namespace.functions.items():
            # allows auto completion of function names in Jupyter environment
            setattr(self, name, Function(ndef, FunctionName(name, prefix)))
        self.__subspaces: Mapping[str, "Namespace"] = {
            name: Namespace(ns, _prefix=prefix + [name])
            for name, ns in namespace.subspaces.items()
        }

    def __getattr__(
        self, attr_name: str
    ) -> Function:  # This is here just to placate mypy
        raise AttributeError(attr_name)

    def __getitem__(self, __k: str) -> "Namespace":
        return self.__subspaces[__k]

    def __len__(self) -> int:
        return self.__subspaces.__len__()

    def __iter__(self) -> Iterator[str]:
        return self.__subspaces.__iter__()
