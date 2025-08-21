"""Combinators for the Tierkreis worker IDL.

We use
https://typespec.io/docs/language-basics/models/
https://typespec.io/docs/language-basics/interfaces/
as well as an extra decorator @portmapping.
"""

from typing import ForwardRef
from tierkreis.idl.models import GenericType, Interface, Method, Model, TypeDecl

from tierkreis.idl.parser import lit, seq
from tierkreis.idl.type_symbols import ident, type_symbol
from tierkreis.namespace import Namespace


def create_spec(args: tuple[list[Model], Interface]) -> Namespace:
    models = args[0]
    interface = args[1]
    namespace = Namespace(interface.name)

    [namespace.models.add(m) for m in models]

    for f in interface.methods:
        if isinstance(f.return_type.t, ForwardRef):
            model = next(x for x in models if x.name == f.return_type.t.__forward_arg__)
            f.return_type_is_portmapping = model.is_portmapping
        namespace.methods[f.name] = f
        namespace.generics.update(f.generics)

    return namespace


generics = (lit("<") >> ident.rep(lit(",")) << lit(">")).opt().map(lambda x: x or [])
generic_type = (type_symbol & generics).map(lambda x: GenericType(*x))
type_decl = ((ident << lit(":")) & generic_type).map(lambda x: TypeDecl(*x))
model = seq(
    lit("@portmapping").opt().map(lambda x: x is not None) << lit("model"),
    ident,
    generics,
    lit("{") >> type_decl.rep(lit(";")) << lit("}"),
).map(lambda x: Model(*x))
method = seq(
    ident,
    generics,
    lit("(") >> type_decl.rep(lit(",")) << lit(")") << lit(":"),
    generic_type,
).map(lambda x: Method(*x))
interface = (
    (lit("interface") >> ident << lit("{")) & method.rep(lit(";")) << lit("}")
).map(lambda x: Interface(*x))
spec = (model.rep() & interface).map(create_spec)
