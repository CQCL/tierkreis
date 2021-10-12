from dataclasses import dataclass, field, make_dataclass
from pathlib import Path
import copy
import sys
import asyncio
from collections import OrderedDict
from typing import Any, Iterable, Iterator, Dict, List, Optional, Tuple, cast
from tierkreis import TierkreisGraph
from tierkreis.core.function import TierkreisFunction
from tierkreis.core.tierkreis_graph import NodePort, NodeRef
from tierkreis.core.types import (
    BoolType,
    CircuitType,
    FloatType,
    GraphType,
    IntType,
    MapType,
    PairType,
    Row,
    StringType,
    StructType,
    TierkreisType,
    VecType,
    VarType,
)
from tierkreis.core.tierkreis_struct import TierkreisStruct
from tierkreis.frontend import local_runtime, RuntimeClient
from tierkreis.core.graphviz import tierkreis_to_graphviz


from antlr4 import InputStream, CommonTokenStream
import io
from antlr.TkslParser import TkslParser
from antlr.TkslLexer import TkslLexer
from antlr.TkslVisitor import TkslVisitor


@dataclass
class FunctionDefinition:
    inputs: list[str]
    outputs: list[str]


FuncDefs = Dict[str, Tuple[TierkreisGraph, FunctionDefinition]]
PortMap = OrderedDict[str, Optional[TierkreisType]]
Aliases = Dict[str, TierkreisType]
NamespaceDict = Dict[str, TierkreisFunction]
RuntimeSignature = Dict[str, NamespaceDict]


@dataclass
class Context:
    functions: FuncDefs = field(default_factory=dict)
    output_vars: Dict[str, Tuple[NodeRef, FunctionDefinition]] = field(
        default_factory=dict
    )
    constants: Dict[str, NodeRef] = field(default_factory=dict)

    inputs: PortMap = field(default_factory=OrderedDict)
    outputs: PortMap = field(default_factory=OrderedDict)

    aliases: Aliases = field(default_factory=dict)

    def copy(self) -> "Context":
        return copy.deepcopy(self)


def def_from_tkfunc(func: TierkreisFunction) -> FunctionDefinition:
    return FunctionDefinition(
        func.input_order,
        func.output_order,
    )


def make_outports(node_ref: NodeRef, ports: Iterable[str]) -> List[NodePort]:
    return [node_ref[outport] for outport in ports]


