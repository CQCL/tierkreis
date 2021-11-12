"""Namespace class for holding namespace definitions of python Tierkreis worker."""

import dataclasses
import typing
from dataclasses import dataclass, make_dataclass
from functools import wraps
from inspect import getdoc, isclass
from typing import Awaitable, Callable, Dict, List, Optional, Type, Union, cast

import opentelemetry.context  # type: ignore
import opentelemetry.propagate  # type: ignore
import opentelemetry.trace  # type: ignore
from tierkreis.core.function import TierkreisFunction
from tierkreis.core.tierkreis_struct import TierkreisStruct
from tierkreis.core.types import (
    Constraint,
    GraphType,
    Kind,
    Row,
    StarKind,
    StructType,
    TierkreisType,
    TypeScheme,
)
from tierkreis.core.values import StructValue, TierkreisValue
from tierkreis.worker.exceptions import (
    DecodeInputError,
    EncodeOutputError,
    NodeExecutionError,
)

tracer = opentelemetry.trace.get_tracer(__name__)


@dataclass
class Function:
    """Registered python function."""

    run: Callable[[StructValue], Awaitable[StructValue]]
    declaration: TierkreisFunction


def _snake_to_pascal(name: str) -> str:
    return name.replace("_", " ").title().replace(" ", "")


def _get_base_tkstruct(class_type: Type) -> Type:
    origin = typing.get_origin(class_type)
    return origin if origin is not None else class_type


def _get_ordered_names(struct: Type) -> List[str]:
    tk_cls = _get_base_tkstruct(struct)
    return [field.name for field in dataclasses.fields(tk_cls)]


# Convert the type vars to names
def _type_var_to_name(type_var: Union[str, typing.TypeVar]) -> str:
    if isinstance(type_var, typing.TypeVar):
        return type_var.__name__
    return type_var


def _check_tkstruct_hint(hint: Type) -> bool:
    tk_cls = _get_base_tkstruct(hint)
    return (
        tk_cls is not None and isclass(tk_cls) and issubclass(tk_cls, TierkreisStruct)
    )


class Namespace:
    """Namespace containing Tierkreis Functions"""

    name: str
    functions: dict[str, Function]
    aliases: dict[str, TypeScheme]

    def __init__(self, name: str):
        self.name = name
        self.functions = {}
        self.aliases = {}

    def add_alias(self, name, type_: Type) -> Type:
        self.aliases[name] = TypeScheme({}, [], TierkreisType.from_python(type_))
        return type_

    def add_named_struct(self, name, type_: Type) -> Type:
        tk_type = TierkreisType.from_python(type_)
        if not isinstance(tk_type, StructType):
            raise ValueError(f"{type_} cannot be converted to a Tierkreis Struct Type.")
        tk_type.name = name
        self.aliases[name] = TypeScheme({}, [], tk_type)
        return type_

    def function(
        self,
        name: Optional[str] = None,
        constraints: Optional[List[Constraint]] = None,
        type_vars: Optional[Dict[Union[str, typing.TypeVar], Kind]] = None,
    ):
        """Decorator to mark python function as available Namespace."""

        def decorator(func):
            func_name = name or func.__name__

            # Get input and output type hints
            type_hints = typing.get_type_hints(func)

            if "return" not in type_hints:
                raise ValueError("Tierkreis function needs return type hint.")
            return_hint = type_hints.pop("return")

            struct_input = "inputs" in type_hints and _check_tkstruct_hint(
                type_hints["inputs"]
            )

            hint_inputs: Type = (
                type_hints["inputs"]
                if struct_input
                else make_dataclass(
                    f"{_snake_to_pascal(func_name)}Inputs", type_hints.items()
                )
            )

            struct_output = _check_tkstruct_hint(return_hint)
            hint_outputs: Type = (
                return_hint
                if struct_output
                else make_dataclass(
                    f"{_snake_to_pascal(func_name)}Outputs", [("value", return_hint)]
                )
            )

            # Convert type hints into tierkreis types
            type_inputs = Row.from_python(hint_inputs)
            type_outputs = Row.from_python(hint_outputs)

            # Wrap function with input and output conversions
            @wraps(func)
            async def wrapped_func(inputs: StructValue) -> StructValue:
                try:
                    with tracer.start_as_current_span("decoding inputs to python type"):
                        python_inputs = (
                            {"inputs": inputs.to_python(hint_inputs)}
                            if struct_input
                            else {
                                name: val.to_python(type_hints[name])
                                for name, val in inputs.values.items()
                            }
                        )
                except Exception as error:
                    raise DecodeInputError(str(error)) from error

                try:
                    python_outputs = await func(**python_inputs)
                except Exception as error:
                    raise NodeExecutionError(error) from error

                try:
                    with tracer.start_as_current_span(
                        "encoding outputs from python type"
                    ):
                        outputs = TierkreisValue.from_python(python_outputs)
                except Exception as error:
                    raise EncodeOutputError(str(error)) from error
                return (
                    cast(StructValue, outputs)
                    if struct_output
                    else StructValue({"value": outputs})
                )

            type_vars_by_name = (
                {_type_var_to_name(var): kind for var, kind in type_vars.items()}
                if type_vars
                else {}
            )

            type_vars_by_name.update(
                {name: StarKind() for name in type_inputs.contained_vartypes()}
            )
            type_vars_by_name.update(
                {name: StarKind() for name in type_outputs.contained_vartypes()}
            )

            # Construct the type schema of the function
            type_scheme = TypeScheme(
                constraints=constraints or [],
                variables=type_vars_by_name,
                body=GraphType(
                    inputs=type_inputs,
                    outputs=type_outputs,
                ),
            )

            self.functions[func_name] = Function(
                run=wrapped_func,
                declaration=TierkreisFunction(
                    func_name,
                    type_scheme=type_scheme,
                    docs=getdoc(func) or "",
                    input_order=_get_ordered_names(hint_inputs),
                    output_order=_get_ordered_names(hint_outputs),
                ),
            )
            return func

        return decorator
