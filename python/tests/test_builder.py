from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, Tuple, cast

import pytest

from tierkreis.builder import (
    Break,
    Case,
    Const,
    Continue,
    Copyable,
    Else,
    If,
    IfElse,
    MakeTuple,
    Match,
    Namespace,
    NodePort,
    Output,
    Scope,
    Tag,
    UnpackTuple,
    ValueSource,
    closure,
    current_builder,
    current_graph,
    graph,
    lazy_graph,
    loop,
)
from tierkreis.client.runtime_client import RuntimeClient
from tierkreis.core import Labels
from tierkreis.core.signature import Signature
from tierkreis.core.tierkreis_graph import (
    BoxNode,
    ConstNode,
    FunctionNode,
    GraphValue,
    TierkreisGraph,
)
from tierkreis.core.types import (
    TierkreisPair,
)
from tierkreis.core.utils import map_vals, rename_ports_graph
from tierkreis.core.values import (
    BoolValue,
    FloatValue,
    IntValue,
    PairValue,
    StringValue,
    StructValue,
    TierkreisValue,
    TierkreisVariant,
    VecValue,
)
from tierkreis.pyruntime import PyRuntime

if TYPE_CHECKING:
    from tierkreis.builder import StablePortFunc
    from tierkreis.core.tierkreis_graph import NodePort, NodeRef


def _compare_graphs(
    first: TierkreisGraph,
    second: TierkreisGraph,
) -> bool:
    return first.to_proto() == second.to_proto()


def _vecs_graph() -> TierkreisGraph:
    tg = TierkreisGraph("g")
    con = tg.add_const([2, 4])
    tg.set_outputs(value=con)
    tg.output_order = [Labels.VALUE]
    return tg


@pytest.fixture()
def _vecs_graph_builder() -> TierkreisGraph:
    @graph()
    def g() -> Output:
        return Output(Const([2, 4]))

    return g


def _structs_graph() -> TierkreisGraph:
    tg = TierkreisGraph("g")
    factory = tg.add_func(
        "make_struct",
        **map_vals(dict(height=12.3, name="hello", age=23), tg.add_const),
    )
    struct = tg.add_func("unpack_struct", struct=factory["struct"])

    tg.set_outputs(value=struct["age"])
    tg.output_order = [Labels.VALUE]

    return tg


@pytest.fixture()
def _structs_graph_builder(bi: Namespace) -> TierkreisGraph:
    @graph()
    def g() -> Output:
        st_node = bi.make_struct(height=Const(12.3), name=Const("hello"), age=Const(23))
        return Output(st_node["struct"]["age"])

    return g


def _maps_graph() -> TierkreisGraph:
    tg = TierkreisGraph("g")
    mp_val = tg.add_func("remove_key", map=tg.input["mp"], key=tg.add_const(3))
    ins = tg.add_func(
        "insert_key",
        map=mp_val["map"],
        **map_vals(dict(key=5, val="bar"), tg.add_const),
    )

    tg.set_outputs(mp=ins["map"], vl=mp_val["val"])
    tg.input_order = ["mp"]
    tg.output_order = ["mp", "vl"]
    return tg


@pytest.fixture()
def _maps_graph_builder(bi: Namespace) -> TierkreisGraph:
    @graph(output_order=["mp", "vl"])
    def g(mp: ValueSource) -> Output:
        mp, val = bi.remove_key(mp, Const(3))
        return Output(bi.insert_key(mp, Const(5), Const("bar")), val)

    return g


def _tag_match_graph() -> TierkreisGraph:
    id_graph = TierkreisGraph("foo")
    id_graph.set_outputs(value=id_graph.input[Labels.VALUE])
    id_graph.output_order = [Labels.VALUE]

    tg = TierkreisGraph("g")
    in_v = tg.add_tag("foo", value=tg.add_const(4))
    m = tg.add_match(in_v, foo=tg.add_const(id_graph))
    e = tg.add_func("eval", thunk=m[Labels.THUNK])
    tg.set_outputs(value=e[Labels.VALUE])
    tg.output_order = [Labels.VALUE]

    return tg


