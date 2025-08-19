from types import NoneType
from typing import NamedTuple

from tierkreis.controller.data.models import TKR_PORTMAPPING_FLAG
from tierkreis.exceptions import TierkreisError
from tierkreis.idl.parser import Parser, lit, reg, seq
from tierkreis.namespace import FunctionSpec, Namespace

signed_int = lit("integer", "int64", "int32", "int16", "int8", "safeint")
unsigned_int = lit("uint64", "uint32", "uint16", "uint8")
integer_t = (signed_int | unsigned_int).coerce(int)
float_t = lit("float", "float32", "float64", "numeric").coerce(float)
bytes_t = lit("bytes").coerce(bytes)
string_t = lit("string", "url").coerce(str)
bool_t = lit("bool").coerce(bool)
none_t = lit("null").coerce(NoneType)
decimal_t = lit("decimal", "decimal128").fail("Decimal")
plain_datetime = lit("plainDate", "plainTime")
other_date = lit("utcDateTime", "offsetDateTime", "duration")
date_t = (plain_datetime | other_date).fail("Date")
unknown_t = lit("unknown", "void", "never").fail("Unknown")
identifier = reg(r"[a-zA-Z0-9_]*")

type TypeTInner = int | float | bytes | bool | NoneType | str | list[TypeTInner] | dict[
    str, TypeTInner
]
type TypeT = type[TypeTInner] | str


def array_t(ins: str) -> tuple[type[list[TypeTInner]], str]:
    return (lit("Array<") >> type_t << lit(">")).map(lambda x: list[x]).fn(ins)


def record_t(ins: str) -> tuple[type[dict[str, TypeTInner]], str]:
    return (lit("Record<") >> type_t << lit(">")).map(lambda x: dict[str, x]).fn(ins)


def type_t_inner(ins: str) -> tuple[TypeT, str]:
    return (
        integer_t
        | float_t
        | bytes_t
        | bool_t
        | none_t
        | string_t
        | array_t
        | record_t
        | identifier
    )(ins)


type_t = Parser[TypeT](type_t_inner)


class TypeDecl(NamedTuple):
    name: str
    t: TypeT


type_decl = ((identifier << lit(":")) & type_t).map(lambda x: TypeDecl(*x))


def parse_model(args: tuple[str, str, list[TypeDecl]]) -> type[NamedTuple]:
    id, name, decls = args
    a = [(x.name, x.t) for x in decls]
    nt = NamedTuple(name, a)
    if id == "portmapping":
        setattr(nt, TKR_PORTMAPPING_FLAG, True)
    return nt


model = seq(
    lit("portmapping", "struct"),
    identifier << lit("{"),
    type_decl.rep(lit(";")) << lit("}"),
).map(parse_model)


class Method(NamedTuple):
    name: str
    decls: list[TypeDecl]
    return_type: TypeT


method = seq(
    identifier << lit("("), type_decl.rep(lit(",")) << lit(")") << lit(":"), type_t
).map(lambda x: Method(*x))


class Interface(NamedTuple):
    name: str
    methods: list[Method]


interface = (
    (lit("interface") >> identifier << lit("{")) & method.rep(lit(";")) << lit("}")
).map(lambda x: Interface(*x))


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


spec = (model.rep() & interface).map(create_spec)
