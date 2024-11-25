"""The builder module allows Tierkreis graphs to be constructed concisely using
decorated functions and context managers.
"""

import inspect
from abc import ABC, abstractmethod
from contextlib import AbstractContextManager
from contextvars import ContextVar, Token
from dataclasses import dataclass
from functools import cached_property
from itertools import count
from types import FrameType, TracebackType
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Iterable,
    Iterator,
    Mapping,
    Optional,
    Type,
    TypeVar,
    Union,
    cast,
    overload,
)

from yachalk import chalk

from tierkreis.core import Labels
from tierkreis.core.function import FunctionDeclaration, FunctionName
from tierkreis.core.signature import Namespace as SigNamespace
from tierkreis.core.signature import Signature
from tierkreis.core.tierkreis_graph import (
    BoxNode,
    ConstNode,
    FunctionNode,
    IncomingWireType,
    Location,
    MatchNode,
    NodePort,
    NodeRef,
    PortID,
    TagNode,
    TierkreisGraph,
    TierkreisNode,
    to_nodeport,
)
from tierkreis.core.type_errors import TierkreisTypeErrors
from tierkreis.core.type_inference import infer_graph_types
from tierkreis.core.types import TupleLabel, TypeScheme, UnionTag
from tierkreis.core.utils import graph_from_func, map_vals, rename_ports_graph
from tierkreis.core.values import (
    TierkreisValue,
)

if TYPE_CHECKING:
    from tierkreis.core.types import GraphType, TierkreisType


class PortFunc(ABC):
    """Magic for lazily creating nodes (and returning ports thereof)."""

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


def _debug_str() -> str:
    # unroll current stack until out of this file
    frm = cast(FrameType, inspect.currentframe())
    while frm.f_code.co_filename == __file__ and frm.f_back is not None:
        frm = cast(FrameType, frm.f_back)
    try:
        return f"Node added at: {frm.f_code.co_filename}:{frm.f_lineno}"
    finally:
        # as recommended in
        # https://docs.python.org/3/library/inspect.html#the-interpreter-stack
        del frm


__state: ContextVar["GraphBuilder"] = ContextVar("state")


class InvalidContext(Exception):
    """Expression not valid outside GraphBuilder `with` context"""


def current_builder() -> "GraphBuilder":
    """The current GraphBuilder context."""
    try:
        return __state.get()
    except LookupError as e:
        raise InvalidContext() from e


def current_graph() -> TierkreisGraph:
    """The current GraphBuilder's graph."""
    return current_builder().graph


def _set_state(bg: "GraphBuilder") -> Token["GraphBuilder"]:
    return __state.set(bg)


def _reset_state(tok: Token["GraphBuilder"]):
    return __state.reset(tok)


def _capture_label(idx: int) -> PortID:
    return f"_c{idx}"


@dataclass(frozen=True)
class _CaptureOutwards:
    # Utility to allow capturing values from inner scopes to outer scopes.

    source_graph: TierkreisGraph
    ref: NodeRef
    contained: Optional["_CaptureOutwards"] = None

    def capture(self, incoming: ValueSource) -> ValueSource:
        """Convert a ValueSource from the inner scope to the outer scope by adding an output to the inner."""

        if self.contained is not None:
            incoming = self.contained.capture(incoming)
        new_name = _capture_label(len(self.source_graph.outputs()))
        self.source_graph.set_outputs(**{new_name: _resolve(incoming)})
        return self.ref[new_name]


TGBuilder = TypeVar("TGBuilder", bound="GraphBuilder")