@pytest.fixture()
def _tag_match_graph_builder(bi: Namespace) -> TierkreisGraph:
    @graph()
    def g() -> Output:
        with Match(Tag("foo", Const(4))) as match:
            with Case("foo") as h1:
                Output(h1.var_value)
        return Output(match.nref)

    return g


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "builder,expected_gen",
    [
        ("_vecs_graph_builder", _vecs_graph),
        ("_structs_graph_builder", _structs_graph),
        ("_maps_graph_builder", _maps_graph),
        ("_tag_match_graph_builder", _tag_match_graph),
    ],
)
async def test_builder_sample(
    builder: str,
    expected_gen: Callable[[], TierkreisGraph],
    client: RuntimeClient,
    bi: Namespace,  # for some reason fails without this
    request: pytest.FixtureRequest,
) -> None:
    tg = request.getfixturevalue(builder)
    assert tg.to_proto() == expected_gen().to_proto()
    # assert _compare_graphs(tg, expected_gen())
    if client.can_type_check:
        tg = await client.type_check_graph(tg)


def _big_sample_builder(bi: Namespace) -> TierkreisGraph:
    def add2(x: ValueSource):
        return Output(bi.iadd(x, Const(2)))

    def add5(x: ValueSource):
        return Output(bi.iadd(x, Const(5)))

    @dataclass
    class Point:
        p1: FloatValue
        p2: IntValue

    @graph()
    def struct_id(in_st: ValueSource) -> Output:
        return Output(in_st)

    @graph()
    def func(v1: ValueSource, v2: ValueSource) -> Output:
        fst, scd = UnpackTuple(v2, 2)
        other_total = bi.iadd(fst, Const(3))
        dbl = double(bi)
        _tuple_out = MakeTuple(Const(True), Const("asdf"))
        total = dbl(v1)

        quadruple = bi.sequence(Const(dbl), Const(dbl))

        total4 = bi.eval(quadruple, value=total)

        with IfElse(scd) as ifelse:
            with If():
                add2(total4)
            with Else():
                add5(total4)

        @loop()
        def loop_def(initial_):
            initial = Copyable(initial_)
            with IfElse(bi.ilt(initial, Const(100))) as loop_ifelse:
                with If():
                    Continue(bi.iadd(initial, Const(5)))
                with Else():
                    Break(initial)
            return Output(loop_ifelse.nref)

        _disc = struct_id(Const(Point(FloatValue(4.3e1), IntValue(3))))

        return Output(o1=ifelse.nref, o2=loop_def(other_total))

    return func


@pytest.mark.asyncio
async def test_bigexample(client: RuntimeClient, bi: Namespace) -> None:
    tg = _big_sample_builder(bi)
    if not client.can_type_check:
        pytest.skip()
    tg = await client.type_check_graph(tg)
    assert sum(1 for _ in tg.nodes()) == 24
    for flag in (True, False):
        outputs = await client.run_graph(tg, v1=67, v2=(45, flag))
        outputs = await client.run_graph(tg, v1=67, v2=(45, flag))
        pyouts = {key: val.try_autopython() for key, val in outputs.items()}
        assert pyouts == {"o2": 103, "o1": 536 + (2 if flag else 5)}


def double(bi: Namespace) -> TierkreisGraph:
    @graph()
    def _double(value: ValueSource) -> Output:
        return Output(bi.iadd(*bi.copy(value)))

    return _double


@pytest.mark.asyncio
async def test_double(client: RuntimeClient, bi: Namespace):
    out = await client.run_graph(double(bi), value=10)
    assert out == {"value": IntValue(20)}


@pytest.mark.asyncio
async def test_copy(client: RuntimeClient, bi: Namespace):
    @graph(output_order=["a", "b"])
    def copy_graph(y: ValueSource) -> Output:
        return Output(*bi.copy(y))

    out = await client.run_graph(copy_graph, y=10)
    assert out == {"a": IntValue(10), "b": IntValue(10)}


