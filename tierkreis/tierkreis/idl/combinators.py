import re
from types import NoneType
from typing import Callable, NamedTuple, overload

from tierkreis.controller.data.models import TKR_PORTMAPPING_FLAG
from tierkreis.exceptions import TierkreisError
from tierkreis.namespace import FunctionSpec, Namespace


class ParserError(Exception): ...


class Parser[T]:
    def __init__(self, fn: Callable[[str], tuple[T, str]]) -> NoneType:
        def f(ins: str):
            ins = ins.strip()
            return fn(ins)

        self.fn = f

    def __call__(self, ins: str) -> tuple[T, str]:
        return self.fn(ins)

    def __or__[S](
        self, other: "Parser[S]" | Callable[[str], tuple[S, str]]
    ) -> "Parser[T|S]":
        def f(ins: str):
            try:
                return self(ins)
            except:
                return other(ins)

        return Parser(f)

    def __and__[S](self, other: "Parser[S]") -> "Parser[tuple[T,S]]":
        def f(ins: str):
            s, remaining = self(ins)
            t, remaining = other(remaining)
            return (s, t), remaining

        return Parser(f)

    def __lshift__[S](self, other: "Parser[S]") -> "Parser[T]":
        def f(ins: str):
            t, remaining = self(ins)
            _, remaining = other(remaining)
            return t, remaining

        return Parser(f)

    def __rshift__[S](self, other: "Parser[S]") -> "Parser[S]":
        def f(ins: str):
            _, remaining = self(ins)
            s, remaining = other(remaining)
            return s, remaining

        return Parser(f)

    def map[A](self, fn: Callable[[T], A]) -> "Parser[A]":
        def f(ins: str):
            t, remaining = self(ins)
            return fn(t), remaining

        return Parser(f)

    def coerce[A](self, a: A) -> "Parser[A]":
        def f(ins: str):
            t, remaining = self(ins)
            return a, remaining

        return Parser(f)

    def rep(self, sep: "Parser[str] | None" = None) -> "Parser[list[T]]":
        def f(ins: str):
            outs: list[T] = []
            while True:
                try:
                    t, ins = self(ins)
                    if sep:
                        try:
                            _, ins = sep(ins)
                        except ParserError:
                            pass
                    outs.append(t)
                except ParserError:
                    break
            return outs, ins

        return Parser(f)


@overload
def seq[A, B](*args: *tuple[Parser[A], Parser[B]]) -> Parser[tuple[A, B]]: ...
@overload
def seq[A, B, C](
    *args: *tuple[Parser[A], Parser[B], Parser[C]],
) -> Parser[tuple[A, B, C]]: ...
@overload
def seq[A, B, C, D](
    *args: *tuple[Parser[A], Parser[B], Parser[C], Parser[D]],
) -> Parser[tuple[A, B, C, D]]: ...
def seq(*args: Parser) -> Parser[tuple]:
    def f(ins: str):
        outs = []
        for arg in args:
            s, ins = arg(ins)
            outs.append(s)
        return tuple(outs), ins

    return Parser(f)


# TODO: use typevar tuple here
def lit(*args: str) -> Parser[str]:
    def f(ins: str):
        for a in args:
            if ins.startswith(a):
                return a, ins[len(a) :]

        raise ParserError(f"lit: expected {args} found '{ins[:20]}'")

    return Parser(f)


def reg(regex: str) -> Parser[str]:
    def f(ins: str):
        r = re.compile("^(" + regex + ")")

        if a := r.match(ins):
            return a.group(0), ins[a.end() :]

        raise ParserError(f"reg: expected regex {regex} found '{ins[:20]}'")

    return Parser(f)


signed_int = lit("integer", "int64", "int32", "int16", "int8", "safeint")
unsigned_int = lit("uint64", "uint32", "uint16", "uint8")
integer_t = (signed_int | unsigned_int).coerce(int)
float_t = lit("float", "float32", "float64", "numeric").coerce(float)
bytes_t = lit("bytes").coerce(bytes)
string_t = lit("string", "url").coerce(str)
bool_t = lit("bool").coerce(bool)
none_t = lit("null").coerce(NoneType)

# decimal_t = lit("decimal", "decimal128") > fail("Decimal not implemented.")
# date_t = lit(
#     "plainDate", "plainTime", "utcDateTime", "offsetDateTime", "duration"
# ) > fail("Date not implemented.")
# unknown_t = lit("unknown", "void", "never") > (TierkreisError)

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


type_t: Parser[TypeT] = Parser(type_t_inner)


class TypeDecl(NamedTuple):
    name: str
    t: TypeT


type_decl = ((identifier << lit(":")) & type_t).map(lambda x: TypeDecl(*x))


def parse_model(args: tuple[tuple[str, str], list[TypeDecl]]) -> type[NamedTuple]:
    (id, name), decls = args
    a = [(x.name, x.t) for x in decls]
    nt = NamedTuple(name, a)
    if id == "portmapping":
        setattr(nt, TKR_PORTMAPPING_FLAG, True)
    return nt


model = (
    lit("portmapping", "struct")
    & identifier << lit("{")
    & type_decl.rep(lit(";")) << lit("}")
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
