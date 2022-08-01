import copy
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Callable, Dict, Iterable, List, Optional, Tuple, Union, cast
from pathlib import Path
import re

from antlr4 import CommonTokenStream, InputStream  # type: ignore
from antlr4.error.ErrorListener import ErrorListener  # type: ignore
from antlr4.error.Errors import ParseCancellationException  # type: ignore

# from pytket.qasm import circuit_from_qasm
from tierkreis import TierkreisGraph
from tierkreis.core import Labels
from tierkreis.core.function import TierkreisFunction
from tierkreis.core.tierkreis_graph import NodePort, NodeRef, TierkreisEdge, TagNode
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
    VariantType,
    VarType,
    VecType,
)
from tierkreis.core.values import (
    FloatValue,
    PairValue,
    TierkreisValue,
    IntValue,
    BoolValue,
    StringValue,
    VecValue,
    StructValue,
    OptionValue,
    VariantValue,
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


def _include(file_path: StringValue) -> TierkreisValue:
    raise TkslCompileException(
        "include! macro only used by preprocessing.\n"
        "Hint: try using load_tksl_file instead of parse_tksl."
    )


MACRODEFS: Dict[str, Callable[..., TierkreisValue]] = {
    "circuit_json": _circuit_json,
    "read_file": _read_file,
    "include": _include,
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

    def visitNamed_obj(self, ctx: TkslParser.Named_objContext) -> tuple[str, str]:
        name = ctx.name.text
        namespace = ctx.namespace.text if ctx.ID(1) else ""

        return namespace, name

    def visitF_name(
        self, ctx: TkslParser.F_nameContext
    ) -> Tuple[str, FunctionDefinition]:
        namespace, func_name = self.visitNamed_obj(ctx.named_obj())
        if namespace:
            pass
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
                if len(func.outputs) > 0:
                    return make_outports(node_ref, func.outputs)
                raise TkslCompileException(
                    f"Node {name} does not have any known outports"
                )
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
        # Should be only one outport in portmap
        in_name = self.visitInport(ctx.inport())
        out_ports = self.visitOutport(ctx.outport())
        if len(out_ports) != 1:
            raise TkslCompileException(f"Expected exactly one outport, got {out_ports}")
        return in_name, out_ports[0]

    def visitPositional_args(
        self, ctx: TkslParser.Positional_argsContext
    ) -> List[NodePort]:
        return sum(map(self.visitOutport, ctx.arg_l), [])

    def visitNamed_map(
        self, ctx: TkslParser.Named_mapContext
    ) -> OrderedDict[str, NodePort]:
        return OrderedDict(map(self.visitPort_map, ctx.port_l))

    def visitOptionalNamed_map(
        self, ctx: Optional[TkslParser.Named_mapContext]
    ) -> Dict[str, NodePort]:
        if ctx:
            return self.visitNamed_map(ctx)
        return {}

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
            noderef = self.graph.add_func(f_name, **arglist)

        return noderef, f_def

    def visitTag(
        self, ctx: TkslParser.TagContext
    ) -> Tuple[NodeRef, FunctionDefinition]:
        tag = str(ctx.ID())
        (value,) = self.visit(ctx.outport())
        noderef = self.graph.add_node(TagNode(tag), value=value)
        return noderef, FunctionDefinition([Labels.VALUE], [Labels.VALUE])

    def visitThunk(
        self, ctx: TkslParser.ThunkContext
    ) -> Tuple[NodeRef, FunctionDefinition]:
        outport = self.visitThunkable_port(ctx.thunkable_port())[0]
        arglist = self.visitOptionalNamed_map(ctx.named_map())
        eval_n = self.graph.add_func("builtin/eval", thunk=outport, **arglist)
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

    def _cloneContextWithInputs(self, inputs: Dict[str, NodePort]) -> Context:
        new_ctx = Context()
        new_ctx.functions = self.context.functions.copy()
        new_ctx.use_defs = self.context.use_defs.copy()
        new_ctx.inputs = OrderedDict({inp: None for inp in inputs})
        return new_ctx

    @staticmethod
    def _discard_unused_inputs(
        graphs: Iterable[TierkreisGraph], inputs: Iterable[str]
    ) -> None:
        for inp in inputs:
            for graph in graphs:
                if inp not in graph.inputs():
                    graph.discard(graph.input[inp])

    def visitIfBlock(self, ctx: TkslParser.IfBlockContext):
        target = ctx.target.text
        condition = self.visitOutport(ctx.condition)[0]
        inputs = self.visitOptionalNamed_map(ctx.inputs)

        ifcontext = self._cloneContextWithInputs(inputs)
        # outputs from if/else blocks have to be named map (not positional)

        ifvisit = TkslFileVisitor(self.sig, ifcontext)
        if_g = ifvisit.visitCode_block(ctx.if_block)

        elsevisit = TkslFileVisitor(self.sig, ifcontext)
        else_g = elsevisit.visitCode_block(ctx.else_block)
        self._discard_unused_inputs([if_g, else_g], ifcontext.inputs)

        sw_nod = self.graph.add_func(
            "builtin/switch", pred=condition, if_true=if_g, if_false=else_g
        )
        eval_n = self.graph.add_func("builtin/eval", thunk=sw_nod["value"], **inputs)

        output_names = set(if_g.outputs()).union(else_g.outputs())
        fake_func = FunctionDefinition(list(ifcontext.inputs), list(output_names))
        self.context.output_vars[target] = (eval_n, fake_func)

    def visitLoop(self, ctx: TkslParser.LoopContext):
        target = ctx.target.text
        port, value = self.visitPort_map(ctx.port_map())
        if port != Labels.VALUE:
            raise TkslCompileException(
                f"Loops must have a single input called '{Labels.VALUE}'"
            )

        loopcontext = self._cloneContextWithInputs({port: value})

        bodyvisit = TkslFileVisitor(self.sig, loopcontext)
        body_g = bodyvisit.visitCode_block(ctx.body)

        # This is only for loops that ignore the "value" input
        self._discard_unused_inputs([body_g], loopcontext.inputs)

        loop_nod = self.graph.add_func("builtin/loop", body=body_g, value=value)

        fake_func = FunctionDefinition(list(loopcontext.inputs), list(body_g.outputs()))
        self.context.output_vars[target] = (loop_nod, fake_func)

    # Visit a parse tree produced by TkslParser#Match.
    def visitMatch(self, ctx: TkslParser.MatchContext):
        target = ctx.target.text
        (scrutinee,) = self.visitOutport(ctx.scrutinee)
        inputs = self.visitOptionalNamed_map(ctx.inputs)
        if Labels.VALUE in inputs:
            raise TkslCompileException(
                "Cannot pass extra 'value' input as 'value' reserved for variant"
            )

        case_ctx = self._cloneContextWithInputs(inputs)
        case_ctx.inputs[Labels.VALUE] = None
        # outputs from each case have to be named map (not positional)

        cases = dict(
            TkslFileVisitor(self.sig, case_ctx).visitMatch_case(c) for c in ctx.cases
        )

        self._discard_unused_inputs(cases.values(), case_ctx.inputs)

        m = self.graph.add_match(scrutinee, **cases)
        eval_n = self.graph.add_func("builtin/eval", thunk=m[Labels.THUNK], **inputs)

        output_names = frozenset.union(
            *[frozenset(case_g.outputs()) for case_g in cases.values()]
        )
        fake_func = FunctionDefinition(list(case_ctx.inputs), list(output_names))
        self.context.output_vars[target] = (eval_n, fake_func)

    def visitEdge(self, ctx: TkslParser.EdgeContext) -> TierkreisEdge:
        return self.graph.add_edge(
            self.visitPort_label(ctx.source), self.visitPort_label(ctx.target)
        )

    def visitCode_block(self, ctx: TkslParser.Code_blockContext) -> TierkreisGraph:
        _ = list(map(self.visit, ctx.inst_list))
        return self.graph

    def visitMatch_case(
        self, ctx: TkslParser.Match_caseContext
    ) -> Tuple[str, TierkreisGraph]:
        tag = ctx.tag.text
        block = self.visitCode_block(ctx.code_block())
        return (tag, block)

    def visitGenerics(self, ctx: TkslParser.GenericsContext) -> list[VarType]:
        return [VarType(name.text) for name in ctx.gen_ids]

    def visitFuncDef(self, ctx: TkslParser.FuncDefContext):
        name = str(ctx.ID())
        vartypes = self.visitGenerics(ctx.generics()) if ctx.generics() else []

        for var in vartypes:
            self.context.aliases[var.name] = var
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
        for in_port, type_ in context.inputs.items():
            graph.annotate_input(in_port, type_)
        for out_port, type_ in context.outputs.items():
            graph.annotate_output(out_port, type_)

        self.context.functions[name] = (graph, f_def)

        # clear function typevars from global context
        for var in vartypes:
            del self.context.aliases[var.name]

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

    def visitStart(self, ctx: TkslParser.StartContext) -> FuncDefs:
        _ = list(map(self.visit, ctx.decs))

        return self.context.functions

    def visitStruct_id(self, ctx: TkslParser.Struct_idContext) -> Optional[str]:
        if ctx.TYPE_STRUCT():
            return None
        if ctx.ID():
            return str(ctx.ID())
        raise TkslCompileException()

    def visitStruct_field(
        self, ctx: TkslParser.Struct_fieldContext
    ) -> Tuple[str, TierkreisValue]:
        return str(ctx.ID()), self.visitConst_(ctx.const_())

    def visitSome(self, ctx: TkslParser.SomeContext) -> OptionValue:
        return OptionValue(self.visitConst_(ctx.const_()))

    def visitNone(self, ctx: TkslParser.NoneContext) -> OptionValue:
        return OptionValue(None)

    def visitStruct_fields(self, ctx: TkslParser.Struct_fieldsContext) -> StructValue:
        fields = dict(map(self.visitStruct_field, ctx.fields))
        return StructValue(fields)

    def visitVariant_const(self, ctx: TkslParser.Variant_constContext) -> VariantValue:
        return VariantValue(str(ctx.ID()), self.visitConst_(ctx.const_()))

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

        if ctx.pair_const():
            pair_ctx = cast(TkslParser.Pair_constContext, ctx.pair_const())
            return PairValue(
                self.visitConst_(pair_ctx.first), self.visitConst_(pair_ctx.second)
            )
        if ctx.struct_const():
            struct_ctx = ctx.struct_const()
            return self.visitStruct_fields(struct_ctx.fields)
        if ctx.opt_const():
            return self.visit(ctx.opt_const())
        if ctx.variant_const():
            return self.visitVariant_const(ctx.variant_const())
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
        if ctx.TYPE_VARIANT():
            return VariantType(Row(dict(map(self.visitF_param, ctx.variants))))
        if ctx.graph_type():
            g_type = self.visitGraph_type(ctx.graph_type()).graph_type
            assert g_type is not None
            return g_type
        if ctx.named_obj():
            namespace, name = self.visitNamed_obj(ctx.named_obj())
            if not namespace:
                if name in self.context.aliases:
                    return self.context.aliases[name]

                if name in self.context.use_defs:
                    namespace = self.context.use_defs[name]
            if namespace:
                namespace_defs = self.sig[namespace]
                try:
                    return namespace_defs.aliases[name].body
                except KeyError as e:
                    raise TkslCompileException(
                        f"Type {name} not found in namespace {namespace}"
                    ) from e

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


def _get_source(path: Union[str, Path]) -> str:
    with open(path) as f:
        return f.read()


INCLUDE_RE = re.compile(r'include!\("([^\(\);]+)"\);')


def _preprocessing(source_file: Union[str, Path]) -> str:
    path = Path(source_file)
    orig_source = _get_source(path)

    def _include(match: re.Match) -> str:
        with open(path.parent / str(match.group(1))) as f:
            return f.read()

    new_source = INCLUDE_RE.sub(_include, orig_source)
    return new_source


def load_tksl_file(
    path: Union[str, Path],
    **kwargs,
) -> TierkreisGraph:
    """Load TierkreisGraph from a tksl file. Applies preprocessing before
    parsing.
    Keyword arguments are passed to parse_tksl

    :param path: path to source file
    :type path: Union[str, Path]
    :return: Compiled tierkreis graph
    :rtype: TierkreisGraph
    """
    return parse_tksl(_preprocessing(path), **kwargs)


def _parser(source: str) -> TkslParser:
    lexer = TkslLexer(InputStream(source))
    lexer.removeErrorListeners()
    lexer.addErrorListener(ThrowingErrorListener())

    stream = CommonTokenStream(lexer)
    parser = TkslParser(stream)
    parser.removeErrorListeners()
    parser.addErrorListener(ThrowingErrorListener())

    return parser


def parse_tksl(
    source: str,
    signature: Optional[RuntimeSignature] = None,
    function_name: str = "main",
) -> TierkreisGraph:
    """Parse a tksl source file (after preprocessing) and return the "main"
    graph by default.

    :param source: Source file as string
    :type source: str
    :param signature: Runtime signature if available, defaults to None
    :type signature: Optional[RuntimeSignature], optional
    :param function_name: Runtime signature if available, defaults to "main"
    :type signature: str, optional
    :return: Graph defined as <function_name> in source
    :rtype: TierkreisGraph
    """
    signature = signature or {}
    parser = _parser(source)
    tree = parser.start()
    func_defs = TkslFileVisitor(signature, Context()).visitStart(tree)
    return func_defs[function_name][0]


def parse_struct_fields(source: str) -> StructValue:
    parser = _parser(source)
    tree = parser.struct_fields()
    return TkslFileVisitor({}, Context()).visitStruct_fields(tree)


def parse_const(source: str) -> TierkreisValue:
    tree = _parser(source).const_()
    return TkslFileVisitor({}, Context()).visitConst_(tree)
