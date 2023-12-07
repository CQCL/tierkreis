import platform
import sys
from copy import deepcopy
from typing import TYPE_CHECKING, Iterator

import betterproto
import pytest

from tierkreis import TierkreisGraph
from tierkreis.builder import (
    Break,
    Const,
    Continue,
    Else,
    If,
    IfElse,
    Output,
    Scope,
    closure,
    graph,
    lazy_graph,
    loop,
)
from tierkreis.client import RuntimeClient, ServerRuntime
from tierkreis.core.function import FunctionDeclaration
from tierkreis.core.signature import Namespace, Signature
from tierkreis.core.tierkreis_graph import GraphValue, NodePort
from tierkreis.core.type_errors import TierkreisTypeErrors, UnifyError, UnknownFunction
from tierkreis.core.type_inference import infer_graph_types
from tierkreis.core.types import (
    FloatType,
    GraphType,
    IntType,
    PairType,
    Row,
    StarKind,
    TypeScheme,
    VarType,
)
from tierkreis.core.values import FloatValue, StructValue

if TYPE_CHECKING:
    from tierkreis.builder import Namespace as BuilderNS


@pytest.mark.asyncio
async def test_infer(client: RuntimeClient) -> None:
    # test when built with client types are auto inferred
    tg = TierkreisGraph()
    _, val1 = tg.copy_value(tg.add_const(3))
    tg.set_outputs(out=val1)
    if not client.can_type_check:
        pytest.skip()
    tg = await client.type_check_graph(tg)
    assert any(node.is_discard_node() for node in tg.nodes())

    assert isinstance(tg.get_edge(val1, NodePort(tg.output, "out")).type_, IntType)


@pytest.mark.asyncio
async def test_infer_errors(client: RuntimeClient) -> None:
    # build graph with two type errors
    tg = TierkreisGraph()
    node_0 = tg.add_const(0)
    node_1 = tg.add_const(1)
    tg.add_edge(node_0["value"], tg.input["illegal"])
    tg.set_outputs(out=node_1["invalid"])

    if not client.can_type_check:
        pytest.skip()

    with pytest.raises(
        TierkreisTypeErrors, match="There are extra inputs: {'illegal'}"
    ) as err1:
        await client.type_check_graph(tg)
    returned_errs = [err1.value.errors]
    if isinstance(client, ServerRuntime):
        # only server runtime type checks on run
        with pytest.raises(TierkreisTypeErrors) as err:
            await client.run_graph(tg)
        returned_errs.append(err.value.errors)
    for errs in returned_errs:
        assert len(errs) == 2
        assert all(isinstance(e, UnifyError) for e in errs)

        # TODO make type errors report in deterministic order
        locs = (e.proto_err.location for e in errs)

        locations = {
            betterproto.which_one_of(loc[1], "location")[0]: loc[1] for loc in locs
        }
        assert set(locations.keys()) == {"input", "node_idx"}
        assert locations["node_idx"].node_idx == node_1.idx


_foo_func = FunctionDeclaration(
    TypeScheme(
        {"a": StarKind()},
        [],
        GraphType(
            inputs=Row({"value": VarType("a")}, None),
            outputs=Row({"res": PairType(VarType("a"), IntType())}, None),
        ),
    ).to_proto(),
    "no docs",
    ["value"],
    ["res"],
)


@pytest.mark.skip_typecheck
def test_infer_graph_types():
    tg = TierkreisGraph()
    foo = tg.add_func("foo", value=tg.add_const(3))
    tg.set_outputs(out=foo["res"])
    with pytest.raises(TierkreisTypeErrors, match="Unknown function: foo") as err:
        infer_graph_types(tg, Signature.empty())
    assert len(err.value) == 1
    e = err.value.errors[0]
    assert isinstance(e, UnknownFunction)
    assert e.proto_err.location[-1].node_idx == foo.idx
    sig = Signature(
        root=Namespace(
            functions={"foo": _foo_func},
        ),
    )
    tg = infer_graph_types(tg, sig)
    out_type = tg.get_edge(NodePort(foo, "res"), NodePort(tg.output, "out")).type_
    assert out_type == PairType(IntType(), IntType())


@pytest.mark.skip_typecheck
@pytest.mark.asyncio
async def test_infer_graph_types_with_sig(client: RuntimeClient):
    # client is only used for signatures of builtins etc.
    sigs = await client.get_signature()

    tg = TierkreisGraph()
    mkp = tg.add_func(
        "make_pair",
        first=tg.input["in"],
        second=tg.add_const(3),
    )
    tg.set_outputs(val=mkp["pair"])

    # updates the graph wrapped by tg inplace
    tg._graph = infer_graph_types(tg, sigs)._graph
    in_type = tg.get_edge(NodePort(tg.input, "in"), NodePort(mkp, "first")).type_
    assert isinstance(in_type, VarType)
    out_type = tg.get_edge(NodePort(mkp, "pair"), NodePort(tg.output, "val")).type_
    assert out_type == PairType(in_type, IntType())


