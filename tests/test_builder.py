from dataclasses import astuple, dataclass
from typing import TYPE_CHECKING, Any, Callable, Optional, Tuple, no_type_check

import pytest

from tierkreis import TierkreisGraph
from tierkreis.core import Labels
from tierkreis.core.protos.tierkreis.graph import Graph
from tierkreis.core.tierkreis_graph import (
    ConstNode,
    FunctionNode,
    GraphValue,
    TierkreisGraph,
)
from tierkreis.core.tierkreis_struct import TierkreisStruct
from tierkreis.core.types import IntType, MapType, StringType, VecType
from tierkreis.core.utils import map_vals
from tierkreis.core.values import (
    BoolValue,
    FloatValue,
    IntValue,
    MapValue,
    PairValue,
    StringValue,
    StructValue,
    TierkreisValue,
    TierkreisVariant,
    VariantValue,
    VecValue,
)
from tierkreis.frontend.builder import (
    Box,
    Break,
    Case,
    Const,
    Continue,
    Copyable,
    Else,
    If,
    IfElse,
    Input,
    Match,
    Namespace,
    Output,
    Tag,
    ValueSource,
    _GraphDecoratorType,
    closure,
    current_graph,
    graph,
    loop,
)
from tierkreis.frontend.runtime_client import RuntimeClient, RuntimeSignature

if TYPE_CHECKING:
    from tierkreis.core.tierkreis_graph import NodePort, NodeRef
    from tierkreis.frontend.builder import StablePortFunc

# This avoids errors on every call to a decorated _GraphDef
# pylint: disable=no-value-for-parameter


def _auto_name_map(index_map: dict[int, int]) -> dict[str, str]:
    return {f"NewNode({key})": f"NewNode({val})" for key, val in index_map.items()}


def _compare_graphs(
    first: TierkreisGraph,
    second: TierkreisGraph,
    node_map: Optional[dict[str, str]] = None,
) -> None:
    f_proto = first.to_proto()
    s_proto = second.to_proto()
    if node_map:
        new_nodes = {
            node_map.get(name, name): node for name, node in s_proto.nodes.items()
        }
        new_edges = []
        for edge in s_proto.edges:
            edge.node_from = node_map.get(edge.node_from, edge.node_from)
            edge.node_to = node_map.get(edge.node_to, edge.node_to)
            new_edges.append(edge)
        s_proto = Graph(new_nodes, new_edges)
    assert f_proto.nodes == s_proto.nodes
    # jsonify type annotations for ease of comparison
    for proto in (f_proto, s_proto):
        for e in proto.edges:
            if e.edge_type is not None:
                # hack, edge_type should be a TierkreisType
                # but we are converting to string for compairson
                e.edge_type = e.edge_type.to_json()  # type: ignore
    edge_set = lambda edge_list: set(map(astuple, edge_list))
    assert edge_set(f_proto.edges) == edge_set(s_proto.edges)


def _vecs_graph() -> TierkreisGraph:
    tg = TierkreisGraph()
    con = tg.add_const([2, 4])
    tg.set_outputs(value=con)
    tg.annotate_output(Labels.VALUE, VecType(IntType()))

    return tg


@pytest.fixture()
def _vecs_graph_builder() -> TierkreisGraph:
    @graph()
    def g() -> Output[VecValue[IntValue]]:
        return Output(Const([2, 4]))

    return g()


def _structs_graph() -> TierkreisGraph:
    tg = TierkreisGraph()
    factory = tg.add_func(
        "builtin/make_struct",
        **map_vals(dict(height=12.3, name="hello", age=23), tg.add_const),
    )
    sturct = tg.add_func("builtin/unpack_struct", struct=factory["struct"])

    tg.set_outputs(value=sturct["age"])
    tg.annotate_output("value", IntType())
    return tg


@pytest.fixture()
def _structs_graph_builder(bi) -> TierkreisGraph:
    @graph()
    def g() -> Output[IntValue]:
        st_node = bi.make_struct(height=Const(12.3), name=Const("hello"), age=Const(23))
        return Output(st_node["struct"]["age"])

    return g()


def _maps_graph() -> TierkreisGraph:
    tg = TierkreisGraph()
    mp_val = tg.add_func("builtin/remove_key", map=tg.input["mp"], key=tg.add_const(3))
    ins = tg.add_func(
        "builtin/insert_key",
        map=mp_val["map"],
        **map_vals(dict(key=5, val="bar"), tg.add_const),
    )

    tg.set_outputs(mp=ins["map"], vl=mp_val["val"])
    tg.annotate_input("mp", MapType(IntType(), StringType()))
    tg.annotate_output("mp", MapType(IntType(), StringType()))
    tg.annotate_output("vl", StringType())

    return tg


