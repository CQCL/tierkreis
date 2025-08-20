"""Combinators for the Tierkreis worker IDL.

We use
https://typespec.io/docs/language-basics/models/
https://typespec.io/docs/language-basics/interfaces/
as well as an extra decorator @portmapping.
"""

from typing import ForwardRef, NamedTuple
from typing_extensions import evaluate_forward_ref

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


class Model(NamedTuple):
    id: str
    name: str
    decls: list[TypeDecl]


def resolve_type(ref: TypeSymbol, model_dict: dict[str, type]) -> type:
    if not isinstance(ref, ForwardRef):
        return ref

    return evaluate_forward_ref(ref, locals=model_dict)


def convert_models(models: list[Model]) -> dict[str, type]:
    model_dict = {}

    for model in models:
        fields = []
        if model.name in model_dict:
            raise TierkreisError(f"Model {model.name} already exists.")
        for arg, t in model.decls:
            fields.append((arg, resolve_type(t, model_dict)))
        nt = NamedTuple(model.name, fields)
        if model.id == "@portmapping\nmodel":
            setattr(nt, TKR_PORTMAPPING_FLAG, True)
        model_dict[model.name] = nt

    return model_dict


def create_spec(args: tuple[list[Model], Interface]) -> Namespace:
    model_dict = convert_models(args[0])
    interface = args[1]

    namespace = Namespace(interface.name)
    for f in interface.methods:
        fn = FunctionSpec(f.name, interface.name, {}, [])
        ins: dict[str, TypeSymbol | TypeDecl] = {}
        for name, t in f.decls:
            ins[name] = resolve_type(t, model_dict)
        fn.add_inputs(ins)
        fn.add_outputs(resolve_type(f.return_type, model_dict))

        namespace._add_function_spec(fn)
    return namespace


type_decl = ((identifier << lit(":")) & type_symbol).map(lambda x: TypeDecl(*x))
model = seq(
    lit("@portmapping\nmodel", "model"),
    identifier << lit("{"),
    type_decl.rep(lit(";")) << lit("}"),
).map(lambda x: Model(*x))
method = seq(
    identifier << lit("("), type_decl.rep(lit(",")) << lit(")") << lit(":"), type_symbol
).map(lambda x: Method(*x))
interface = (
    (lit("interface") >> identifier << lit("{")) & method.rep(lit(";")) << lit("}")
).map(lambda x: Interface(*x))
spec = (model.rep() & interface).map(create_spec)