@pytest.mark.skip_typecheck
@pytest.mark.asyncio
async def test_infer_graph_types_with_inputs(
    client: RuntimeClient, idpy_graph: TierkreisGraph
):
    ns = Namespace(
        functions={"foo": _foo_func},
        subspaces={
            "python_nodes": (await client.get_signature()).root.subspaces[
                "python_nodes"
            ]
        },
    )
    funcs = Signature(
        root=ns,
    )
    tg = TierkreisGraph()
    foo = tg.add_func("foo", value=tg.input["inp"])
    tg.set_outputs(out=foo["res"])

    tg2 = deepcopy(tg)

    inputs: StructValue = StructValue({"inp": FloatValue(3.14)})
    tg, inputs_ = infer_graph_types(tg, funcs, inputs)
    assert inputs_ == inputs
    out_type = tg.get_edge(NodePort(foo, "res"), NodePort(tg.output, "out")).type_
    assert out_type == PairType(FloatType(), IntType())

    graph_inputs: StructValue = StructValue({"inp": GraphValue(idpy_graph)})
    with pytest.raises(TierkreisTypeErrors, match=r"Pair\[Float, Int\] | Float") as err:
        # Pass an argument inconsistent with the annotations now on tg
        infer_graph_types(tg, funcs, graph_inputs)

    assert len(err.value) == 1
    e = err.value.errors[0]
    assert isinstance(e, UnifyError)
    # TODO location sometimes
    assert betterproto.which_one_of(e.proto_err.location[-1], "location")[0] in (
        "input",
        "root",
    )
    # deep copy (above) has no annotations yet, so ok
    tg2, inputs_ = infer_graph_types(tg2, funcs, graph_inputs)
    out_type = tg2.get_edge(NodePort(foo, "res"), NodePort(tg2.output, "out")).type_
    assert isinstance(out_type, PairType) and out_type.second == IntType()
    assert isinstance(out_type.first, GraphType)
    argtypes, restypes = out_type.first.inputs, out_type.first.outputs
    assert argtypes.rest is restypes.rest is None
    assert len(argtypes.content) == len(restypes.content) == 1
    assert argtypes.content["id_in"] == restypes.content["id_out"]
    assert isinstance(argtypes.content["id_in"], VarType)


@pytest.mark.asyncio
async def test_deep_type_err(client: RuntimeClient, bi: "BuilderNS"):
    @graph()
    def ifelse() -> Output:
        with IfElse(Const(True)):
            with If():
                bi.iadd(Const(1), Const(1.0))
            with Else():
                pass
        return Output()

    if not client.can_type_check:
        pytest.skip()
    with pytest.raises(
        TierkreisTypeErrors,
        match=r"In: NodeRef\(3, Const\(Graph\(if\)\)\)\/NodeRef\(4, Function\(iadd\)\)"
        + r"| NodeRef\(3, Const\(Graph\(if\)\)\)\/NodeRef\(3, Const\(1.0\)\)",
    ):
        await client.type_check_graph(ifelse)


def _extract_dbg_info(errstrings: str) -> Iterator[tuple[str, int]]:
    for errstr in errstrings.split("\n\n" + ("─" * 80) + "\n\n"):
        lines = errstr.splitlines()

        lines = lines[lines.index("Debug Info:") + 1 :]
        for line in lines:
            _, fname, linno = line.split(":", 3)
            yield fname.strip(), int(linno.strip())


@pytest.mark.skip_typecheck
@pytest.mark.asyncio
async def test_builder_debug(bi: "BuilderNS", sig: Signature):
    # test debug string is correctly found
    # checks that "ERROR" preceeds the location of reported errors
    def _bad_nod():
        # ERROR
        return bi.iadd(Const(1), Const(1.0))

    @lazy_graph(type_check_sig=sig)
    def ifelse() -> Output:
        # ERROR
        with IfElse(Const(True)):
            with If():
                _bad_nod()
            with Else():
                # ERROR
                pass
        return Output()

    @lazy_graph(type_check_sig=sig)
    def lop() -> Output:
        @loop()
        def lopdef(x) -> Output:
            # ERROR
            with IfElse(Const(True)):
                with If():
                    # ERROR
                    Continue(bi.iadd(Const(1), Const(1.0)))
                with Else():
                    # ERROR
                    Break(Const(1))
            return Output()

        # ERROR
        _y = lopdef(Const(1))

        return Output()

    @lazy_graph(type_check_sig=sig)
    def clos1() -> Output:
        # ERROR
        y = Const(1.0)

        @closure()
        # ERROR
        def clos_def(x) -> Output:
            # ERROR
            bi.iadd(x, y)
            return Output()

        return Output()

    @lazy_graph(type_check_sig=sig)
    def clos2() -> Output:
        @closure()
        # ERROR
        def clos_def(x) -> Output:
            # ERROR
            bi.iadd(x, Const(1))
            return Output()

        # ERROR
        _y = clos_def(Const(1.0))

        return Output()

    @lazy_graph(type_check_sig=sig)
    def scop(x) -> Output:
        # ERROR
        with Scope():
            # ERROR
            with Scope():
                # ERROR
                x = _bad_nod()
        return Output(x)

    for g in (ifelse, lop, clos1, clos2, scop):
        with pytest.raises(TierkreisTypeErrors) as e:
            _ = g.graph
        if (
            sys.platform.startswith("win")
            or int(platform.python_version_tuple()[1]) > 10
        ):
            # string parsing doesn't work on windows or 3.11
            continue
        with open(__file__) as f:
            self_lines = f.readlines()
        for fil, linno in _extract_dbg_info(str(e.value)):
            assert fil == __file__
            # minus 1 for 1 indexed line numbers
            assert "# ERROR" in self_lines[linno - 2]
