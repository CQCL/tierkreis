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
from tierkreis.idl.type_symbols import TypeSymbol, identifier, type_symbol
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


def parse_model(args: tuple[str, str, list[TypeDecl]]) -> type[NamedTuple]:
    id, name, decls = args
    a = [(x.name, x.t) for x in decls]
    nt = NamedTuple(name, a)
    if id == "@portmapping\nmodel":
        setattr(nt, TKR_PORTMAPPING_FLAG, True)
    return nt


def create_spec(args: tuple[list[type[NamedTuple]], Interface]) -> Namespace:
    models = {f.__name__: f for f in args[0]}
    interface = args[1]

    namespace = Namespace(interface.name)
    for f in interface.methods:
        fn = FunctionSpec(f.name, interface.name, {}, [])
        ins = {}
        for name, t in f.decls:
            if isinstance(t, str):
                t = models.get(t)
                if t is None:
                    raise TierkreisError(f"No such model {name}")
            ins[name] = t
        fn.add_inputs(ins)

        if isinstance(f.return_type, str):
            t = models.get(f.return_type)
            if t is None:
                raise TierkreisError(f"No such model {f.return_type}")
            fn.add_outputs(t)
        else:
            fn.add_outputs(f.return_type)

        namespace._add_function_spec(fn)
    return namespace


type_decl = ((identifier << lit(":")) & type_symbol).map(lambda x: TypeDecl(*x))
model = seq(
    lit("@portmapping\nmodel", "model"),
    identifier << lit("{"),
    type_decl.rep(lit(";")) << lit("}"),
).map(parse_model)
method = seq(
    identifier << lit("("), type_decl.rep(lit(",")) << lit(")") << lit(":"), type_symbol
).map(lambda x: Method(*x))
interface = (
    (lit("interface") >> identifier << lit("{")) & method.rep(lit(";")) << lit("}")
).map(lambda x: Interface(*x))
spec = (model.rep() & interface).map(create_spec)