@pytest.mark.asyncio
async def test_ifelse(client: RuntimeClient, bi: Namespace):
    # some graph type annotations are missing here to test this scenario
    @graph()
    def triple(y: ValueSource) -> Output:
        return Output(bi.imul(y, Const(3)))

    @graph()
    def ifelse(x: ValueSource, flag: ValueSource) -> Output:
        bias = Const(1)
        with IfElse(flag) as sw:
            with If():
                Output(value=bi.iadd(bias, triple(x)))
            with Else():
                Output(value=x)
        return Output(sw.nref)

    outs = [await client.run_graph(ifelse, x=2, flag=f) for f in (True, False)]

    assert outs[0] == {"value": IntValue(7)}
    assert outs[1] == {"value": IntValue(2)}


def num_copies(g: TierkreisGraph) -> int:
    return sum(1 for n in g.nodes() if n.is_copy_node())


def constant_subgraphs(g: TierkreisGraph) -> list[TierkreisGraph]:
    return [
        n.value.value
        for n in g.nodes()
        if isinstance(n, ConstNode) and isinstance(n.value, GraphValue)
    ]


@pytest.mark.asyncio
async def test_ifelse_copying(
    client: RuntimeClient,
    bi: Namespace,
):
    @graph()
    def ifelse(x: ValueSource) -> Output:
        pred = bi.eq(bi.imod(x, Const(2)), Const(0))
        x2 = Copyable(x)
        with IfElse(pred) as sw:
            with If():
                Output(value=bi.idiv(x2, Const(2)))
            with Else():
                Output(value=bi.iadd(bi.imul(x2, Const(3)), Const(1)))
        return Output(sw.nref)

    assert num_copies(ifelse) == 1
    subgraphs = constant_subgraphs(ifelse)
    assert len(subgraphs) == 2
    for g in subgraphs:
        assert num_copies(g) == 0

    outs = await client.run_graph(ifelse, x=10)
    assert outs == {"value": IntValue(5)}
    outs = await client.run_graph(ifelse, x=5)
    assert outs == {"value": IntValue(16)}


@pytest.mark.asyncio
async def test_copy_twice_inside_if(client: RuntimeClient, bi: Namespace):
    @graph()
    def ifelse(x: ValueSource, flag: ValueSource) -> Output:
        with IfElse(flag) as sw:
            with If():
                c = Copyable(x)  # Copy in inner graph
                Output(value=bi.imul(c, bi.iadd(c, Const(1))))
            with Else():
                Output(value=x)
        return Output(sw.nref)

    assert num_copies(ifelse) == 0
    assert sorted(num_copies(g) for g in constant_subgraphs(ifelse)) == sorted([1, 0])

    outs = {b: await client.run_graph(ifelse, x=3, flag=b) for b in [True, False]}
    assert outs[True] == {"value": IntValue(12)}
    assert outs[False] == {"value": IntValue(3)}


@pytest.mark.asyncio
async def test_copy_twice_from_outside_if(bi: Namespace):
    @lazy_graph()
    def ifelse(x: ValueSource, flag: ValueSource) -> Output:
        c = Copyable(x)  # This can only copy in outer graph
        with IfElse(flag) as sw:
            with If():
                # Use copy twice in inner graph, this is not allowed
                Output(value=bi.imul(c, bi.iadd(c, Const(1))))
            with Else():
                Output(value=c)
        return Output(sw.nref)

    with pytest.raises(ValueError, match="Already captured"):
        _ = ifelse.graph


@pytest.mark.asyncio
async def test_loop(client: RuntimeClient, bi: Namespace):
    @graph()
    def loopyg() -> Output:
        incr = Const(1)

        @loop()
        def loop_def(value):
            x1, x2 = bi.copy(value)

            @closure()
            def succ(x):
                return Output(value=bi.iadd(x, incr))

            with IfElse(bi.ilt(x1, Const(7))) as sw:
                with If():
                    Continue(succ(x2))
                with Else():
                    Break(bi.int_to_float(x2))
            return Output(sw.nref)

        return Output(loop_def(Const(0)))

    assert (await client.run_graph(loopyg)) == {"value": FloatValue(7.0)}