class GraphBuilder(AbstractContextManager):
    """Builder context that maintains a graph state and allows adding nodes
    within the context."""

    graph: TierkreisGraph
    inputs: list[str]
    outputs: list[str]
    inner_scopes: dict[TierkreisGraph, _CaptureOutwards]
    debug_info: dict[NodeRef, str]
    _state_token: Token["GraphBuilder"]

    def __init__(
        self,
        inputs: list[str] | None = None,
        outputs: list[str] | None = None,
        name: str = "",
        debug: bool = True,
    ) -> None:
        """Create a new GraphBuilder context.

        Args:
            inputs: Optional list of input port names, defaults to None (i.e. the empty list).
            outputs: Optional list of output port names, defaults to None (i.e. the empty list).
            name: _description_. Name the graph being built.
            debug: _description_. Whether to store debug info while building..
        """
        self.graph = TierkreisGraph(name)
        self.inputs = inputs or []
        self.outputs = outputs or []
        self.inner_scopes = {}
        self.graph.input_order.extend(self.inputs)
        self.debug_info = {self.graph.input: _debug_str()} if debug else {}

    def input(self, name: str) -> NodePort:
        """Get a port from the input node by name."""
        if name in self.inputs:
            return self.graph.input[name]
        raise RuntimeError("Input not declared.")

    def __enter__(self: TGBuilder) -> TGBuilder:
        self._state_token = _set_state(self)
        return self

    def __exit__(
        self,
        __exc_type: Optional[Type[BaseException]],
        __exc_value: Optional[BaseException],
        __traceback: Optional[TracebackType],
    ) -> Optional[bool]:
        _reset_state(self._state_token)
        return None

    def _inner_capture(self, incoming: ValueSource) -> Optional[ValueSource]:
        source_graph = _source_graph(incoming)
        if source_graph is self.graph:
            return incoming
        inner_scope = self.inner_scopes.get(source_graph)
        if inner_scope is not None:
            return inner_scope.capture(incoming)
        return None

    def capture(
        self, incoming: ValueSource, allow_existing: bool = False
    ) -> ValueSource:
        """Capture an input from an outer scope."""
        if (ret_val := self._inner_capture(incoming)) is None:
            raise InvalidContext(
                f"ValueSource {incoming} does not belong to current graph."
            )
        return ret_val

    def _add_edges(
        self,
        nr: NodeRef,
        /,
        **incoming_wires: ValueSource,
    ) -> None:
        for tgt_port, vs in incoming_wires.items():
            src = _resolve(self.capture(vs))
            self.graph.add_edge(src, nr[tgt_port])

    def add_node_to_graph(
        self,
        _tk_node: TierkreisNode,
        /,
        **incoming_wires: ValueSource,
    ) -> NodeRef:
        """Add a node to the graph and connect incoming wires, which are
        specified via keyword arguments."""
        nr = self.graph.add_node(_tk_node)
        self._add_edges(nr, **incoming_wires)
        if self.debug_info:
            self.debug_info[nr] = _debug_str()
        return nr

    def set_graph_outputs(self, **incoming_wires: ValueSource) -> None:
        """Set the outputs of the graph by specifying incoming wires as keyword arguments."""
        if len(self.graph.outputs()) != 0:
            raise RuntimeError("Outputs set multiple times for same graph.")
        self._add_edges(self.graph.output, **incoming_wires)

    def type_check(self, sig: Signature) -> TierkreisGraph:
        """Type check a graph against a provided signature and return a new graph with
        type annotations. Throws an exception if  `typecheck` optional
        dependencies not installed)."""
        try:
            return infer_graph_types(self.graph, sig)
        except TierkreisTypeErrors as te:
            raise te.with_debug(self.debug_info) from None


