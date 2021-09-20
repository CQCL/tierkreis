#!/usr/bin/env python3
from pathlib import Path
import sys
from typing import Any, Iterator, Dict, List, Optional, Set, Tuple
from lark import Lark
from tierkreis import TierkreisGraph
from tierkreis.core.function import TierkreisFunction
from tierkreis.core.tierkreis_graph import NodePort, NodeRef
from tierkreis.core.types import (
    BoolType,
    FloatType,
    GraphType,
    IntType,
    PairType,
    Row,
    StringType,
    TierkreisType,
    TypeScheme,
    ArrayType,
    VarType,
)
from tierkreis.frontend import local_runtime, RuntimeClient
from tierkreis.core.graphviz import tierkreis_to_graphviz

FuncDefs = Dict[str, Tuple[TierkreisGraph, TierkreisFunction]]


def get_client() -> Iterator[RuntimeClient]:
    exe = Path("../../../../target/debug/tierkreis-server")
    # launch a local server for this test run and kill it at the end
    with local_runtime(exe, show_output=True) as local_client:
        yield local_client


client = next(get_client())

sig = client.signature


def get_func_name(token) -> Tuple[str, str]:
    if len(token.children) == 1:
        return "builtin", token.children[0]
    return token.children[0], token.children[1]


def get_const(token) -> Any:
    if token.data == "int":
        return int(token.children[0].value)
    if token.data == "float":
        return float(token.children[0].value)
    if token.data == "bool":
        return token.children[0].value == "True"
    if token.data == "str":
        return str(token.children[0].value[1:-1])


def get_type(token) -> TierkreisType:
    type_name = token.children[0].type
    if type_name == "TYPE_INT":
        return IntType()
    if type_name == "TYPE_BOOL":
        return BoolType()
    if type_name == "TYPE_STR":
        return StringType()
    if type_name == "TYPE_FLOAT":
        return FloatType()
    if type_name == "TYPE_PAIR":
        return PairType(get_type(token.children[1]), get_type(token.children[2]))
    if type_name == "TYPE_ARRAY":
        return ArrayType(get_type(token.children[1]))
    return VarType("unkown")


def get_annotations(f_param_list) -> Dict[str, TierkreisType]:
    return {
        param.children[0].value: get_type(param.children[1])
        for param in f_param_list.children
    }


def get_inp_out(f_tree) -> Tuple[Dict[str, TierkreisType], Dict[str, TierkreisType]]:
    return get_annotations(f_tree.children[1]), get_annotations(f_tree.children[2])


def get_tkfunc_def(f_tree) -> TierkreisFunction:
    inputs, outputs = get_inp_out(f_tree)
    return TierkreisFunction(
        f_tree.children[0].value,
        TypeScheme({}, [], GraphType(Row(content=inputs), Row(content=outputs))),
        "",
    )