@pytest.mark.asyncio
async def test_match(client: RuntimeClient, bi: Namespace):
    @dataclass
    class _Vdict:
        list: VecValue[FloatValue]
        pair: PairValue[FloatValue, FloatValue]

    @graph()
    def match(var: ValueSource) -> Output:
        factor = Const(2.0)
        with Match(var) as match:
            with Case("list") as h1:
                lst, fst = bi.pop(h1.var_value)
                Output(bi.push(lst, bi.fmul(fst, factor)))
            with Case("pair") as h2:
                fst, scd = bi.unpack_pair(h2.var_value)
                Output(bi.push(bi.push(Const([]), bi.fmul(fst, factor)), scd))
        return Output(match.nref)

    assert (
        await client.run_graph(
            match, var=TierkreisVariant("pair", TierkreisPair(1.0, 2.0))
        )
    ) == {"value": VecValue(values=[FloatValue(value=2.0), FloatValue(value=2.0)])}
    assert (
        await client.run_graph(match, var=TierkreisVariant("list", [1.0, 2.0]))
    ) == {"value": VecValue(values=[FloatValue(value=1.0), FloatValue(value=4.0)])}


@pytest.fixture()
def _tuple_builder(bi: Namespace, sig: Signature) -> TierkreisGraph:
    @graph()
    def main() -> Output:
        return Output(
            **dict(zip(("first", "second"), UnpackTuple(Const((2, "asdf")), 2)))
        )

    return main


@pytest.fixture()
def _if_no_inputs(bi: Namespace, sig: Signature) -> TierkreisGraph:
    @graph()
    def main(pred: ValueSource) -> Output:
        with IfElse(pred) as ifelse:
            with If():
                Output(Const(3))
            with Else():
                Output(Const(5))
        return Output(ifelse.nref)

    return main


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "builder,inputs,expected_outputs",
    [
        ("_tuple_builder", {}, {"first": IntValue(2), "second": StringValue("asdf")}),
        ("_if_no_inputs", {"pred": BoolValue(True)}, {"value": IntValue(3)}),
        ("_if_no_inputs", {"pred": BoolValue(False)}, {"value": IntValue(5)}),
    ],
)
async def test_run_sample(
    client: RuntimeClient,
    builder: str,
    inputs: dict[str, TierkreisValue],
    expected_outputs: dict[str, TierkreisValue],
    bi: Namespace,
    request: pytest.FixtureRequest,
) -> None:
    tg = request.getfixturevalue(builder)

    outputs = await client.run_graph(tg, **inputs)
    assert outputs == expected_outputs


@pytest.mark.asyncio
async def test_Copyable(bi: Namespace, client: RuntimeClient) -> None:
    @graph()
    def foo(a: ValueSource, b: ValueSource) -> Output:
        assert num_copies(current_graph()) == 0

        # Even without an explicit Copy, discards should be removed
        f = bi.iadd(a=a, b=b)
        assert num_copies(current_graph()) == 0

        a_squared_plus_ab = bi.imul(a=Copyable(a), b=f)
        assert num_copies(current_graph()) == 1

        b_plus_2a = bi.iadd(a=Copyable(a), b=Copyable(f))
        assert num_copies(current_graph()) == 3
        return Output(out=a_squared_plus_ab, res=b_plus_2a)

    outputs = await client.run_graph(foo, a=2, b=3)
    assert outputs == {"out": IntValue(10), "res": IntValue(7)}