@pytest.fixture()
def _maps_graph_builder(bi) -> TierkreisGraph:
    @dataclass
    class Mapout(TierkreisStruct):
        mp: MapValue[IntValue, StringValue]
        vl: StringValue

    @graph()
    def g(mp: Input[MapValue[IntValue, StringValue]]) -> Output[Mapout]:
        mp, val = bi.remove_key(mp, Const(3))
        return Output(bi.insert_key(mp, Const(5), Const("bar")), val)

    return g()


def _tag_match_graph() -> TierkreisGraph:
    id_graph = TierkreisGraph()
    id_graph.set_outputs(value=id_graph.input[Labels.VALUE])

    tg = TierkreisGraph()
    in_v = tg.add_tag("foo", value=tg.add_const(4))
    m = tg.add_match(in_v, foo=tg.add_const(id_graph))
    e = tg.add_func("builtin/eval", thunk=m[Labels.THUNK])
    tg.set_outputs(value=e[Labels.VALUE])
    tg.annotate_output("value", IntType())

    return tg


@pytest.fixture()
def _tag_match_graph_builder(bi) -> TierkreisGraph:
    @graph()
    def g() -> Output[IntValue]:
        with Match(Tag("foo", Const(4))) as match:
            with Case("foo") as h1:
                Output(h1.var_value)
        return Output(match.nref)

    return g()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "builder,expected_gen,rename_map",
    [
        ("_vecs_graph_builder", _vecs_graph, {}),
        ("_structs_graph_builder", _structs_graph, {}),
        ("_maps_graph_builder", _maps_graph, {1: 2, 0: 1, 2: 0}),
        ("_tag_match_graph_builder", _tag_match_graph, {}),
    ],
)
async def test_builder_sample(
    builder: str,
    expected_gen: Callable[[], TierkreisGraph],
    rename_map: dict[int, int],
    client: RuntimeClient,
    bi,  # for some reason fails without this
    request,
) -> None:
    tg = request.getfixturevalue(builder)

    _compare_graphs(tg, expected_gen(), _auto_name_map(rename_map))

    tg = await client.type_check_graph(tg)


def _big_sample_builder(bi: Namespace) -> TierkreisGraph:
    def add2(x: ValueSource) -> Output[IntValue]:
        return Output(bi.iadd(x, Const(2)))

    def add5(x: ValueSource) -> Output[IntValue]:
        return Output(bi.iadd(x, Const(5)))

    @dataclass
    class Point(TierkreisStruct):
        p1: FloatValue
        p2: IntValue

    @graph()
    def struc_id(in_st: Input[StructValue[Point]]) -> Output[StructValue[Point]]:
        return Output(in_st)

    @graph()
    def func(v1: Input[IntValue], v2: Input[PairValue[IntValue, BoolValue]]) -> Output:

        fst, scd = bi.unpack_pair(v2)
        other_total = bi.iadd(fst, Const(3))
        dbl = double(bi)
        _pair_out = bi.make_pair(Const(True), Const("asdf"))
        total = Box(dbl)(v1)

        quadruple = bi.sequence(Const(dbl), Const(dbl))

        total4 = bi.eval(quadruple, value=total)

        with IfElse(scd) as ifelse:
            with If():
                add2(total4)
            with Else():
                add5(total4)

        @loop()
        def loop_def(initial_: Input[IntValue]) -> Output:
            initial = Copyable(initial_)
            with IfElse(bi.ilt(initial, Const(100))) as loop_ifelse:
                with If():
                    Continue(bi.iadd(initial, Const(5)))
                with Else():
                    Break(initial)
            return Output(loop_ifelse.nref)

        _disc = Box(struc_id())(Const(Point(FloatValue(4.3e1), IntValue(3))))

        return Output(o1=ifelse.nref, o2=loop_def(other_total))

    return func()


@pytest.mark.asyncio
async def test_bigexample(client: RuntimeClient, bi) -> None:
    tg = _big_sample_builder(bi)
    tg = await client.type_check_graph(tg)
    assert len(tg.nodes()) == 24
    for flag in (True, False):
        outputs = await client.run_graph(tg, v1=67, v2=(45, flag))
        outputs = await client.run_graph(tg, v1=67, v2=(45, flag))
        pyouts = {key: val.try_autopython() for key, val in outputs.items()}
        assert pyouts == {"o2": 103, "o1": 536 + (2 if flag else 5)}