class CaptureBuilder(GraphBuilder):
    """Graph builder for closures which capture inputs from outer scopes."""

    captured: dict[ValueSource, PortID]

    def __init__(
        self,
        inputs: list[str] | None = None,
        outputs: list[str] | None = None,
        name: str = "",
        debug: Optional[bool] = None,
    ) -> None:
        bool_debug = bool(current_builder().debug_info) if debug is None else debug
        super().__init__(inputs, outputs, name, bool_debug)

        self.captured = {}

    def capture(
        self, incoming: ValueSource, allow_existing: bool = False
    ) -> ValueSource:
        """Capture input from an outer scope, wiring it through the input
        node.
        """
        if (valsrc := self._inner_capture(incoming)) is not None:
            return valsrc
        if incoming in self.captured and not allow_existing:
            # This would generate two wires from the same NodePort
            raise ValueError(f"Already captured {incoming} as input to {self.graph}")
        in_name = self.captured.setdefault(incoming, _capture_label(len(self.captured)))
        return self.graph.input[in_name]

    def __exit__(
        self,
        __exc_type: Optional[Type[BaseException]],
        __exc_value: Optional[BaseException],
        __traceback: Optional[TracebackType],
    ) -> Optional[bool]:
        super().__exit__(__exc_type, __exc_value, __traceback)
        if not any((__exc_type, __exc_value, __traceback)):
            current_builder().debug_info.update(self.debug_info)
        return None


def _partial_thunk(
    thunk: Union[GraphBuilder, NodePort], captured: dict[ValueSource, PortID]
) -> NodePort:
    # add the thunk as constant to the current graph and partial up
    bg = current_builder()
    thunk_port: NodePort = (
        Const(thunk.graph) if isinstance(thunk, GraphBuilder) else thunk
    )
    if captured:
        return bg.add_node_to_graph(
            FunctionNode(FunctionName("partial")),
            thunk=thunk_port,
            **{k: v for v, k in captured.items()},
        )[Labels.VALUE]
    return thunk_port


T = TypeVar("T")


def Const(
    val: Any,
    type_: Type | None = None,
) -> NodePort:
    """Add a constant value to the graph. If a type is provided, it will be used
    in the conversion, otherwise the type will be inferred from the value."""
    if isinstance(val, LazyGraph):
        val = val.graph
    n = current_builder().add_node_to_graph(
        ConstNode(TierkreisValue.from_python(val, type_))
    )
    return n[Labels.VALUE]


def UnionConst(val: Any) -> NodePort:
    """Add a constant as a variant value tagged by its type, to be used
    with `Union` type annotations.
    """
    union_tag = UnionTag.value_type_tag(val)
    return Tag(union_tag, Const(val))


@dataclass(frozen=True)
class _CallAddNode:
    node: TierkreisNode
    input_order: list[str]
    output_order: list[str]

    def __call__(self, *args: ValueSource, **kwds: ValueSource) -> NodeRef:
        bg = current_builder()
        kwds = _combine_args_with_kwargs(self.input_order, *args, **kwds)

        n = bg.add_node_to_graph(self.node, **kwds)
        return NodeRef(n.idx, n.graph, self.output_order)


class Scope(CaptureBuilder, ABC):
    """Build a sub graph to be executed at a specific `Location`."""

    location: Location

    def __init__(self, location: Union[str, Location] = Location([])):
        if isinstance(location, str):
            self.location = Location(location.split("/"))
        else:
            self.location = location
        super().__init__()

    def __exit__(
        self,
        __exc_type: Optional[Type[BaseException]],
        __exc_value: Optional[BaseException],
        __traceback: Optional[TracebackType],
    ) -> None:
        super().__exit__(__exc_type, __exc_value, __traceback)

        if not any((__exc_type, __exc_value, __traceback)):
            graph = self.graph
            inputs = {v: k for k, v in self.captured.items()}
            node_ref = _build_box(graph, self.location, **inputs)
            for inner_graph, captured in self.inner_scopes.items():
                current_builder().inner_scopes[inner_graph] = _CaptureOutwards(
                    graph, node_ref, captured
                )
            current_builder().inner_scopes[graph] = _CaptureOutwards(graph, node_ref)


def Tag(tag: str, value: ValueSource) -> NodePort:
    """Add a tag node to the graph, tagging the value with the provided tag
    string and producing a :class:`~tierkreis.core.values.VariantValue` from the output port.
    """
    return current_builder().add_node_to_graph(TagNode(tag), value=value)[Labels.VALUE]