@pytest.mark.asyncio
async def test_unpacking(
    bi: Namespace,
    client: RuntimeClient,
    sig: Signature,
) -> None:
    def num_unpacks() -> int:
        return sum(1 for n in current_graph().nodes() if n.is_unpack_node())

    pn = bi["python_nodes"]

    @graph()
    def foo(a: ValueSource, b: ValueSource) -> Output:
        f = bi.make_struct(foo=a, bar=b)
        id_: "NodeRef" = pn.id_py(value=f["struct"])
        struct: "NodePort" = id_["value"]
        old_proto = current_graph().to_proto()

        foo: "StablePortFunc" = struct["foo"]
        assert num_unpacks() == 0
        assert current_graph().to_proto() == old_proto  # Nothing changed yet

        first = bi.id(foo)
        assert num_unpacks() == 1
        second = bi.iadd(a=struct["bar"], b=Const(1))
        assert num_unpacks() == 1

        # Repeated uses of the same struct member need an explicit copy
        proto = current_graph().to_proto()
        with pytest.raises(ValueError, match="Already an edge from"):
            current_graph().add_edge(
                struct["foo"].resolve(), current_graph().output["second"]
            )
        assert proto == current_graph().to_proto()  # Did nothing
        return Output(first=first, second=second)

    outputs = await client.run_graph(foo, a=3.142, b=5)
    assert outputs == {"first": FloatValue(3.142), "second": IntValue(6)}


def num_copies_unpacks() -> Tuple[int, int]:
    return (
        sum(1 for n in current_graph().nodes() if n.is_copy_node()),
        sum(1 for n in current_graph().nodes() if n.is_unpack_node()),
    )


def test_cant_unpack_original_after_copy(bi: Namespace) -> None:
    @graph()
    def foo(a: ValueSource, b: ValueSource) -> Output:
        struct: ValueSource = bi.make_struct(foo=a, bar=b)["struct"]

        bi.discard(struct["foo"])
        assert num_copies_unpacks() == (0, 1)

        cp = Copyable(struct)
        o: Output = Output(whole=cp)
        assert num_copies_unpacks() == (1, 1)

        proto = current_graph().to_proto()
        with pytest.raises(ValueError, match="Cannot unpack"):
            current_graph().add_edge(
                struct["bar"].resolve(), current_graph().output["second"]
            )
        assert proto == current_graph().to_proto()  # Did nothing
        return o


@pytest.mark.asyncio
async def test_can_unpack_copy_with_resolve(
    bi: Namespace, client: RuntimeClient
) -> None:
    @graph()
    def foo(a: ValueSource, b: ValueSource) -> Output:
        struct = bi.make_struct(foo=a, bar=b)["struct"]

        s = bi.iadd(a=struct["foo"], b=struct["bar"])
        assert num_copies_unpacks() == (0, 1)

        cp = Copyable(struct).resolve()

        o: Output = Output(sum=s, product=bi.imul(a=cp["foo"], b=cp["bar"]))
        assert num_copies_unpacks() == (1, 2)
        return o

    outputs = await client.run_graph(foo, a=3, b=4)
    assert outputs == {"sum": IntValue(7), "product": IntValue(12)}


@pytest.mark.asyncio
async def test_Copyable_fields(bi: Namespace, client: RuntimeClient) -> None:
    @graph()
    def foo(a: ValueSource, b: ValueSource) -> Output:
        struct = bi.make_struct(foo=a, bar=b)["struct"]

        s = bi.iadd(a=struct["foo"], b=struct["bar"])
        assert num_copies_unpacks() == (0, 1)

        return Output(
            sum=s,
            product=bi.imul(a=Copyable(struct["foo"]), b=Copyable(struct["bar"])),
        )

    outputs = await client.run_graph(foo, a=3, b=4)
    assert outputs == {"sum": IntValue(7), "product": IntValue(12)}


@pytest.mark.asyncio
async def test_unpacking_nested(client: RuntimeClient) -> None:
    @graph()
    def foo(arg: NodePort) -> Output:
        return Output(out=arg["outer"]["inner"])

    nested_val = FloatValue(42.0)
    argument: StructValue = StructValue(
        values={"outer": StructValue(values={"inner": nested_val})}
    )

    outputs = await client.run_graph(foo, arg=argument)
    assert outputs == {"out": nested_val}