def get_graph(f_tree, func_defs: FuncDefs) -> TierkreisGraph:
    tg = TierkreisGraph()
    code_block = f_tree.children[-1]

    node_names: Dict[str, Tuple[NodeRef, Optional[TierkreisFunction]]] = {}

    inputs, outputs = get_inp_out(f_tree)

    def get_func_outputs(node_name: str):
        node_ref, func = node_names[node_name]
        outs = (
            ["value"] if func is None else func.type_scheme.body.outputs.content.keys()
        )
        # FIXME canonical ordering
        return [node_ref[outport] for outport in outs]

    def get_outport(token) -> List[NodePort]:
        if token.data == "name":
            name = token.children[0].value
            if name in inputs:
                return [tg.input[name]]
            if name in node_names:
                return get_func_outputs(name)
            if name in func_defs:
                grap, _ = func_defs[name]
                const_node = tg.add_const(grap)
                node_names[const_node.name] = (const_node, None)
                return [const_node["value"]]
            raise RuntimeError(f"Name not found in scope: {name}.")
        if token.data == "node_output":
            return [node_names[token.children[0].value][0][token.children[1].value]]
        if token.data == "nested":
            node_ref, fun = add_node(token.children[0])
            node_names[node_ref.name] = (node_ref, fun)
            return get_func_outputs(node_ref.name)
        if token.data == "const_port":
            node_ref, fun = add_const_node(token.children[0])
            node_names[node_ref.name] = (node_ref, fun)
            return [node_ref["value"]]
        raise RuntimeError

    def get_positional_args(token, expected_ports: List[str]) -> Dict[str, NodePort]:
        all_outports = []
        for provided in token.children:
            all_outports.extend(get_outport(provided))

        return dict(zip(expected_ports, all_outports))

    def get_named_map_args(token) ->  Dict[str, NodePort]:
        return {
            t.children[0].value: get_outport(t.children[1])[0]
            for t in token.children
        }

    def get_arglist(token, expected_ports: List[str]) -> Dict[str, NodePort]:
        if token.data == "named_map":
            return get_named_map_args(token.children[0])
        if token.data == "positional":
            return get_positional_args(token, expected_ports)
        raise RuntimeError

    def add_const_node(
        token, name: Optional[str] = None
    ) -> Tuple[NodeRef, Optional[TierkreisFunction]]:
        val = get_const(token)
        const_node = tg.add_const(val, name)
        return (const_node, None)

    def add_node(
        token, name: Optional[str] = None
    ) -> Tuple[NodeRef, Optional[TierkreisFunction]]:
        if token.data == "thunk":
            outport = token.children[0]
            thunk_port = get_outport(outport)[0]
            arglist = get_named_map_args(token.children[1])
            eval_n = tg.add_node("builtin/eval", thunk=thunk_port, **arglist)
            return (eval_n, sig["builtin"]["eval"])
        else:
            nmspace, fname = get_func_name(token.children[0])
            primitive = True
            try:
                tk_func = sig[nmspace][fname]
            except KeyError as err:
                if fname in func_defs:
                    tk_func = func_defs[fname][1]
                    primitive = False
                else:
                    raise RuntimeError(f"Function name not found: {fname}") from err
            # FIXME canonical ordering
            input_ports = list(tk_func.type_scheme.body.inputs.content.keys())

            arglist = get_arglist(token.children[1], input_ports)
            if primitive:
                noderef = tg.add_node(tk_func.name, name, **arglist)
            else:
                noderef = tg.add_box(func_defs[fname][0], fname, **arglist)
            return (noderef, tk_func)

    for inst in code_block.children:
        if inst.data == "comment":
            pass
        elif inst.data == "output":
            tg.set_outputs(**get_arglist(inst.children[0], list(outputs.keys())))
        elif inst.data == "node":
            node_names[inst.children[1]] = add_node(inst.children[0])
        elif inst.data == "const_decl":
            target_name, token = inst.children
            node_names[target_name] = add_const_node(token, target_name)
        else:
            pass
    return tg



if __name__ == "__main__":
    with open("tksl.lark") as f:
        parser = Lark(f.read())

    text = """

    def add2(x: int) -> (y: int) {
        output(y: python_nodes::add(x, 2))
    }

    def add5(x: int) -> (y: int) {
        output(y: python_nodes::add(x, 5))
    }

    def main(v1: int, v2: pair<int, bool>) -> (o1: int, o2:int) {
        unpack_pair(v2) -> unp
        const three = 3
        python_nodes::add(a:unp.first, b:three) -> sum
        make_pair(unp.second, "asdf") -> pair
        # python_nodes::add(unp) -> sum
        python_nodes::add(copy(v1)) -> total

        eval(thunk: add2, x: total.value) -> eval_out
        add5(sum) -> sum
        output(o1:eval_out.y, o2: sum.y)
    }

    """
    # TODO inline function definitions
    with open(sys.argv[1]) as source:
        parse_tree = parser.parse(source.read())

    func_defs: FuncDefs = {
        child.children[0].value: (TierkreisGraph(), get_tkfunc_def(child))
        for child in parse_tree.children
    }

    # funcs = TierkreisFunction(nam, TypeScheme({}, [], GraphType(Row(content=))))
    for f_def in parse_tree.children:
        name = f_def.children[0].value
        _, tkfunc = func_defs[name]
        func_defs[name] = (get_graph(f_def, func_defs), tkfunc)

    tg = func_defs["main"][0]


    with local_runtime("../../../../target/debug/tierkreis-server", show_output=True) as client:

        tg = client.type_check_graph_blocking(tg)

        # outs = client.run_graph_blocking(tg, {"v1": 67, "v2": (45, True)})
        # print(outs)
    tierkreis_to_graphviz(tg).render("dump", "png")