class Output(NodeRef):
    """Set the outputs of a graph to the provided values. Return this object
    when terminating a graph building context. Positional arguments are mapped to any output
    names annotated on the graph being built, keyword arguments are used to
    explicitly set outputs.
    """

    def __init__(self, *args: ValueSource, **kwargs: ValueSource) -> None:
        s = current_builder()

        g = s.graph

        if len(args) == 1 and len(kwargs) == 0:
            kwargs = {Labels.VALUE: args[0]}
        else:
            kwargs = _combine_args_with_kwargs(s.outputs, *args, **kwargs)

        s.set_graph_outputs(**kwargs)
        for o in kwargs:
            g.output_order.append(o)

        super().__init__(g.output.idx, g)


class _LoopOutput(Output):
    def __init__(self, loopout: ValueSource) -> None:
        super().__init__(value=loopout)


class Continue(_LoopOutput):
    """Exit the current iteration of a loop and continue to the next with the
    provided output.
    """

    def __init__(self, loopout: ValueSource) -> None:
        super().__init__(Tag(Labels.CONTINUE, loopout))


class Break(_LoopOutput):
    """Exit the loop with the provided output."""

    def __init__(self, loopout: ValueSource) -> None:
        super().__init__(Tag(Labels.BREAK, loopout))


def _input_port(port: PortID) -> NodePort:
    return current_builder().graph.input[port]


_GraphDef = Callable[..., Output]


def _get_input_names(f: _GraphDef) -> list[str]:
    return list(inspect.signature(f).parameters.keys())


@dataclass(frozen=True)
class LazyGraph:
    """Context to lazily build a graph from a decorated function. A graph is only
    built when the function is called.
    """

    _builder: Callable[[], TierkreisGraph]

    @cached_property
    def graph(self) -> TierkreisGraph:
        return self._builder()

    def __call__(self, *args: ValueSource, **kwargs: ValueSource) -> NodeRef:
        return self.graph(*args, **kwargs)

    def _repr_svg_(self) -> str:
        return getattr(self.graph, "_repr_svg_")()


_GraphDecoratorType = Callable[[_GraphDef], TierkreisGraph]
_LazyGraphDecoratorType = Callable[[_GraphDef], LazyGraph]


def lazy_graph(
    name: str | None = None,
    type_check_sig: Signature | None = None,
    output_order: list[str] | None = None,
    debug: bool = True,
) -> _LazyGraphDecoratorType:
    """Decorate a function to build a `TierkreisGraph` when it is called.

    Args:
        name: Optionally name the graph,
            defaults to None
        type_check_sig: If a type signature
            is provided, the graph will be type checked when built,
            defaults to None
        output_order: Optional list of
            output ports, inputs are inferred from function arguments,
            defaults to None
    """

    def decorator_graph(f: _GraphDef) -> LazyGraph:
        input_order = _get_input_names(f)
        # Use getattr as _GraphDef doesn't specify that it has a __name__
        graph_name = name or getattr(f, "__name__")
        # graph_name = name or f.__name__  # type: ignore  # the alternative

        def wrapper() -> TierkreisGraph:
            gb = GraphBuilder(input_order, output_order, name=graph_name, debug=debug)

            with gb as sub_build:
                f(*(_input_port(port) for port in input_order))

            return (
                sub_build.graph
                if type_check_sig is None
                else sub_build.type_check(type_check_sig)
            )

        return LazyGraph(wrapper)

    return decorator_graph


def graph(
    name: Optional[str] = None,
    type_check_sig: Optional[Signature] = None,
    output_order: list[str] | None = None,
    debug: bool = True,
) -> _GraphDecoratorType:
    """Convert a function into a `TierkreisGraph`. See `lazy_graph` for details.
    This function is equivalent except that the graph is built when the module is loaded and replaces
    the original function.
    """
    dec = lazy_graph(name, type_check_sig, output_order, debug)

    def decorator_graph(f: _GraphDef) -> TierkreisGraph:
        return dec(f).graph

    return decorator_graph


