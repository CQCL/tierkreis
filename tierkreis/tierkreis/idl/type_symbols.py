"""Types that are allowed in the Tierkreis worker specification IDL.

We use https://typespec.io/docs/language-basics/built-in-types/ as a guide.
"""

from types import NoneType
from typing import ForwardRef, Mapping, Sequence
from tierkreis.controller.data.types import format_ptype
from tierkreis.idl.models import format_ident
from tierkreis.idl.parser import Parser, lit, reg

type _TypeT = type | ForwardRef


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
ident = reg(r"[a-zA-Z0-9_]+")
forward_ref = ident.map(ForwardRef)
generics = (lit("<") >> ident.rep(lit(",")) << lit(">")).opt().map(lambda x: x or [])


@Parser
def array_t(ins: str) -> tuple[type, str]:
    return (lit("Array<") >> type_t_inner << lit(">")).map(lambda x: Sequence[x])(ins)


@Parser
def record_t(ins: str) -> tuple[type, str]:
    return (lit("Record<") >> type_t_inner << lit(">")).map(lambda x: Mapping[str, x])(
        ins
    )


@Parser
def generic_t(ins: str) -> tuple[ForwardRef, str]:
    return (ident & generics).map(lambda x: ForwardRef(format_ident(x[0], x[1])))(ins)


@Parser
def type_t_inner(ins: str) -> tuple[_TypeT, str]:
    return (
        integer_t
        | float_t
        | bytes_t
        | bool_t
        | none_t
        | string_t
        | array_t
        | record_t
        | generic_t
    )(ins)


type_symbol = type_t_inner.map(lambda x: format_ptype(x))