class TkslTopVisitor(TkslVisitor):
    def __init__(self, signature: RuntimeSignature, context: Context):
        self.sig = signature
        self.context = context
        self.graph = TierkreisGraph()

    def visitBool_token(self, ctx: TkslParser.Bool_tokenContext) -> bool:
        if ctx.TRUE():
            return True
        return False

    def visitInport(self, ctx: TkslParser.InportContext) -> str:
        return str(ctx.ID())

    def visitPort_label(self, ctx: TkslParser.Port_labelContext) -> NodePort:
        var_name = str(ctx.ID(0))
        port_name = str(ctx.ID(1))
        noderef, _ = self.context.output_vars[var_name]
        return self.visitChildren(ctx)
        return NodePort(noderef, port_name)

    def visitF_name(
        self, ctx: TkslParser.F_nameContext
    ) -> Tuple[str, FunctionDefinition]:
        func_name = ctx.func_name.text
        namespace = ctx.namespace.text if ctx.ID(1) else "builtin"
        try:
            tkfunc = self.sig[namespace][func_name]
            func_name = tkfunc.name
            return func_name, def_from_tkfunc(tkfunc)
        except KeyError as err:
            if func_name in self.context.functions:
                return func_name, self.context.functions[func_name][1]
                primitive = False
            else:
                raise RuntimeError(f"Function name not found: {func_name}") from err

    def visitThunkable_port(
        self, ctx: TkslParser.Thunkable_portContext
    ) -> List[NodePort]:
        if ctx.port_label():
            return [self.visitPort_label(ctx.port_label())]
        if ctx.ID():
            name = str(ctx.ID())
            if name in self.context.inputs:
                return [self.graph.input[name]]
            if name in self.context.output_vars:
                node_ref, func = self.context.output_vars[name]
                return make_outports(node_ref, func.outputs)
            if name in self.context.functions:
                grap, _ = self.context.functions[name]
                const_node = self.graph.add_const(grap)
                return [const_node["value"]]
            if name in self.context.constants:
                return [self.context.constants[name]["value"]]
            raise RuntimeError(f"Name not found in scope: {name}.")
        raise RuntimeError()

    def add_const_node(self, val: Any, name: Optional[str] = None) -> NodeRef:
        const_node = self.graph.add_const(val, name)
        return const_node

    def visitOutport(self, ctx: TkslParser.OutportContext) -> List[NodePort]:
        if ctx.thunkable_port():
            return self.visitThunkable_port(ctx.thunkable_port())
        if ctx.node_inputs():
            node_ref, fun = self.visit(
                ctx.node_inputs()
            )  # relies on correct output here
            return make_outports(node_ref, fun.outputs)
        if ctx.const_():
            node_ref = self.add_const_node(self.vist(ctx.const_()))
            return [node_ref["value"]]
        raise RuntimeError()

    def visitPort_map(self, ctx: TkslParser.Port_mapContext) -> Tuple[str, NodePort]:
        # only one outport in portmap
        return self.visitInport(ctx.inport()), self.visitOutport(ctx.outport())[0]

    def visitPositional_args(
        self, ctx: TkslParser.Positional_argsContext
    ) -> List[NodePort]:
        return sum(map(self.visitOutport, ctx.arg_l), [])

    def visitNamed_map(self, ctx: TkslParser.Named_mapContext) -> Dict[str, NodePort]:
        return dict(map(self.visitPort_map, ctx.port_l))

    # def visit
    def visitStruct_id(self, ctx: TkslParser.Struct_idContext) -> Optional[str]:
        if ctx.TYPE_STRUCT():
            return None
        if ctx.ID():
            return str(ctx.ID())
        raise RuntimeError()

    def visitConst_assign(self, ctx: TkslParser.Const_assignContext) -> Tuple[str, Any]:
        return str(ctx.ID()), self.visitConst_(ctx.const_())

    def visitConst_(self, ctx: TkslParser.Const_Context) -> Any:
        if ctx.SIGNED_INT():
            return int(str(ctx.SIGNED_INT()))
        if ctx.bool_token():
            return self.visitBool_token(ctx.bool_token())
        if ctx.SIGNED_FLOAT():
            return float(str(ctx.SIGNED_FLOAT()))
        if ctx.SHORT_STRING():
            return str(ctx.SHORT_STRING())[1:-1]
        if ctx.vec_const():
            return list(map(self.visitConst_, ctx.vec_const().elems))
        if ctx.struct_const():
            struct_ctx = ctx.struct_const()
            _struct_id = str(struct_ctx.sid)
            fields = dict(map(self.visitConst_assign, struct_ctx.fields))
            cl = make_dataclass(
                "anon_struct", fields=fields.keys(), bases=(TierkreisStruct,)
            )
            return cl(**fields)

    def visitF_param(self, ctx: TkslParser.F_paramContext) -> Tuple[str, TierkreisType]:
        return ctx.label.text, self.visitType_(ctx.annotation)

    def visitF_param_list(
        self, ctx: TkslParser.F_param_listContext
    ) -> Dict[str, TierkreisType]:
        return dict(map(self.visitF_param, ctx.par_list))

    def visitType_(self, ctx: TkslParser.Type_Context) -> TierkreisType:
        if ctx.TYPE_INT():
            return IntType()
        if ctx.TYPE_BOOL():
            return BoolType()
        if ctx.TYPE_STR():
            return StringType()
        if ctx.TYPE_FLOAT():
            return FloatType()
        if ctx.TYPE_PAIR():
            pair_type = PairType(self.visit(ctx.first), self.visit(ctx.second))
            return pair_type
        if ctx.TYPE_MAP():
            return MapType(self.visit(ctx.key), self.visit(ctx.val))
        if ctx.TYPE_VEC():
            return VecType(self.visit(ctx.element))
        if ctx.TYPE_STRUCT():
            return StructType(Row(self.visit(ctx.fields)))
        if ctx.graph_type():
            gt_ctx = ctx.graph_type()
            return GraphType(
                inputs=Row(self.visit(gt_ctx.inputs)),
                outputs=Row(self.visit(gt_ctx.outputs)),
            )
        if ctx.ID():
            return self.context.aliases[str(ctx.ID())]
            # if type_name == "TYPE_MAP":
            #     return MapType(
            #         get_type(token.children[1], aliases), get_type(token.children[2], aliases)
            #     )
            # if type_name == "TYPE_VEC":
            #     return VecType(get_type(token.children[1], aliases))
            # if type_name == "TYPE_STRUCT":
            #     args = token.children[1].children
            #     return StructType(
            #         Row(
            #             {
            #                 arg.children[0].value: get_type(arg.children[1], aliases)
            #                 for arg in args
            #             }
            #         )
            #     )
            # if type_name == "TYPE_CIRCUIT":
            #     return CircuitType()
            # if token.data == "alias":
            # return aliases[token.children[0].value]
        return VarType("unkown")

    def visitDeclaration(self, ctx: TkslParser.DeclarationContext) -> None:

        if ctx.TYPE():
            self.context.aliases[ctx.alias.text] = self.visit(ctx.type_def)
        return self.visitChildren(ctx)


from grpclib.client import Channel
from tierkreis.frontend.myqos_client import MyqosClient
import ssl


async def main():
    with open("antlr_sample.tksl") as f:
        text = f.read()
    lexer = TkslLexer(InputStream(text))
    stream = CommonTokenStream(lexer)
    parser = TkslParser(stream)

    output = io.StringIO()
    error = io.StringIO()
    # parser.removeErrorListeners()
    # errorListener = ChatErrorListener(self.error)

    tree = parser.start()
    exe = Path("../../../../target/debug/tierkreis-server")
    async with local_runtime(exe) as local_client:
        sig = await local_client.get_signature()
    # context = ssl.create_default_context()
    # context.check_hostname = False
    # context.verify_mode = ssl.CERT_NONE
    # async with Channel("cqtrr595bx-staging-pr.uksouth.cloudapp.azure.com/tierkreis/", ssl=context) as channel:
    #     print(await channel.__connect__())
    #     client = MyqosClient(channel)
    #     sig = await client.get_signature()
    out = TkslTopVisitor(sig, Context()).visit(tree)
    print(out)


asyncio.run(main())
