"""Combinators for the Tierkreis worker IDL.

We use
https://typespec.io/docs/language-basics/models/
https://typespec.io/docs/language-basics/interfaces/
as well as an extra decorator @portmapping.
"""

from typing import ForwardRef, NamedTuple
from tierkreis.idl.models import Interface, Method, Model, TypeDecl
from typing_extensions import evaluate_forward_ref

from tierkreis.controller.data.models import TKR_PORTMAPPING_FLAG
from tierkreis.exceptions import TierkreisError
from tierkreis.idl.parser import lit, seq
from tierkreis.idl.type_symbols import TypeSymbol, identifier, type_symbol
from tierkreis.namespace import Namespace


def resolve_type(ref: TypeSymbol, model_dict: dict[str, type]) -> type:
    if not isinstance(ref, ForwardRef):
        return ref

    return evaluate_forward_ref(ref, locals=model_dict)


def convert_models(models: list[Model]) -> dict[str, type]:
    model_dict = {}

    for model in models:
        if model.name in model_dict:
            raise TierkreisError(f"Model {model.name} already exists.")
        nt = NamedTuple(model.name, model.decls)
        if model.is_portmapping:
            setattr(nt, TKR_PORTMAPPING_FLAG, True)
        model_dict[model.name] = nt

    return model_dict


def create_spec(args: tuple[list[Model], Interface]) -> Namespace:
    models = args[0]
    interface = args[1]
    namespace = Namespace(interface.name)

    [namespace.models.add(m) for m in models]

    for f in interface.methods:
        namespace.methods[f.name] = f

    return namespace


generics = lit("<") >> identifier.rep(lit(",")) << lit(">")
type_decl = ((identifier << lit(":")) & type_symbol).map(lambda x: TypeDecl(*x))
model = seq(
    lit("@portmapping").opt().map(lambda x: x is not None) << lit("model"),
    identifier,
    generics.opt(),
    lit("{") >> type_decl.rep(lit(";")) << lit("}"),
).map(lambda x: Model(*x))
method = seq(
    identifier,
    generics.opt(),
    lit("(") >> type_decl.rep(lit(",")) << lit(")") << lit(":"),
    type_symbol,
).map(lambda x: Method(*x))
interface = (
    (lit("interface") >> identifier << lit("{")) & method.rep(lit(";")) << lit("}")
).map(lambda x: Interface(*x))
spec = (model.rep() & interface).map(create_spec)
