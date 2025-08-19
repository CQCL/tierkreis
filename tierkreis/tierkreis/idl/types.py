from types import NoneType
from tierkreis.idl.parser import Parser, lit, reg

type _TypeT = int | float | bytes | bool | NoneType | str | list[_TypeT] | dict[
    str, _TypeT
]
type TypeSymbol = type[_TypeT] | str

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


def array_t(ins: str) -> tuple[type[list[_TypeT]], str]:
    return (lit("Array<") >> type_symbol << lit(">")).map(lambda x: list[x]).fn(ins)


def record_t(ins: str) -> tuple[type[dict[str, _TypeT]], str]:
    return (
        (lit("Record<") >> type_symbol << lit(">")).map(lambda x: dict[str, x]).fn(ins)
    )


def type_t_inner(ins: str) -> tuple[TypeSymbol, str]:
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


type_symbol = Parser[TypeSymbol](type_t_inner)