class Thunk(_CallAddNode, PortFunc):
    """Utility to call a thunk (a graph) as a function. Adds an eval node when called."""

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

    def resolve(self) -> NodePort:
        """Return a NodePort, creating nodes as necessary in source graph."""
        return _resolve(self.graph_src)

    def source_graph(self) -> TierkreisGraph:
        """The graph the port belongs to (or will)."""
        return _source_graph(self.graph_src)


def closure(
    name: Optional[str] = None,
    debug: bool = True,
    output_order: list[str] | None = None,
) -> Callable[[_GraphDef], Thunk]:
    """Decorator to build a closure `TierkreisGraph` inside a builder context.

    Args:
        name: Optionally name the closure,
            defaults to None
        output_order: Optional list of
            output ports, defaults to None
    """

    def decorator_graph(f: _GraphDef) -> Thunk:
        input_order = _get_input_names(f)

        # Use getattr as _GraphDef doesn't specify that it has a __name__
        graph_name = name or getattr(f, "__name__")
        # graph_name = name or f.__name__  # type: ignore  # the alternative

        gb = CaptureBuilder(input_order, output_order, name=graph_name, debug=debug)

        with gb as sub_build:
            f(*(_input_port(port) for port in input_order))
        return Thunk(_partial_thunk(sub_build, sub_build.captured), input_order, [])

    return decorator_graph


def loop(name: Optional[str] = None, debug: bool = True):
    """Decorator to build a loop body `TierkreisGraph` inside a builder context.
    Must have exactly one input argument, the loop variable.
    """

    def decorator_graph(f: _GraphDef):
        inps = _get_input_names(f)
        if len(inps) != 1:
            raise ValueError("Loop body graph can only have one input.")

        # the loop node has input port "value"
        # allow body definitions to use any input names and map it
        graph_name = name or getattr(f, "__name__")

        def wrapper(initial: ValueSource) -> NodePort:
            gb = CaptureBuilder(inps, None, name=graph_name, debug=debug)
            with gb as sub_build:
                f(_input_port(Labels.VALUE))

            loop_node = current_builder().add_node_to_graph(
                FunctionNode(FunctionName("loop")),
                body=_partial_thunk(sub_build, sub_build.captured),
                value=initial,
            )
            return loop_node[Labels.VALUE]

        return wrapper

    return decorator_graph


class If(CaptureBuilder):
    """Utility to build an if/else block, adds a `Match` node when called."""

    def __init__(self) -> None:
        super().__init__()
        self.graph.name = "if"
        Match._add_handler("if", self)


class Else(CaptureBuilder):
    """Utility to build an if/else block, adds a `Match` node when called."""

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
    __variant_handlers: ContextVar[dict[str, CaptureBuilder]] = ContextVar(
        "variant_handlers"
    )

    _token: Token[dict[str, CaptureBuilder]]
    nref: NodeRef

    @classmethod
    def _get_handlers(cls) -> dict[str, CaptureBuilder]:
        return cls.__variant_handlers.get()

    def __enter__(self) -> "_CaseScope":
        super().__enter__()
        self._token = self.__variant_handlers.set({})
        return self

    @classmethod
    def _add_handler(cls, tag: str, handler: CaptureBuilder):
        handlers = cls.__variant_handlers.get()
        if tag in handlers:
            raise DuplicateBlock(tag)
        handlers[tag] = handler

    @abstractmethod
    def _get_thunk(self) -> NodePort: ...

    @abstractmethod
    def _intermediate_error(self) -> IntermediateNodes: ...

    def __exit__(
        self,
        __exc_type: Optional[Type[BaseException]],
        __exc_value: Optional[BaseException],
        __traceback: Optional[TracebackType],
    ) -> None:
        super().__exit__(__exc_type, __exc_value, __traceback)

        if not any((__exc_type, __exc_value, __traceback)):
            # do not perform graph building if error

            if self.graph.n_nodes != 2:
                raise self._intermediate_error()
            handlers = self.__variant_handlers.get()
            for h in handlers.values():
                current_builder().debug_info.update(h.debug_info)

            thunk_port = self._get_thunk()
            partial_inps = _combine_captures(list(handlers.values()))
            thunk_port = _partial_thunk(thunk_port, partial_inps)

            self.nref = current_builder().add_node_to_graph(
                FunctionNode(FunctionName("eval")),
                thunk=thunk_port,
            )
        self.__variant_handlers.reset(self._token)


