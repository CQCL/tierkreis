from pathlib import Path
from types import NoneType
from typing import Literal, NamedTuple
from lark import Lark, Tree
from tierkreis.controller.data.models import TKR_PORTMAPPING_FLAG, PModel, PNamedModel
from tierkreis.controller.data.types import PType
from tierkreis.exceptions import TierkreisError
from tierkreis.namespace import FunctionSpec, Namespace

grammar_file = Path(__file__).parent / "interface.lark"
with open(grammar_file) as fh:
    typespec_parser = Lark(fh.read(), start="spec")


class NamespaceTransformer:
    def __init__(self) -> NoneType:
        self.model_lookup = {}

    def type_symbol(self, type_symbol: Tree) -> type[PType]:
        """Parse into allowed types. Try to support all TypeSpec built-in types.

        https://typespec.io/docs/language-basics/built-in-types/"""

        type_decl = type_symbol.children[0]
        match type_decl:
            case "integer" | "int64" | "int32" | "int16" | "int8" | "safeint":
                return int
            case "uint64" | "uint32" | "uint16" | "uint8":
                return int
            case "float" | "float32" | "float64" | "numeric":
                return float
            case "decimal" | "decimal128":
                raise TierkreisError("Decimal support not implemented yet.")
            case (
                "plainDate"
                | "plainTime"
                | "utcDateTime"
                | "offsetDateTime"
                | "duration"
            ):
                raise TierkreisError("Date support not implemented yet.")
            case "bytes":
                return bytes
            case "string" | "url":
                return str
            case "boolean":
                return bool
            case "null":
                return NoneType
            case "unknown" | "void" | "never":
                raise TierkreisError(f"Type {type_decl} not implemented yet.")
            case str():
                nt = self.model_lookup.get(type_decl)
                if nt is None:
                    raise TierkreisError(f"Expected type symbol, got {type_decl}")
                return nt

        raise TierkreisError(f"Expected type symbol, got {type_decl}")

    def var_name(self, var_name: Tree) -> str:
        name = var_name.children[0]
        if not isinstance(name, str) or not name.isidentifier():
            raise TierkreisError(f"Invalid variable name {name}.")

        return getattr(name, "value")

    def key_type_pair(self, pair: Tree) -> tuple[str, type[PModel]]:
        return (
            self.var_name(pair.children[0]),
            self.type_symbol(pair.children[1]),
        )

    def key_type_pairs(self, pairs: Tree) -> list[tuple[str, type[PModel]]]:
        return [self.key_type_pair(x) for x in pairs.children]

    def model_kw(self, model_kw: Tree) -> Literal["struct", "portmapping"]:
        kw = model_kw.children[0].data
        if kw == "struct_kw":
            return "struct"
        if kw == "portmapping_kw":
            return "portmapping"

        raise TierkreisError(f"Unknown model keyword {kw}.")

    def model(self, model: Tree) -> type[PNamedModel]:
        kw = self.model_kw(model.children[0])
        name = self.var_name(model.children[1])
        arg_list = self.key_type_pairs(model.children[2])
        nt = NamedTuple(name, arg_list)
        self.model_lookup[name] = nt
        if kw == "portmapping":
            setattr(nt, TKR_PORTMAPPING_FLAG, True)

        return nt

    def models(self, models: Tree) -> list[type[PNamedModel]]:
        return [self.model(x) for x in models.children]

    def arg(self, arg: Tree) -> tuple[str, type[PType]]:
        return (
            self.var_name(arg.children[0]),
            self.type_symbol(arg.children[1]),
        )

    def args(self, args: Tree) -> list[tuple[str, type[PType]]]:
        print(args)
        return [self.arg(x) for x in args.children]

    def return_type(self, args: Tree) -> type[PModel]:
        return self.type_symbol(args.children[0])

    def method(self, method: Tree) -> FunctionSpec:
        name = self.var_name(method.children[0])
        ins = {k: v for k, v in self.args(method.children[1])}
        ret_type = self.return_type(method.children[2])
        fn = FunctionSpec(name, "unknown", {}, [], NoneType)
        fn.add_inputs(ins)
        fn.add_outputs(ret_type)
        return fn

    def methods(self, methods: Tree) -> list[FunctionSpec]:
        return [self.method(x) for x in methods.children]

    def interface(self, interface: Tree) -> Namespace:
        name = self.var_name(interface.children[0])
        fns = self.methods(interface.children[1])
        ns = Namespace(name, {}, set())

        for f in fns:
            f.namespace = name
            ns._add_function_spec(f)

        return ns

    def spec(self, spec: Tree) -> Namespace:
        models = self.models(spec.children[0])
        namespace = self.interface(spec.children[1])

        for model in models:
            namespace._add_struct(model)
        return namespace
