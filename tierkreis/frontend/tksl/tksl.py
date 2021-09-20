#!/usr/bin/env python3
from dataclasses import dataclass, field, make_dataclass
from pathlib import Path
import copy
import sys
from typing import Any, Iterable, Iterator, Dict, List, Optional, Set, Tuple, cast
from lark import Lark
from lark.lexer import Token
from lark.tree import Tree
from networkx import convert
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
    StructType,
    TierkreisType,
    TypeScheme,
    ArrayType,
    VarType,
)
from tierkreis.core.tierkreis_struct import TierkreisStruct
from tierkreis.frontend import local_runtime, RuntimeClient
from tierkreis.core.graphviz import tierkreis_to_graphviz

FuncDefs = Dict[str, Tuple[TierkreisGraph, TierkreisFunction]]


@dataclass
class Context:
    functions: Dict[str, Tuple[TierkreisGraph, TierkreisFunction]] = field(
        default_factory=dict
    )
    output_vars: Dict[str, Tuple[NodeRef, TierkreisFunction]] = field(
        default_factory=dict
    )
    constants: Dict[str, NodeRef] = field(default_factory=dict)

    inputs: Dict[str, TierkreisType] = field(default_factory=dict)
    outputs: Dict[str, TierkreisType] = field(default_factory=dict)

    aliases: Dict[str, TierkreisType] = field(default_factory=dict)

    def copy(self) -> "Context":
        return copy.deepcopy(self)


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
    if token.data == "struct":
        struct_id = token.children[0]
        # if struct_id.data == "anon":
        #     pass
        # else:
        #     raise RuntimeError # TODO aliases
        
        field_names = [const_assign.children[0].value for const_assign in token.children[1:]]
        values = [get_const(const_assign.children[1]) for const_assign in token.children[1:]]
        cl = make_dataclass("anon_struct", fields=field_names, bases=(TierkreisStruct,))

        return cl(**dict(zip(field_names, values)))


def get_type(token, aliases: Dict[str, TierkreisType] = {}) -> TierkreisType:
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
        return PairType(get_type(token.children[1], aliases), get_type(token.children[2], aliases))
    if type_name == "TYPE_ARRAY":
        return ArrayType(get_type(token.children[1], aliases))
    if type_name == "TYPE_STRUCT":
        args = token.children[1].children
        return StructType(Row({arg.children[0].value: get_type(arg.children[1], aliases) for arg in args}))
    if type_name == "CNAME":
        return aliases[token.children[0].value]
    return VarType("unkown")


def get_annotations(f_param_list, aliases: Dict[str, TierkreisType] = {}) -> Dict[str, TierkreisType]:
    return {
        param.children[0].value: get_type(param.children[1], aliases)
        for param in f_param_list.children
    }


def get_inp_out(f_tree, aliases: Dict[str, TierkreisType] = {}) -> Tuple[Dict[str, TierkreisType], Dict[str, TierkreisType]]:
    return get_annotations(f_tree.children[1], aliases), get_annotations(f_tree.children[2], aliases)


def gen_tkfunc(
    name: str, inputs: Dict[str, TierkreisType], outputs: Dict[str, TierkreisType]
) -> TierkreisFunction:
    return TierkreisFunction(
        name,
        TypeScheme({}, [], GraphType(Row(content=inputs), Row(content=outputs))),
        "",
    )


def get_tkfunc_def(f_tree, aliases: Dict[str, TierkreisType] = {}) -> TierkreisFunction:
    inputs, outputs = get_inp_out(f_tree, aliases)
    return gen_tkfunc(f_tree.children[0].value, inputs, outputs)


def make_outports(node_ref: NodeRef, ports: Iterable[str]) -> List[NodePort]:
    return [node_ref[outport] for outport in ports]


def ports_from_tkfunc(func: TierkreisFunction, outputs: bool = True) -> List[str]:
    # FIXME canonical ordering
    row = func.type_scheme.body.outputs if outputs else func.type_scheme.body.inputs
    return list(row.content.keys())


def get_graph(f_tree, context: Context) -> TierkreisGraph:
    tg = TierkreisGraph()
    code_block = f_tree.children[-1]
    inputs, outputs = get_inp_out(f_tree, context.aliases)
    context.inputs = inputs
    context.outputs = outputs
    append_code_block(code_block, context, tg)

    return tg


