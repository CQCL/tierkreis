"""Types that are allowed in the Tierkreis worker specification IDL.

We use https://typespec.io/docs/language-basics/built-in-types/ as a guide.
"""

from types import NoneType
from typing import ForwardRef, get_args
from tierkreis.idl.parser import Parser, lit, reg

type _TypeT = (
    int | float | bytes | bool | NoneType | str | list[_TypeT] | dict[str, _TypeT]
)
type TypeSymbol = str | ForwardRef

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
identifier = reg(r"[a-zA-Z0-9_]+")
forward_ref = identifier.map(ForwardRef)


@Parser
def array_t(ins: str) -> tuple[type[list[_TypeT]], str]:
    return (lit("Array<") >> type_t_inner << lit(">")).map(lambda x: list[x])(ins)


@Parser
def record_t(ins: str) -> tuple[type[dict[str, _TypeT]], str]:
    return (lit("Record<") >> type_t_inner << lit(">")).map(lambda x: dict[str, x])(ins)


@Parser
def type_t_inner(ins: str) -> tuple[type[_TypeT], str]:
    return (
        integer_t | float_t | bytes_t | bool_t | none_t | string_t | array_t | record_t
    )(ins)


def format_type(t: type) -> str:
    if get_args(t):
        return str(t)
    return t.__name__


type_symbol = type_t_inner.map(format_type) | forward_ref