class Match(_CaseScope):
    """Pattern match on a variant value by providing a `Case` for each variant."""

    variant_value: ValueSource

    def __init__(self, variant_value: ValueSource):
        super().__init__()
        self.variant_value = variant_value

    def _get_thunk(self) -> NodePort:
        handlers = _CaseScope._get_handlers()
        bg = current_builder()
        return bg.add_node_to_graph(
            MatchNode(),
            variant_value=self.variant_value,
            **map_vals(handlers, lambda x: Const(x.graph)),
        )[Labels.THUNK]

    def _intermediate_error(self) -> IntermediateNodes:
        return IntermediateNodes(
            "Graph building operations outside Case blocks not allowed in Match block."
        )


class Case(CaptureBuilder):
    """Define a graph to handle a specific variant in a `Match` block."""

    var_value: NodePort

    def __init__(self, tag: str) -> None:
        super().__init__()
        self.graph.name = tag
        Match._add_handler(tag, self)

        self.var_value = self.graph.input[Labels.VALUE]


class IfElse(_CaseScope):
    """Define an if/else block. Must contain exactly one `If` block and exactly one `Else` blocks."""

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
            pred=self.predicate,
            if_true=Const(handlers["if"].graph),
            if_false=Const(handlers["else"].graph),
        )[Labels.VALUE]

    def _intermediate_error(self) -> IntermediateNodes:
        return IntermediateNodes(
            "Graph building operations outside"
            " If/Else blocks not allowed in IfElse block."
        )


def _combine_captures(thunks: list[CaptureBuilder]) -> dict[ValueSource, PortID]:
    """Given a list of thunks with captured inputs, remove their existing input
    names, common up any shared sources (up to == equality), and add all those
    inputs to all graphs, discarding any unused.
    """
    old_names = frozenset([v for bg in thunks for v in bg.captured.values()])
    # Generate a sparsely numbered list of names that won't conflict:
    names = filter(lambda x: x not in old_names, map(_capture_label, count()))
    # Assign new names in deterministic order of thunks and captures in each
    combined_inputs: dict[ValueSource, str] = {
        vs: next(names) for bg in thunks for vs in bg.captured
    }  # Duplicate ValueSources overwrite earlier entries, making even sparser.
    for vs, name in combined_inputs.items():
        for bg in thunks:
            if in_name := bg.captured.get(vs):
                in_edge = bg.graph.out_edge_from_port(bg.graph.input[in_name])
                assert in_edge is not None
                bg.graph._graph.remove_edge(*in_edge.to_edge_handle())
                bg.graph.add_edge(bg.graph.input[name], in_edge.target)
            else:
                bg.graph.discard(bg.graph.input[name])

    return combined_inputs


def _combine_args_with_kwargs(
    expected: Iterable[str], *args: ValueSource, **kwargs: ValueSource
) -> dict[str, ValueSource]:
    pos_args = dict(zip(expected, args))
    if ints := set(kwargs).intersection(pos_args):
        raise RuntimeError(f"Arguments specified positionally and in keywords: {ints}")
    kwargs.update(pos_args)
    return kwargs