@pytest.fixture()
async def sig(client: RuntimeClient) -> RuntimeSignature:
    return await client.get_signature()


@pytest.fixture(params=[False, True])
def dec_checks_types(request) -> bool:
    return request.param


@pytest.fixture()
def graph_dec(dec_checks_types: bool, sig: RuntimeSignature) -> _GraphDecoratorType:
    # provide decorators with and without incremental type checking
    return graph(sig=sig) if dec_checks_types else graph()


@pytest.fixture()
def bi(sig: RuntimeSignature) -> Namespace:
    return Namespace(sig["builtin"])


def double(bi) -> TierkreisGraph:
    @graph()
    def _double(value: Input[IntValue]) -> Output[IntValue]:
        return Output(bi.iadd(*bi.copy(value)))

    return _double()


@pytest.mark.asyncio
async def test_double(client: RuntimeClient, bi: Namespace):

    out = await client.run_graph(double(bi), value=10)
    assert out == {"value": IntValue(20)}


@pytest.mark.asyncio
async def test_copy(
    client: RuntimeClient, bi: Namespace, graph_dec: _GraphDecoratorType
):
    @dataclass
    class CopyOut(TierkreisStruct):
        a: Any
        b: IntValue

    @graph_dec
    def copy_graph(y: Input[IntValue]) -> Output[CopyOut]:
        return Output(*bi["copy"](y))

    out = await client.run_graph(copy_graph(), y=10)
    assert out == {"a": IntValue(10), "b": IntValue(10)}


@pytest.mark.asyncio
async def test_ifelse(
    client: RuntimeClient, bi: Namespace, graph_dec: _GraphDecoratorType
):
    # some graph type annotations are missing here to test this scenario
    @graph_dec
    def triple(y: Input[IntValue]):
        return Output(bi.imul(y, Const(3)))

    @graph_dec
    def ifelse(x: Input, flag) -> Output:
        bias = Const(1)
        with IfElse(flag) as sw:
            with If():
                Output(value=bi.iadd(bias, Box(triple())(x)))
            with Else():
                Output(value=x)
        return Output(sw.nref)

    tg = ifelse()

    outs = [await client.run_graph(tg, x=2, flag=f) for f in (True, False)]

    assert outs[0] == {"value": IntValue(7)}
    assert outs[1] == {"value": IntValue(2)}


def num_copies_discards(g: TierkreisGraph) -> Tuple[int, int]:
    nodefuncs = [
        n.function_name for n in g.nodes().values() if isinstance(n, FunctionNode)
    ]
    return nodefuncs.count("builtin/copy"), nodefuncs.count("builtin/discard")


def constant_subgraphs(g: TierkreisGraph) -> list[TierkreisGraph]:
    return [
        n.value.value
        for n in g.nodes().values()
        if isinstance(n, ConstNode) and isinstance(n.value, GraphValue)
    ]


@pytest.mark.asyncio
async def test_ifelse_copying(
    client: RuntimeClient,
    bi: Namespace,
    graph_dec: _GraphDecoratorType,
):
    @graph_dec
    def ifelse(x: Input[IntValue]) -> Output[IntValue]:
        pred = bi.eq(bi.imod(x, Const(2)), Const(0))
        x2 = Copyable(x)
        with IfElse(pred) as sw:
            with If():
                Output(value=bi.idiv(x2, Const(2)))
            with Else():
                Output(value=bi.iadd(bi.imul(x2, Const(3)), Const(1)))
        return Output(sw.nref)

    tg = ifelse()
    assert num_copies_discards(tg) == (1, 0)
    subgraphs = constant_subgraphs(tg)
    assert len(subgraphs) == 2
    for g in subgraphs:
        assert num_copies_discards(g) == (0, 0)

    outs = await client.run_graph(tg, x=10)
    assert outs == {"value": IntValue(5)}
    outs = await client.run_graph(tg, x=5)
    assert outs == {"value": IntValue(16)}