def test_retry_secs(bi: Namespace) -> None:
    pn = bi["python_nodes"]

    @graph()
    def foo(arg: ValueSource) -> Output:
        return Output(res=pn.id_py(arg).with_retry_secs(2))

    (f,) = [n for n in foo.nodes() if isinstance(n, FunctionNode)]
    assert f.retry_secs == 2


@pytest.mark.skip_typecheck
@pytest.mark.asyncio
async def test_box_order(bi: Namespace, sig: Signature) -> None:
    @graph(type_check_sig=sig)
    def push_pair(lst: ValueSource, first: ValueSource, second: ValueSource) -> Output:
        first = Copyable(first)
        pair = bi.make_pair(first, second)
        return Output(lst=bi.push(lst, pair), first=first)

    assert push_pair.input_order == ["lst", "first", "second"]
    assert push_pair.output_order == ["lst", "first"]

    @graph(type_check_sig=sig)
    def test_g() -> Output:
        lst, i = push_pair(Const([]), Const(3), Const("hello"))
        return Output(one=lst, two=i)

    box_n_name = next(
        n for n, nod in enumerate(test_g.nodes()) if isinstance(nod, BoxNode)
    )
    box_ins = {
        p2: n1
        for n1, _, (_, p2) in test_g._graph.in_edges(box_n_name, keys=True)  # type: ignore
    }
    assert len(box_ins) == 3

    assert all(isinstance(test_g[n], ConstNode) for n in box_ins.values())
    assert isinstance(cast(ConstNode, test_g[box_ins["lst"]]).value, VecValue)
    assert isinstance(cast(ConstNode, test_g[box_ins["first"]]).value, IntValue)
    assert isinstance(cast(ConstNode, test_g[box_ins["second"]]).value, StringValue)

    box_outs = tuple(
        ports
        for _, _, ports in test_g._graph.out_edges(box_n_name, keys=True)  # type: ignore
    )
    assert len(box_outs) == 2

    assert ("first", "two") in box_outs
    assert ("lst", "one") in box_outs


@pytest.mark.asyncio
async def test_scope(bi: Namespace, client: RuntimeClient) -> None:
    @graph()
    def g() -> Output:
        with Scope():
            bi.discard(Const(3))
        assert len(current_builder().inner_scopes.values()) == 1
        return Output()

    if not client.can_type_check:
        pytest.skip()
    tc_graph = await client.type_check_graph(g)
    assert tc_graph.n_nodes == 3
    n = cast(
        BoxNode,
        next(filter(lambda x: isinstance(x, BoxNode), tc_graph.nodes())),
    )
    assert any([x.is_discard_node() for x in n.graph.nodes()])
    assert n.graph.inputs() == []
    assert n.graph.outputs() == []


@pytest.mark.asyncio
async def test_scope_capture_in(bi: Namespace, client: RuntimeClient) -> None:
    @graph()
    def g() -> Output:
        a = Const(3)
        with Scope():
            bi.discard(a)
        assert len(current_builder().inner_scopes.values()) == 1
        return Output()

    if not client.can_type_check:
        pytest.skip()
    tc_graph = await client.type_check_graph(g)
    assert tc_graph.n_nodes == 4
    n = cast(
        BoxNode,
        next(filter(lambda x: isinstance(x, BoxNode), tc_graph.nodes())),
    )
    assert any([x.is_discard_node() for x in n.graph.nodes()])
    assert n.graph.inputs() == ["_c0"]
    assert n.graph.outputs() == []


@pytest.mark.asyncio
async def test_scope_capture_out(bi: Namespace, client: RuntimeClient) -> None:
    @graph()
    def g() -> Output:
        with Scope():
            a = Const(3)
        assert len(current_builder().inner_scopes.values()) == 1
        bi.discard(a)
        return Output()

    if not client.can_type_check:
        pytest.skip()
    tc_graph = await client.type_check_graph(g)
    assert tc_graph.n_nodes == 4
    n = cast(
        BoxNode,
        next(filter(lambda x: isinstance(x, BoxNode), tc_graph.nodes())),
    )
    assert not any([x.is_discard_node() for x in n.graph.nodes()])
    assert n.graph.inputs() == []
    assert n.graph.outputs() == ["_c0"]