def append_code_block(code_block: Tree, context: Context, tg: TierkreisGraph) -> None:

    context = context.copy()

    def get_func_outputs(node_name: str) -> List[NodePort]:
        node_ref, func = context.output_vars[node_name]
        outs = ports_from_tkfunc(func)
        return make_outports(node_ref, outs)

    def get_outport(token) -> List[NodePort]:
        if token.data == "name":
            name = token.children[0].value
            if name in context.inputs:
                return [tg.input[name]]
            if name in context.output_vars:
                return get_func_outputs(name)
            if name in context.functions:
                grap, _ = context.functions[name]
                const_node = tg.add_const(grap)
                return [const_node["value"]]
            if name in context.constants:
                return [context.constants[name]["value"]]
            raise RuntimeError(f"Name not found in scope: {name}.")
        if token.data == "node_output":
            return [
                context.output_vars[token.children[0].value][0][token.children[1].value]
            ]
        if token.data == "nested":
            node_ref, fun = add_node(token.children[0])
            return make_outports(
                node_ref,
                ports_from_tkfunc(
                    fun,
                ),
            )
        if token.data == "const_port":
            node_ref = add_const_node(token.children[0])
            return [node_ref["value"]]
        raise RuntimeError

    def get_positional_args(token, expected_ports: List[str]) -> Dict[str, NodePort]:
        all_outports = []
        for provided in token.children:
            all_outports.extend(get_outport(provided))

        return dict(zip(expected_ports, all_outports))

    def get_named_map_args(token) -> Dict[str, NodePort]:
        return {
            t.children[0].value: get_outport(t.children[1])[0] for t in token.children
        }

    def get_arglist(token, expected_ports: List[str]) -> Dict[str, NodePort]:
        if token.data == "named_map":
            return get_named_map_args(token.children[0])
        if token.data == "positional":
            return get_positional_args(token, expected_ports)
        raise RuntimeError

    def add_const_node(token, name: Optional[str] = None) -> NodeRef:
        val = get_const(token)
        const_node = tg.add_const(val, name)
        return const_node

    def add_node(
        token, name: Optional[str] = None
    ) -> Tuple[NodeRef, TierkreisFunction]:
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
                if fname in context.functions:
                    tk_func = context.functions[fname][1]
                    primitive = False
                else:
                    raise RuntimeError(f"Function name not found: {fname}") from err
            # FIXME canonical ordering
            input_ports = list(tk_func.type_scheme.body.inputs.content.keys())

            arglist = get_arglist(token.children[1], input_ports)
            if primitive:
                noderef = tg.add_node(tk_func.name, name, **arglist)
            else:
                noderef = tg.add_box(context.functions[fname][0], fname, **arglist)
            return (noderef, tk_func)

    for inst in code_block.children:
        inst = cast(Tree, inst)
        if inst.data == "comment":
            pass
        elif inst.data == "output":
            tg.set_outputs(
                **get_arglist(inst.children[0], list(context.outputs.keys()))
            )
        elif inst.data == "node":
            outvar = cast(str, inst.children[1])
            node_inputs = cast(Tree, inst.children[0])
            context.output_vars[outvar] = add_node(node_inputs)
        elif inst.data == "const_decl":
            target_name, token = inst.children
            target_name = cast(str, target_name)
            token = cast(Token, token)
            context.constants[target_name] = add_const_node(token, target_name)
        elif inst.data == "if_block":
            condition = cast(Tree, inst.children[0])
            pred = get_outport(condition)[0]

            port_map = cast(Tree, inst.children[1])
            inps = get_named_map_args(port_map)
            loopcontext = Context()
            loopcontext.functions = context.functions
            loopcontext.inputs = {inp: VarType("unknown_if") for inp in inps}

            # outputs from if-else block have to be named map (not positional)

            if_block = cast(Tree, inst.children[2])
            if_g = TierkreisGraph()
            append_code_block(if_block, loopcontext, if_g)

            else_block = cast(Tree, inst.children[3])
            else_g = TierkreisGraph()
            append_code_block(else_block, loopcontext, else_g)

            output_var = cast(str, inst.children[4])

            sw_nod = tg.add_node(
                "builtin/switch", predicate=pred, true=if_g, false=else_g
            )
            eval_n = tg.add_node("builtin/eval", thunk=sw_nod["value"], **inps)

            output_names = set(if_g.outputs()).union(else_g.outputs())
            loopcontext.outputs = {outp: VarType("unknown_if") for outp in output_names}

            fake_func = gen_tkfunc(
                f"eval_{eval_n.name}", loopcontext.inputs, loopcontext.outputs
            )
            context.output_vars[output_var] = (eval_n, fake_func)
            # raise RuntimeError
        elif inst.data == "loop":

            port_map = cast(Tree, inst.children[0])
            inps = get_named_map_args(port_map)
            loopcontext = Context()
            loopcontext.functions = context.functions
            loopcontext.inputs = {inp: VarType("unknown_loop") for inp in inps}

            # outputs from if-else block have to be named map (not positional)

            condition_block = cast(Tree, inst.children[1])
            condition_g = TierkreisGraph()
            append_code_block(condition_block, loopcontext, condition_g)

            body_block = cast(Tree, inst.children[2])
            body_g = TierkreisGraph()
            append_code_block(body_block, loopcontext, body_g)

            output_var = cast(str, inst.children[3])

            loop_nod = tg.add_node(
                "builtin/loop", condition=condition_g, body=body_g, **inps
            )

            loopcontext.outputs = {
                outp: VarType("unknown_if") for outp in body_g.outputs()
            }

            fake_func = gen_tkfunc(
                f"loop_{loop_nod.name}", loopcontext.inputs, loopcontext.outputs
            )
            context.output_vars[output_var] = (loop_nod, fake_func)
            # raise RuntimeError

        else:
            pass


if __name__ == "__main__":
    with open("tksl.lark") as f:
        parser = Lark(f.read())

    # TODO inline function definitions
    with open(sys.argv[1]) as source:
        parse_tree = parser.parse(source.read())

    context = Context()

    funcs = [child.children[0] for child in parse_tree.children if child.data == "func"]
    typ_decs = [child for child in parse_tree.children if child.data == "type_alias"]
    for typ_dec in typ_decs:
        alias = typ_dec.children[0].value

        context.aliases[alias] = get_type(typ_dec.children[1], context.aliases)
    

    context.functions = {
        child.children[0].value: (TierkreisGraph(), get_tkfunc_def(child, context.aliases))
        for child in funcs
    }

    # funcs = TierkreisFunction(nam, TypeScheme({}, [], GraphType(Row(content=))))
    for f_def in funcs:
        name = f_def.children[0].value
        _, tkfunc = context.functions[name]
        context.functions[name] = (get_graph(f_def, context), tkfunc)

    tg = context.functions["main"][0]

    with local_runtime(
        "../../../../target/debug/tierkreis-server", show_output=True
    ) as client:

        tg = client.type_check_graph_blocking(tg)

        # outs = client.run_graph_blocking(tg, {"v1": 67, "v2": (45, True)})
        # print(outs)
    tierkreis_to_graphviz(tg).render("dump", "png")