@pytest.mark.asyncio
async def test_copy_twice_inside_if(
    client: RuntimeClient, bi: Namespace, graph_dec: _GraphDecoratorType
):
    @graph_dec
    def ifelse(x: Input[IntValue], flag: Input[BoolValue]) -> Output[IntValue]:
        with IfElse(flag) as sw:
            with If():
                c = Copyable(x)  # Copy in inner graph
                Output(value=bi.imul(c, bi.iadd(c, Const(1))))
            with Else():
                Output(value=x)
        return Output(sw.nref)

    tg = ifelse()
    assert num_copies_discards(tg) == (0, 0)
    assert sorted(num_copies_discards(g) for g in constant_subgraphs(tg)) == sorted(
        [(1, 0), (0, 0)]
    )

    outs = {b: await client.run_graph(tg, x=3, flag=b) for b in [True, False]}
    assert outs[True] == {"value": IntValue(12)}
    assert outs[False] == {"value": IntValue(3)}


@pytest.mark.asyncio
async def test_copy_twice_from_outside_if(
    client: RuntimeClient, bi: Namespace, graph_dec: _GraphDecoratorType
):
    @graph_dec
    def ifelse(x: Input[IntValue], flag: Input[BoolValue]) -> Output[IntValue]:
        c = Copyable(x)  # This can only copy in outer graph
        with IfElse(flag) as sw:
            with If():
                # Use copy twice in inner graph, this is not allowed
                Output(value=bi.imul(c, bi.iadd(c, Const(1))))
            with Else():
                Output(value=c)
        return Output(sw.nref)

    with pytest.raises(ValueError, match="Already captured"):
        ifelse()


@pytest.mark.asyncio
async def test_loop(
    client: RuntimeClient, bi: Namespace, graph_dec: _GraphDecoratorType
):
    @graph_dec
    def loopyg() -> Output[FloatValue]:
        incr = Const(1)

        @loop()
        def loop_def(value: Input[IntValue]) -> Output:
            x1, x2 = bi.copy(value)

            @closure()
            def succ(x: Input[IntValue]) -> Output[IntValue]:
                return Output(value=bi.iadd(x, incr))

            with IfElse(bi.ilt(x1, Const(7))) as sw:
                with If():
                    Continue(succ(x2))
                with Else():
                    Break(bi.int_to_float(x2))
            return Output(sw.nref)

        return Output(loop_def(Const(0)))

    assert (await client.run_graph(loopyg())) == {"value": FloatValue(7.0)}


@pytest.mark.asyncio
async def test_match(
    client: RuntimeClient, bi: Namespace, graph_dec: _GraphDecoratorType
):
    @dataclass
    class _Vdict(TierkreisStruct):
        list: VecValue[FloatValue]
        pair: PairValue[FloatValue, FloatValue]

    @graph_dec
    def match(var: Input[VariantValue[_Vdict]]) -> Output:
        factor = Const(2.0)
        with Match(var) as match:
            with Case("list") as h1:
                lst, fst = bi.pop(h1.var_value)
                Output(bi.push(lst, bi.fmul(fst, factor)))
            with Case("pair") as h2:
                fst, scd = bi.unpack_pair(h2.var_value)
                Output(bi.push(bi.push(Const([]), bi.fmul(fst, factor)), scd))
        return Output(match.nref)

    tg = match()

    assert (await client.run_graph(tg, var=TierkreisVariant("pair", (1.0, 2.0)))) == {
        "value": VecValue(values=[FloatValue(value=2.0), FloatValue(value=2.0)])
    }
    assert (await client.run_graph(tg, var=TierkreisVariant("list", [1.0, 2.0]))) == {
        "value": VecValue(values=[FloatValue(value=1.0), FloatValue(value=4.0)])
    }


@pytest.fixture()
def _pair_builder(bi: Namespace, sig: RuntimeSignature) -> TierkreisGraph:
    @dataclass
    class Pair(TierkreisStruct):
        first: IntValue
        second: StringValue

    @graph(sig=sig)
    def main() -> Output[Pair]:
        return Output(*bi.unpack_pair(Const((2, "asdf"))))

    return main()


