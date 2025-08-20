"""Combinators for the Tierkreis worker IDL.

We use
https://typespec.io/docs/language-basics/models/
https://typespec.io/docs/language-basics/interfaces/
as well as an extra decorator @portmapping.
"""

from typing import NamedTuple

from tierkreis.controller.data.models import TKR_PORTMAPPING_FLAG
from tierkreis.exceptions import TierkreisError
from tierkreis.idl.parser import lit, seq
from tierkreis.idl.type_symbols import TypeParser, TypeSymbol, identifier
from tierkreis.namespace import FunctionSpec, Namespace


class TypeDecl(NamedTuple):
    name: str
    t: TypeSymbol


class Method(NamedTuple):
    name: str
    decls: list[TypeDecl]
    return_type: TypeSymbol


class Interface(NamedTuple):
    name: str
    methods: list[Method]


class Model(NamedTuple):
    id: str
    name: str
    decls: list[TypeDecl]


class SpecParser(TypeParser):
    def resolve_type(self, ref: TypeSymbol) -> type:
        if not isinstance(ref, str):
            return ref

        if ref not in self.identifier_lookup:
            raise TierkreisError(f"No such model {ref}")

        return self.identifier_lookup[ref]

    def create_spec(self, args: tuple[list[type], Interface]) -> Namespace:
        interface = args[1]

        namespace = Namespace(interface.name)
        for f in interface.methods:
            fn = FunctionSpec(f.name, interface.name, {}, [])
            ins: dict[str, TypeSymbol | TypeDecl] = {}
            for name, t in f.decls:
                ins[name] = self.resolve_type(t)
            fn.add_inputs(ins)
            fn.add_outputs(self.resolve_type(f.return_type))

            namespace._add_function_spec(fn)
        return namespace

    def add_model(self, args: tuple[str, str, list[TypeDecl]]) -> type:
        id, name, decls = args
        fields = []
        if name in self.identifier_lookup:
            raise TierkreisError(f"Model {name} already exists.")
        for arg, t in decls:
            fields.append((arg, self.resolve_type(t)))
        nt = NamedTuple(name, fields)
        if id == "@portmapping\nmodel":
            setattr(nt, TKR_PORTMAPPING_FLAG, True)
        self.identifier_lookup[name] = nt
        return nt

    def type_decl(self):
        return ((identifier << lit(":")) & self.type_symbol()).map(
            lambda x: TypeDecl(*x)
        )

    def model(self):
        return seq(
            lit("@portmapping\nmodel", "model"),
            identifier << lit("{"),
            self.type_decl().rep(lit(";")) << lit("}"),
        ).map(self.add_model)

    def method(self):
        return seq(
            identifier << lit("("),
            self.type_decl().rep(lit(",")) << lit(")") << lit(":"),
            self.type_symbol(),
        ).map(lambda x: Method(*x))

    def interface(self):
        return (
            (lit("interface") >> identifier << lit("{"))
            & self.method().rep(lit(";")) << lit("}")
        ).map(lambda x: Interface(*x))

    def spec(self):
        return (self.model().rep() & self.interface()).map(self.create_spec)