@pytest.mark.asyncio
async def test_nested_scopes(bi: Namespace, client: RuntimeClient) -> None:
    @graph()
    def g() -> Output:
        a = Const(3)
        with Scope():
            b = Const(2)
            c = bi.iadd(a, b)
            with Scope():
                d, e = bi.copy(c)
            assert len(current_builder().inner_scopes.values()) == 1
            with Scope():
                f = bi.iadd(d, Const(1))
                assert len(current_builder().inner_scopes.values()) == 0
            assert len(current_builder().inner_scopes.values()) == 2
        assert len(current_builder().inner_scopes.values()) == 3
        assert e.node_ref.graph in current_builder().inner_scopes
        h = bi.iadd(e, f)

        return Output(value=h)

    if not client.can_type_check:
        pytest.skip()
    tc_graph = await client.type_check_graph(g)
    assert tc_graph.n_nodes == 5
    n = cast(
        BoxNode,
        next(filter(lambda x: isinstance(x, BoxNode), tc_graph.nodes())),
    )
    assert any([isinstance(x, BoxNode) for x in n.graph.nodes()])
    assert n.graph.inputs() == ["_c0"]
    assert sorted(n.graph.outputs()) == ["_c0", "_c1"]


@pytest.mark.asyncio
async def test_copyable_capture_in(bi: Namespace, client: RuntimeClient) -> None:
    @graph()
    def g() -> Output:
        a = Copyable(Const(3))
        with Scope():
            bi.discard(a)
        with Scope():
            bi.discard(a)
        return Output()

    if not client.can_type_check:
        pytest.skip()
    tc_graph = await client.type_check_graph(g)
    assert tc_graph.n_nodes == 6
    assert any([n.is_copy_node() for n in tc_graph.nodes()])


@pytest.mark.asyncio
async def test_copyable_capture_out_once(bi: Namespace, client: RuntimeClient) -> None:
    @graph()
    def g() -> Output:
        with Scope():
            a = Copyable(Const(3))
        bi.discard(a)
        return Output()

    if not client.can_type_check:
        pytest.skip()
    tc_graph = await client.type_check_graph(g)
    assert tc_graph.n_nodes == 4
    assert not any([n.is_copy_node() for n in tc_graph.nodes()])
    assert any([isinstance(n, BoxNode) for n in tc_graph.nodes()])


@pytest.mark.asyncio
async def test_copyable_capture_out_copied(
    bi: Namespace, client: RuntimeClient
) -> None:
    @graph()
    def g() -> Output:
        with Scope():
            a = Copyable(Const(3))
            bi.discard(a)
        bi.discard(a)
        return Output()

    if not client.can_type_check:
        pytest.skip()
    tc_graph = await client.type_check_graph(g)
    assert tc_graph.n_nodes == 4
    assert not any([n.is_copy_node() for n in tc_graph.nodes()])
    assert any([isinstance(n, BoxNode) for n in tc_graph.nodes()])


@pytest.mark.asyncio
async def test_copyable_on_captured_input(bi: Namespace, client: RuntimeClient) -> None:
    @graph()
    def g() -> Output:
        a = Const(3)
        with Scope():
            b = Copyable(a)
            bi.discard(b)
        bi.discard(b)
        return Output()

    if not client.can_type_check:
        pytest.skip()
    tc_graph = await client.type_check_graph(g)
    assert tc_graph.n_nodes == 5
    assert not any([n.is_copy_node() for n in tc_graph.nodes()])
    assert any([isinstance(n, BoxNode) for n in tc_graph.nodes()])