@pytest.fixture()
def _if_no_inputs(bi: Namespace, sig: RuntimeSignature) -> TierkreisGraph:
    @graph(sig=sig)
    def main(pred: Input[BoolValue]) -> Output[IntValue]:
        with IfElse(pred) as ifelse:
            with If():
                Output(Const(3))
            with Else():
                Output(Const(5))
        return Output(ifelse.nref)

    return main()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "builder,inputs,expected_outputs",
    [
        # ("_option_builder", {}, {"some": IntValue(30), "none": IntValue(-1)}),
        ("_pair_builder", {}, {"first": IntValue(2), "second": StringValue("asdf")}),
        ("_if_no_inputs", {"pred": BoolValue(True)}, {"value": IntValue(3)}),
        ("_if_no_inputs", {"pred": BoolValue(False)}, {"value": IntValue(5)}),
        # (
        #     "match_variant.tksl",
        #     {"expr": VariantValue("cst", IntValue(5)), "vv": IntValue(67)},
        #     {"res": IntValue(5)},
        # ),
        # (
        #     "match_variant.tksl",
        #     {"expr": VariantValue("var", StructValue({})), "vv": IntValue(4)},
        #     {"res": IntValue(4)},
        # ),
        # (
        #     "match_variant.tksl",
        #     {
        #         "expr": VariantValue(
        #             "sum", StructValue({"a": IntValue(5), "b": IntValue(3)})
        #         ),
        #         "vv": IntValue(99),
        #     },
        #     {"res": IntValue(8)},
        # ),
        # (
        #     "match_variant.tksl",
        #     {
        #         "expr": VariantValue(
        #             "prod", StructValue({"a": IntValue(5), "b": IntValue(3)})
        #         ),
        #         "vv": IntValue(99),
        #     },
        #     {"res": IntValue(15)},
        # ),
    ],
)
async def test_run_sample(
    client: RuntimeClient,
    builder: str,
    inputs: dict[str, TierkreisValue],
    expected_outputs: dict[str, TierkreisValue],
    bi,
    request,
) -> None:
    tg = request.getfixturevalue(builder)

    outputs = await client.run_graph(tg, **inputs)
    assert outputs == expected_outputs


@pytest.mark.asyncio
async def test_Copyable(
    bi, client: RuntimeClient, graph_dec: _GraphDecoratorType, dec_checks_types: bool
) -> None:
    ins_disc = int(dec_checks_types)

    @graph_dec
    def foo(a: Input[IntValue], b: Input[IntValue]) -> Output:
        assert num_copies_discards(current_graph()) == (0, 2)

        # Even without an explicit Copy, discards should be removed
        f = bi.iadd(a=a, b=b)
        assert num_copies_discards(current_graph()) == (0, ins_disc)

        a_squared_plus_ab = bi.imul(a=Copyable(a), b=f)
        assert num_copies_discards(current_graph()) == (1, ins_disc)

        b_plus_2a = bi.iadd(a=Copyable(a), b=Copyable(f))
        assert num_copies_discards(current_graph()) == (3, 2 * ins_disc)
        return Output(out=a_squared_plus_ab, res=b_plus_2a)

    outputs = await client.run_graph(foo(), a=2, b=3)
    assert outputs == {"out": IntValue(10), "res": IntValue(7)}


@pytest.mark.asyncio
async def test_unpacking(
    bi,
    client: RuntimeClient,
    sig: RuntimeSignature,
    graph_dec: _GraphDecoratorType,
    dec_checks_types: bool,
) -> None:
    def num_unpacks_discards() -> Tuple[int, int]:
        funcs = [
            getattr(n, "function_name", "") for n in current_graph().nodes().values()
        ]
        return funcs.count("builtin/unpack_struct"), funcs.count("builtin/discard")

    pn = Namespace(sig["python_nodes"])
    ins_disc = int(dec_checks_types)

    @graph_dec
    def foo(a: Input[FloatValue], b: Input[IntValue]) -> Output:
        f = bi.make_struct(foo=a, bar=b)
        id_: "NodeRef" = pn.id_py(value=f["struct"])
        sturct: "NodePort" = id_["value"]
        bi.discard(sturct)
        old_proto = current_graph().to_proto()

        foo: "StablePortFunc" = sturct["foo"]
        assert num_unpacks_discards() == (0, 1)
        assert current_graph().to_proto() == old_proto  # Nothing changed yet

        first = bi.id(foo)
        # Discard should be removed, but unpack node should be generated
        assert num_unpacks_discards() == (1, 2 * ins_disc)
        # Typechecking will add a discard on the other port of the unpack
        # assert num_unpacks_discards(
        #    await client.type_check_graph(current_graph())) == (1, 1)
        # Second struct component (bar) reuses same unpack node
        second = bi.iadd(a=sturct["bar"], b=Const(1))
        assert num_unpacks_discards() == (1, 2 * ins_disc)

        # Repeated uses of the same struct member need an explicit copy
        proto = current_graph().to_proto()
        with pytest.raises(ValueError, match="Already an edge from"):
            current_graph().add_edge(
                sturct["foo"].resolve(), current_graph().output["second"]
            )
        assert proto == current_graph().to_proto()  # Did nothing
        return Output(first=first, second=second)

    outputs = await client.run_graph(foo(), a=3.142, b=5)
    assert outputs == {"first": FloatValue(3.142), "second": IntValue(6)}


