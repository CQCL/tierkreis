import copy
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Callable, Dict, Iterable, List, Optional, Tuple

from antlr4 import CommonTokenStream, InputStream  # type: ignore
from antlr4.error.ErrorListener import ErrorListener  # type: ignore
from antlr4.error.Errors import ParseCancellationException  # type: ignore

# from pytket.qasm import circuit_from_qasm
from tierkreis import TierkreisGraph
from tierkreis.core.function import TierkreisFunction
from tierkreis.core.tierkreis_graph import NodePort, NodeRef, TierkreisEdge
from tierkreis.core.types import (
    BoolType,
    FloatType,
    GraphType,
    IntType,
    MapType,
    OptionType,
    PairType,
    Row,
    StringType,
    StructType,
    TierkreisType,
    TypeScheme,
    VecType,
)
from tierkreis.core.values import (
    FloatValue,
    TierkreisValue,
    IntValue,
    BoolValue,
    StringValue,
    VecValue,
    StructValue,
    OptionValue,
)
from tierkreis.frontend.runtime_client import RuntimeSignature
from tierkreis.frontend.tksl.antlr.TkslLexer import TkslLexer  # type: ignore
from tierkreis.frontend.tksl.antlr.TkslParser import TkslParser  # type: ignore
from tierkreis.frontend.tksl.antlr.TkslVisitor import TkslVisitor  # type: ignore


def _circuit_json(file_path: StringValue) -> StructValue:
    with open(file_path.value) as f:
        return StructValue({"json": StringValue(f.read())})


def _read_file(file_path: StringValue) -> StringValue:
    with open(file_path.value) as f:
        return StringValue(f.read())


MACRODEFS: Dict[str, Callable[..., TierkreisValue]] = {
    "circuit_json": _circuit_json,
    "read_file": _read_file,
}


@dataclass
class FunctionDefinition:
    inputs: list[str]
    outputs: list[str]
    graph_type: Optional[GraphType] = None


FuncDefs = Dict[str, Tuple[TierkreisGraph, FunctionDefinition]]
PortMap = OrderedDict[str, Optional[TierkreisType]]
Aliases = Dict[str, TierkreisType]


class TkslCompileException(Exception):
    pass


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

    use_defs: Dict[str, str] = field(default_factory=dict)

    def copy(self) -> "Context":
        return copy.deepcopy(self)


def def_from_tkfunc(func: TierkreisFunction) -> FunctionDefinition:
    return FunctionDefinition(
        func.input_order,
        func.output_order,
    )


def make_outports(node_ref: NodeRef, ports: Iterable[str]) -> List[NodePort]:
    return [node_ref[outport] for outport in ports]