@pytest.mark.asyncio
async def test_copyable_dont_use(bi: Namespace, client: RuntimeClient) -> None:
    @graph()
    def g() -> Output:
        a = Const(3)
        with Scope():
            b = Copyable(a)
        bi.discard(b)
        return Output()

    if not client.can_type_check:
        pytest.skip()
    tc_graph = await client.type_check_graph(g)
    assert tc_graph.n_nodes == 5
    assert not any([n.is_copy_node() for n in tc_graph.nodes()])
    assert any([isinstance(n, BoxNode) for n in tc_graph.nodes()])


@pytest.mark.asyncio
async def test_unpack_capture_in(bi: Namespace, client: RuntimeClient) -> None:
    @graph()
    def g() -> Output:
        a = Const(StructValue({"a": IntValue(1), "b": StringValue("hello")}))
        with Scope():
            bi.discard(a["a"])
        return Output()

    if not client.can_type_check:
        pytest.skip()
    tc_graph = await client.type_check_graph(g)
    assert tc_graph.n_nodes == 6
    assert any([n.is_unpack_node() for n in tc_graph.nodes()])
    assert any([isinstance(n, BoxNode) for n in tc_graph.nodes()])


@pytest.mark.asyncio
async def test_unpack_capture_out(bi: Namespace, client: RuntimeClient) -> None:
    @graph()
    def g() -> Output:
        with Scope():
            a = Const(StructValue({"a": IntValue(1), "b": StringValue("hello")}))
        bi.discard(a["a"])
        return Output()

    if not client.can_type_check:
        pytest.skip()
    tc_graph = await client.type_check_graph(g)
    assert tc_graph.n_nodes == 4
    assert not any([n.is_unpack_node() for n in tc_graph.nodes()])
    assert any([isinstance(n, BoxNode) for n in tc_graph.nodes()])


@pytest.mark.skip_typecheck
@pytest.mark.asyncio
async def test_parmap_builder(
    bi: Namespace, sig: Signature, pyruntime: PyRuntime
) -> None:
    client = pyruntime  # We expect to make this pass for Rust runtime too soon

    @lazy_graph()
    def const_vec() -> Output:
        return Output(vec=Const([]))

    @lazy_graph(type_check_sig=sig)
    def par_map_builder(f: ValueSource, ins: ValueSource) -> Output:
        """Returns a graph which when evaluated applies f to each value in inps
        and collates the results."""
        f = bi.parallel(f, Const(rename_ports_graph({"vec": "vec"})))
        f = bi.sequence(f, Const(bi.push.to_graph(input_map={"item": "out"})))

        @loop()
        def built(loop_dat):
            vec: ValueSource = Copyable(loop_dat["vec"])
            with IfElse(bi.eq(Const([]), vec)) as loop_ifelse:
                with If():
                    Break(loop_dat["big_g"])
                with Else():
                    vec, i = bi.pop(vec)

                    f_part = bi.partial(f, inp=i)

                    big_g = bi.sequence(loop_dat["big_g"], f_part)
                    Continue(bi.make_struct(vec=vec, big_g=big_g))
            return Output(loop_ifelse.nref)

        par_f = built(bi.make_struct(vec=ins, big_g=Const(const_vec)))

        return Output(par_f)

    @graph()
    def func(inp: ValueSource) -> Output:
        return Output(out=bi.imul(inp, Const(2)))

    ins = [2387, 123, 64]
    out = await client.run_graph(par_map_builder.graph, f=func, ins=ins)

    gv = out["value"]

    assert isinstance(gv, GraphValue)

    tg = gv.value

    @graph()
    def expected_graph() -> Output:
        ls: ValueSource = Const([])
        for v in reversed(ins):
            ls = bi.push(ls, bi.imul(Const(v), Const(2)))
        return Output(vec=ls)

    # tg contains some type info, but has never been fully type-checked.
    # expected_graph contains no type information.
    # For comparison, we must make the two contain the same type information.
    tg = await client.type_check_graph(tg)
    exp = await client.type_check_graph(expected_graph)
    tg.name = exp.name
    tg.output_order = ["vec"]
    assert _compare_graphs(tg, exp)
    out = await client.run_graph(tg)

    assert out["vec"].try_autopython() == [x * 2 for x in reversed(ins)]