def num_copies_unpacks() -> Tuple[int, int]:
    funcs = [getattr(n, "function_name", "") for n in current_graph().nodes().values()]
    return funcs.count("builtin/copy"), funcs.count("builtin/unpack_struct")


def test_cant_unpack_original_after_copy(bi, graph_dec: _GraphDecoratorType) -> None:
    @graph_dec
    def foo(a: Input[StringValue], b: Input[FloatValue]) -> Output:
        sturct: NodePort = bi.make_struct(foo=a, bar=b)["struct"]

        bi.discard(sturct["foo"])
        assert num_copies_unpacks() == (0, 1)

        cp = Copyable(sturct)
        o: Output = Output(whole=cp)
        assert num_copies_unpacks() == (1, 1)

        proto = current_graph().to_proto()
        with pytest.raises(ValueError, match="Cannot unpack"):
            current_graph().add_edge(
                sturct["bar"].resolve(), current_graph().output["second"]
            )
        assert proto == current_graph().to_proto()  # Did nothing
        return o

    foo()


@pytest.mark.asyncio
async def test_can_unpack_copy_with_resolve(
    bi, client: RuntimeClient, graph_dec: _GraphDecoratorType
) -> None:
    @graph_dec
    def foo(a: Input[IntValue], b: Input[IntValue]) -> Output:
        sturct = bi.make_struct(foo=a, bar=b)["struct"]

        s = bi.iadd(a=sturct["foo"], b=sturct["bar"])
        assert num_copies_unpacks() == (0, 1)

        cp = Copyable(sturct).resolve()

        o: Output = Output(sum=s, product=bi.imul(a=cp["foo"], b=cp["bar"]))
        assert num_copies_unpacks() == (1, 2)
        return o

    outputs = await client.run_graph(foo(), a=3, b=4)
    assert outputs == {"sum": IntValue(7), "product": IntValue(12)}


@pytest.mark.asyncio
async def test_Copyable_fields(
    bi, client: RuntimeClient, graph_dec: _GraphDecoratorType
) -> None:
    @graph_dec
    def foo(a: Input[IntValue], b: Input[IntValue]) -> Output:
        sturct = bi.make_struct(foo=a, bar=b)["struct"]

        s = bi.iadd(a=sturct["foo"], b=sturct["bar"])
        assert num_copies_unpacks() == (0, 1)

        return Output(
            sum=s,
            product=bi.imul(a=Copyable(sturct["foo"]), b=Copyable(sturct["bar"])),
        )

    outputs = await client.run_graph(foo(), a=3, b=4)
    assert outputs == {"sum": IntValue(7), "product": IntValue(12)}


@pytest.mark.asyncio
async def test_unpacking_nested(
    client: RuntimeClient, graph_dec: _GraphDecoratorType
) -> None:
    @graph_dec
    def foo(arg: Input[Any]) -> Output:
        return Output(out=arg["outer"]["inner"])

    tg = foo()
    nested_val = FloatValue(42.0)
    argument: StructValue = StructValue(
        values={"outer": StructValue(values={"inner": nested_val})}
    )

    outputs = await client.run_graph(tg, arg=argument)
    assert outputs == {"out": nested_val}


@pytest.mark.asyncio
async def test_bad_annotations(graph_dec: _GraphDecoratorType) -> None:
    # each case should also generate a static type error without
    # the `no_type_check` decorator
    with pytest.raises(TypeError, match="return type"):

        @no_type_check
        @graph_dec
        def foo1(arg: Input[Any]) -> int:
            return Output(out=arg)

    with pytest.raises(TypeError, match="return type"):

        @no_type_check
        @graph_dec
        def foo2(arg: Input[Any]) -> Output[int]:
            return Output(out=arg)

    with pytest.raises(TypeError, match="Graph builder function arguments"):

        @no_type_check
        @graph_dec
        def foo3(arg: float) -> Output:
            return Output(out=arg)

    with pytest.raises(ValueError, match="Cannot convert"):

        @no_type_check
        @graph_dec
        def foo4(arg: Input[float]) -> Output:
            return Output(out=arg)