from types import NoneType
from tierkreis.controller.data.core import PortID, TModel, TType, is_namedtuple_model
from tierkreis.namespace import FunctionSpec, Namespace


def format_ttype(ttype: type[TType], is_constructor: bool = False) -> str:
    if issubclass(ttype, int):
        return "IntRef" if is_constructor else "int"
    elif issubclass(ttype, str):
        return "StrRef" if is_constructor else "str"
    elif issubclass(ttype, float):
        return "FloatRef" if is_constructor else "float"
    elif (
        issubclass(ttype, bytes)
        or issubclass(ttype, bytearray)
        or issubclass(ttype, memoryview)
    ):
        return "BytesRef" if is_constructor else "bytes"

    elif issubclass(ttype, list):
        return ""
    elif ttype is NoneType:
        return "None"
    else:
        return f'DictConvertibleRef[Literal["{ttype.__qualname__}"]]'


def format_annotation(
    port_id: PortID, tk_type: type[TType], is_constructor: bool = False
) -> str:
    sep = "=" if is_constructor else ":"
    constructor = f'.from_value_ref(n, "{port_id}")' if is_constructor else ""
    return f"{port_id}{sep} {format_ttype(tk_type, is_constructor)}{constructor}"


def format_output(fn_name: str, outputs: type[TModel], is_ref: bool = False) -> str:
    if is_namedtuple_model(outputs):
        return f"{fn_name.title()}Output"
    if is_ref:
        return format_ttype(outputs, True)  # type:ignore
    return outputs.__qualname__


def format_output_class(fn_name: str, outputs: type[TModel]) -> str:
    if not is_namedtuple_model(outputs):
        return ""

    outs = {format_annotation(k, v) for k, v in outputs.__annotations__.items()}
    outs_str = "\n    ".join(outs)

    out_constructor = {
        format_annotation(k, v, True) for k, v in outputs.__annotations__.items()
    }
    out_constructor_str = ",\n            ".join(out_constructor)
    return f"""
class {fn_name.title()}Output(NamedTuple):
    {outs_str}

    @staticmethod
    def from_value_ref(n: NodeIndex, p: PortID) -> "{fn_name.title()}Output":
        return {fn_name.title()}Output(
            {out_constructor_str}
        )

"""


def format_function(namespace_name: str, fn: FunctionSpec) -> str:
    ins = [format_annotation(k, v) for k, v in fn.ins.items()]
    ins_str = "\n    ".join(ins)
    class_name = format_output(fn.name, fn.outs)
    class_name_ref = format_output(fn.name, fn.outs, True)
    return f"""{format_output_class(fn.name, fn.outs)}
class {fn.name}(NamedTuple):
    {ins_str}

    @staticmethod
    def out(idx: NodeIndex) -> {class_name}:
        return {class_name_ref}.from_value_ref(idx, "value")

    @property
    def namespace(self) -> str:
        return "{namespace_name}" """


def format_namespace(namespace: Namespace) -> str:
    functions = [format_function(namespace.name, f) for f in namespace.functions]
    functions_str = "\n\n".join(functions)

    return f'''"""Code generated from {namespace.name} namespace. Please do not edit."""

from typing import Literal, NamedTuple
import typing
from tierkreis.controller.data.core import TKRRef, Function, NodeIndex, PortID
from tierkreis.controller.data.refs import IntRef, StrRef, FloatRef, BytesRef, ListRef, DictConvertibleRef

{functions_str}
    '''