class Copyable(PortFunc):
    """Inserts a copy of an underlying ValueSource whenever an outgoing edge is added
    unless there are *no* existing uses of the underlying ValueSource
    (=> the wire is routed from the underlying ValueSource)
    """

    np: NodePort

    def __init__(self, src: ValueSource):
        builder = current_builder()
        while isinstance(src, Copyable) and _source_graph(src) == builder.graph:
            # Simplify if we call Copyable on a ValueSource twice
            self = src
        self.np = _resolve(builder.capture(src, allow_existing=True))

    def resolve(self) -> NodePort:
        g = self.source_graph()
        existing_edge = g.out_edge_from_port(self.np)
        if existing_edge is None:
            return self.np
        g._graph.remove_edge(*existing_edge.to_edge_handle())
        c1, c2 = g.copy_value(self.np)
        g.add_edge(c1, existing_edge.target, existing_edge.type_)
        return c2

    def source_graph(self) -> "TierkreisGraph":
        return self.np.node_ref.graph


@dataclass(frozen=True)
class Unpack(StablePortFunc):
    """Utility class representing an unpacked field of a struct."""

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
    """A Tierkreis function - i.e. provided by a worker, or a builtin."""

    f: FunctionDeclaration
    name: FunctionName

    def __init__(self, f: FunctionDeclaration, name: FunctionName):
        self.f = f
        self.name = name
        super().__init__(FunctionNode(name), f.input_order, f.output_order)

    def signature_string(self) -> str:
        return _func_sig(self.name.name, self.f)

    def to_graph(
        self,
        input_map: Optional[dict[str, str]] = None,
        output_map: Optional[dict[str, str]] = None,
    ) -> TierkreisGraph:
        return graph_from_func(self.name, self.f, input_map, output_map)

    def __str__(self) -> str:
        return self.signature_string()


class Namespace(Mapping[str, "Namespace"]):
    """Namespace of functions and sub-namespaces."""

    @overload
    def __init__(self, args: Signature, /): ...

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


def _rename_ports(
    thunk: ValueSource, map_old_to_new: dict[str, str], is_inputs: bool
) -> NodePort:
    bg = current_builder()
    rename_g = Const(rename_ports_graph(map_old_to_new))
    f, s = (rename_g, thunk) if is_inputs else (thunk, rename_g)
    seq = bg.add_node_to_graph(
        FunctionNode(FunctionName("sequence")), first=f, second=s
    )

    return seq["sequenced"]


def RenameInputs(thunk: ValueSource, rename_map: dict[str, str]) -> NodePort:
    """Utility function to rename the inputs of a thunk (runtime graph value)."""
    return _rename_ports(thunk, {v: k for k, v in rename_map.items()}, True)


def RenameOutputs(thunk: ValueSource, rename_map: dict[str, str]) -> NodePort:
    """Utility to rename the outputs of a thunk (runtime graph value)."""
    return _rename_ports(thunk, rename_map, False)


def _build_box(
    g: TierkreisGraph, _tk_loc: Location, *args: ValueSource, **kwargs: ValueSource
) -> NodeRef:
    bx = _CallAddNode(
        BoxNode(g, _tk_loc),
        g.input_order,
        g.output_order,
    )
    return bx(*args, **kwargs)


def __graph_call__(
    self: TierkreisGraph, *args: ValueSource, **kwargs: ValueSource
) -> NodeRef:
    return _build_box(self, Location([]), *args, **kwargs)


def UnpackTuple(src: ValueSource, first_n: int) -> Iterator[NodePort]:
    """Unpack a struct containing python tuple fields, up to the `first_n` fields."""
    unpack_node = current_builder().add_node_to_graph(
        FunctionNode(FunctionName("unpack_struct")),
        struct=src,
    )

    return (unpack_node[TupleLabel.index_label(i)] for i in range(first_n))


def MakeTuple(*args: ValueSource) -> NodePort:
    """Make a struct from some values, treating them like a python tuple, with
    member position indices used to generate the field labels.
    """
    make_node = current_builder().add_node_to_graph(
        FunctionNode(FunctionName("make_struct")),
        **{TupleLabel.index_label(i): v for i, v in enumerate(args)},
    )
    return make_node["struct"]


# mypy is not happy with assignment to a method
setattr(TierkreisGraph, "__call__", __graph_call__)