class TkslFileVisitor(TkslVisitor):
    def __init__(self, signature: RuntimeSignature, context: Context):
        self.sig = signature
        self.context = context.copy()
        self.graph = TierkreisGraph()

    def visitBool_token(self, ctx: TkslParser.Bool_tokenContext) -> bool:
        return True if ctx.TRUE() else False

    def visitInport(self, ctx: TkslParser.InportContext) -> str:
        return str(ctx.ID())

    def visitPort_label(self, ctx: TkslParser.Port_labelContext) -> NodePort:
        var_name = str(ctx.ID(0))
        port_name = str(ctx.ID(1))
        noderef, _ = self.context.output_vars[var_name]
        return NodePort(noderef, port_name)

    def visitF_name(
        self, ctx: TkslParser.F_nameContext
    ) -> Tuple[str, FunctionDefinition]:
        func_name = ctx.func_name.text
        if ctx.ID(1):
            namespace = ctx.namespace.text
        elif func_name in self.context.use_defs:
            namespace = self.context.use_defs[func_name]
        else:
            namespace = "builtin"
        try:
            tkfunc = self.sig[namespace].functions[func_name]
            func_name = tkfunc.name
            return func_name, def_from_tkfunc(tkfunc)
        except KeyError as err:
            if func_name in self.context.functions:
                return func_name, self.context.functions[func_name][1]
            else:
                raise TkslCompileException(
                    f"Function name not found: {func_name}"
                ) from err

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
            raise TkslCompileException(f"Name not found in scope: {name}.")
        raise TkslCompileException()

    def visitOutport(self, ctx: TkslParser.OutportContext) -> List[NodePort]:
        if ctx.thunkable_port():
            return self.visitThunkable_port(ctx.thunkable_port())
        if ctx.node_inputs():
            node_ref, fun = self.visit(
                ctx.node_inputs()
            )  # relies on correct output here
            return make_outports(node_ref, fun.outputs)
        if ctx.const_():
            node_ref = self.graph.add_const(self.visitConst_(ctx.const_()))
            return [node_ref["value"]]
        raise TkslCompileException()

    def visitPort_map(self, ctx: TkslParser.Port_mapContext) -> Tuple[str, NodePort]:
        # only one outport in portmap
        return self.visitInport(ctx.inport()), self.visitOutport(ctx.outport())[0]

    def visitPositional_args(
        self, ctx: TkslParser.Positional_argsContext
    ) -> List[NodePort]:
        return sum(map(self.visitOutport, ctx.arg_l), [])

    def visitNamed_map(self, ctx: TkslParser.Named_mapContext) -> Dict[str, NodePort]:
        return dict(map(self.visitPort_map, ctx.port_l))

    def visitArglist(self, ctx: TkslParser.ArglistContext) -> Dict[str, NodePort]:
        if ctx.named_map():
            return self.visitNamed_map(ctx.named_map())
        if ctx.positional_args():
            assert hasattr(ctx, "expected_ports")
            return dict(
                zip(
                    ctx.expected_ports, self.visitPositional_args(ctx.positional_args())
                )
            )
        raise TkslCompileException()

    def visitFuncCall(
        self, ctx: TkslParser.FuncCallContext
    ) -> Tuple[NodeRef, FunctionDefinition]:
        f_name, f_def = self.visitF_name(ctx.f_name())
        arglist = {}
        if hasattr(ctx, "arglist"):
            argctx = ctx.arglist()
            argctx.expected_ports = f_def.inputs
            arglist = self.visitArglist(argctx)

        if f_name in self.context.functions:
            noderef = self.graph.add_box(
                self.context.functions[f_name][0], f_name, **arglist
            )
        else:
            noderef = self.graph.add_node(f_name, **arglist)

        return noderef, f_def

    def visitThunk(
        self, ctx: TkslParser.ThunkContext
    ) -> Tuple[NodeRef, FunctionDefinition]:
        outport = self.visitThunkable_port(ctx.thunkable_port())[0]
        arglist = self.visitNamed_map(ctx.named_map()) if ctx.named_map() else {}
        eval_n = self.graph.add_node("builtin/eval", thunk=outport, **arglist)
        return eval_n, def_from_tkfunc(self.sig["builtin"].functions["eval"])

    def visitCallMap(self, ctx: TkslParser.CallMapContext) -> None:
        target = ctx.target.text
        self.context.output_vars[target] = self.visit(ctx.call)

    def visitOutputCall(self, ctx: TkslParser.OutputCallContext) -> None:
        argctx = ctx.arglist()
        argctx.expected_ports = list(self.context.outputs)
        self.graph.set_outputs(**self.visitArglist(argctx))

    def visitConstDecl(self, ctx: TkslParser.ConstDeclContext) -> None:
        target = ctx.const_name.text
        const_val = self.visitConst_(ctx.const_())
        self.context.constants[target] = self.graph.add_const(const_val)

    def visitIfBlock(self, ctx: TkslParser.IfBlockContext):
        target = ctx.target.text
        condition = self.visitOutport(ctx.condition)[0]
        inputs = self.visitNamed_map(ctx.inputs) if ctx.inputs else {}

        ifcontext = Context()
        ifcontext.functions = self.context.functions.copy()
        ifcontext.use_defs = self.context.use_defs.copy()
        ifcontext.inputs = OrderedDict({inp: None for inp in inputs})
        # outputs from if-else block have to be named map (not positional)

        ifvisit = TkslFileVisitor(self.sig, ifcontext)
        if_g = ifvisit.visitCode_block(ctx.if_block)

        elsevisit = TkslFileVisitor(self.sig, ifcontext)
        else_g = elsevisit.visitCode_block(ctx.else_block)

        sw_nod = self.graph.add_node(
            "builtin/switch", pred=condition, if_true=if_g, if_false=else_g
        )
        eval_n = self.graph.add_node("builtin/eval", thunk=sw_nod["value"], **inputs)

        output_names = set(if_g.outputs()).union(else_g.outputs())
        ifcontext.outputs = OrderedDict({outp: None for outp in output_names})

        fake_func = FunctionDefinition(list(ifcontext.inputs), list(ifcontext.outputs))
        self.context.output_vars[target] = (eval_n, fake_func)

    def visitLoop(self, ctx: TkslParser.LoopContext):
        target = ctx.target.text
        inputs = self.visitNamed_map(ctx.inputs) if ctx.inputs else {}

        loopcontext = Context()
        loopcontext.functions = self.context.functions.copy()
        loopcontext.use_defs = self.context.use_defs.copy()
        loopcontext.inputs = OrderedDict({inp: None for inp in inputs})
        # outputs from if-else block have to be named map (not positional)

        bodyvisit = TkslFileVisitor(self.sig, loopcontext)
        body_g = bodyvisit.visitCode_block(ctx.body)

        conditionvisit = TkslFileVisitor(self.sig, loopcontext)
        condition_g = conditionvisit.visitCode_block(ctx.condition)

        # ignore unused inputs
        body_g.set_outputs(
            **{
                inp: body_g.input[inp]
                for inp in loopcontext.inputs
                if inp not in body_g.inputs()
            }
        )

        for inp in loopcontext.inputs:
            if inp not in condition_g.inputs():
                condition_g.discard(condition_g.input[inp])

        loop_nod = self.graph.add_node(
            "builtin/loop", condition=condition_g, body=body_g, **inputs
        )

        loopcontext.outputs = OrderedDict({outp: None for outp in body_g.outputs()})

        fake_func = FunctionDefinition(
            list(loopcontext.inputs), list(loopcontext.outputs)
        )
        self.context.output_vars[target] = (loop_nod, fake_func)

    def visitEdge(self, ctx: TkslParser.EdgeContext) -> TierkreisEdge:
        return self.graph.add_edge(
            self.visitPort_label(ctx.source), self.visitPort_label(ctx.target)
        )

    def visitCode_block(self, ctx: TkslParser.Code_blockContext) -> TierkreisGraph:
        _ = list(map(self.visit, ctx.inst_list))
        return self.graph

    def visitFuncDef(self, ctx: TkslParser.FuncDefContext):
        name = str(ctx.ID())
        f_def = self.visitGraph_type(ctx.graph_type())
        g_type = f_def.graph_type
        assert g_type is not None
        context = self.context.copy()
        context.inputs = OrderedDict(
            (key, g_type.inputs.content[key]) for key in f_def.inputs
        )
        context.outputs = OrderedDict(
            (key, g_type.outputs.content[key]) for key in f_def.outputs
        )
        def_visit = TkslFileVisitor(self.sig, context)
        graph = def_visit.visitCode_block(ctx.code_block())

        self.context.functions[name] = (graph, f_def)

    def visitTypeAlias(self, ctx: TkslParser.TypeAliasContext):
        alias_name = str(ctx.ID())
        if alias_name in self.context.aliases:
            raise TkslCompileException(f"Type alias {alias_name} already exists.")
        type_ = self.visitType_(ctx.type_())
        self.context.aliases[alias_name] = type_

    def visitUseDef(self, ctx: TkslParser.UseDefContext):
        namespace = ctx.namespace.text
        names = self.visitUse_ids(ctx.use_ids())
        if names is None:
            names = list(self.sig[namespace].functions.keys())
        self.context.use_defs.update({name: namespace for name in names})

    def visitUse_ids(self, ctx: TkslParser.Use_idsContext) -> Optional[List[str]]:
        if ctx.names:
            return [name.text for name in ctx.names]
        return None

    def visitStart(self, ctx: TkslParser.StartContext) -> TierkreisGraph:
        _ = list(map(self.visit, ctx.decs))

        return self.context.functions["main"][0]

    def visitStruct_id(self, ctx: TkslParser.Struct_idContext) -> Optional[str]:
        if ctx.TYPE_STRUCT():
            return None
        if ctx.ID():
            return str(ctx.ID())
        raise TkslCompileException()

    def visitConst_assign(
        self, ctx: TkslParser.Const_assignContext
    ) -> Tuple[str, TierkreisValue]:
        return str(ctx.ID()), self.visitConst_(ctx.const_())

    def visitSome(self, ctx: TkslParser.SomeContext) -> OptionValue:
        return OptionValue(self.visitConst_(ctx.const_()))

    def visitNone(self, ctx: TkslParser.NoneContext) -> OptionValue:
        return OptionValue(None)

    def visitConst_(self, ctx: TkslParser.Const_Context) -> TierkreisValue:
        if ctx.SIGNED_INT():
            return IntValue(int(str(ctx.SIGNED_INT())))
        if ctx.bool_token():
            return BoolValue(self.visitBool_token(ctx.bool_token()))
        if ctx.SIGNED_FLOAT():
            return FloatValue(float(str(ctx.SIGNED_FLOAT())))
        if ctx.SHORT_STRING():
            return StringValue(str(ctx.SHORT_STRING())[1:-1])
        if ctx.vec_const():
            vec_ctx = ctx.vec_const()
            if len(vec_ctx.elems) == 1:
                if vec_ctx.elems[0].getText() == "":
                    return VecValue([])
            return VecValue(list(map(self.visitConst_, vec_ctx.elems)))
        if ctx.struct_const():
            struct_ctx = ctx.struct_const()
            fields = dict(map(self.visitConst_assign, struct_ctx.fields))
            return StructValue(fields)
        if ctx.opt_const():
            return self.visit(ctx.opt_const())
        if ctx.macro_const():
            macro_ctx = ctx.macro_const()
            macro_name = str(macro_ctx.ID())
            args = tuple(map(self.visitConst_, macro_ctx.cargs))
            try:
                macrofunc = MACRODEFS[macro_name]
            except KeyError as e:
                raise TkslCompileException(
                    f"No constant macro found with name {macro_name}"
                ) from e
            return macrofunc(*args)

        raise TkslCompileException(f"Unrecognised constant: {ctx.getText()}")

    def visitF_param(self, ctx: TkslParser.F_paramContext) -> Tuple[str, TierkreisType]:
        return ctx.label.text, self.visitType_(ctx.annotation)

    def visitF_param_list(
        self, ctx: TkslParser.F_param_listContext
    ) -> OrderedDict[str, TierkreisType]:
        return OrderedDict(map(self.visitF_param, ctx.par_list))

    def visitGraph_type(self, ctx: TkslParser.Graph_typeContext) -> FunctionDefinition:
        inputs = self.visitF_param_list(ctx.inputs)
        outputs = self.visitF_param_list(ctx.outputs)
        g_type = GraphType(
            inputs=Row(inputs),
            outputs=Row(outputs),
        )
        return FunctionDefinition(list(inputs), list(outputs), g_type)

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
        if ctx.TYPE_OPTION():
            return OptionType(self.visit(ctx.inner))
        if ctx.TYPE_STRUCT():
            return StructType(Row(self.visit(ctx.fields)))
        if ctx.graph_type():
            g_type = self.visitGraph_type(ctx.graph_type()).graph_type
            assert g_type is not None
            return g_type
        if ctx.ID():
            return self.context.aliases[str(ctx.ID())]
        raise TkslCompileException(f"Unknown type: {ctx.getText()}")

    def visitDeclaration(self, ctx: TkslParser.DeclarationContext) -> None:

        if ctx.TYPE():
            self.context.aliases[ctx.alias.text] = self.visit(ctx.type_def)
        return self.visitChildren(ctx)


class ThrowingErrorListener(ErrorListener):
    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
        ex = ParseCancellationException(f"line {line}: {column} {msg}")
        ex.line = line
        ex.column = column
        raise ex


def parse_tksl(
    source: str, signature: Optional[RuntimeSignature] = None
) -> TierkreisGraph:
    """Parse a tksl source file and return the "main" graph.

    :param source: Source file as string
    :type source: str
    :param signature: Runtime signature if available, defaults to None
    :type signature: Optional[RuntimeSignature], optional
    :return: Graph defined as "main" in source
    :rtype: TierkreisGraph
    """
    signature = signature or {}
    lexer = TkslLexer(InputStream(source))
    lexer.removeErrorListeners()
    lexer.addErrorListener(ThrowingErrorListener())

    stream = CommonTokenStream(lexer)
    parser = TkslParser(stream)
    parser.removeErrorListeners()
    parser.addErrorListener(ThrowingErrorListener())

    tree = parser.start()
    return TkslFileVisitor(signature, Context()).visitStart(tree)
