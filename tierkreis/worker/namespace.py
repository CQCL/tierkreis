"""Namespace class for holding namespace definitions of python Tierkreis worker."""

import dataclasses
import typing
from ctypes import ArgumentError
from dataclasses import dataclass, make_dataclass
from functools import wraps
from inspect import getdoc, isclass
from typing import Awaitable, Callable, Dict, List, Mapping, Optional, Type, Union, cast

from tierkreis.client.runtime_client import RuntimeClient
from tierkreis.core.function import FunctionDeclaration, FunctionName
from tierkreis.core.signature import Namespace as SigNamespace
from tierkreis.core.signature import Signature
from tierkreis.core.tierkreis_graph import Location
from tierkreis.core.types import (
    Constraint,
    GraphType,
    Kind,
    Row,
    StarKind,
    StructType,
    TierkreisType,
    TypeScheme,
    UnpackRow,
)
from tierkreis.core.values import (
    StructValue,
    TierkreisValue,
)
from tierkreis.worker.exceptions import (
    DecodeInputError,
    EncodeOutputError,
    NamespaceClash,
    NodeExecutionError,
)

from .tracing import get_tracer, span

tracer = get_tracer(__name__)


@dataclass
class Function:
    """Registered python function.
    The second (bytes) argument is an encoded stack-trace."""

    run: Callable[[RuntimeClient, bytes, StructValue], Awaitable[StructValue]]
    declaration: FunctionDeclaration


def _snake_to_pascal(name: str) -> str:
    return name.replace("_", " ").title().replace(" ", "")


def _get_base_tkstruct(class_type: Type) -> Type:
    origin = cast(Type, typing.get_origin(class_type))
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
    return tk_cls is not None and isclass(tk_cls) and issubclass(tk_cls, UnpackRow)


class Namespace(Mapping[str, "Namespace"]):
    """Namespace containing Tierkreis Functions"""

    functions: dict[str, Function]
    aliases: dict[str, TypeScheme]
    subspaces: dict[str, "Namespace"]

    def __init__(self):
        self.functions = {}
        self.aliases = {}
        self.subspaces = {}

    def __getitem__(self, __k: str) -> "Namespace":
        return self.subspaces.setdefault(__k, Namespace())

    def __iter__(self):
        return self.subspaces.__iter__()

    def __len__(self):
        return self.subspaces.__len__()

    def merge_namespace(self, other: "Namespace"):
        self._merge_namespace(other, [])

    def _merge_namespace(self, other: "Namespace", prefix: list[str]):
        """Merges other namespace into self"""
        intersect = self.functions.keys() & other.functions.keys()
        if intersect:
            raise NamespaceClash(prefix, intersect)
        self.functions = other.functions | self.functions
        for k, v in other.subspaces.items():
            if (x := self.subspaces.get(k)) is None:
                self.subspaces[k] = v
            else:
                x._merge_namespace(v, prefix + ["k"])

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

    def extract_contents(self) -> SigNamespace:
        return SigNamespace(
            functions={k: v.declaration for k, v in self.functions.items()},
            subspaces={k: v.extract_contents() for k, v in self.subspaces.items()},
        )

    def extract_aliases(self) -> dict[str, TypeScheme]:
        return self.aliases | {
            f"{name}::{k}": v
            for name, ns in self.subspaces.items()
            for k, v in ns.extract_aliases().items()
        }

    def extract_signature(self, can_scope: bool) -> Signature:
        return Signature(
            root=self.extract_contents(),
            aliases=self.extract_aliases(),
            scopes=[Location([])] if can_scope else [],
        )

    def get_function(self, name: FunctionName) -> Optional[Function]:
        ns = self
        for x in name.namespaces:
            if (subns := ns.subspaces.get(x)) is None:
                return None
            ns = subns
        return ns.functions.get(name.name)

    def function(
        self,
        name: Optional[str] = None,
        constraints: Optional[List[Constraint]] = None,
        type_vars: Optional[Dict[Union[str, typing.TypeVar], Kind]] = None,
        callback: bool = False,
        pass_stack: bool = False,
    ) -> Callable[[Callable], Callable]:
        """Decorator to mark python function as available Namespace."""

        def decorator(func: Callable) -> Callable:
            func_name = name or func.__name__

            # Get input and output type hints
            type_hints = typing.get_type_hints(func)

            if "return" not in type_hints:
                raise ValueError("Tierkreis function needs return type hint.")
            return_hint = type_hints.pop("return")

            struct_input = "inputs" in type_hints and _check_tkstruct_hint(
                type_hints["inputs"]
            )

            if callback:
                try:
                    type_hints.pop("client")
                except KeyError:
                    raise ArgumentError(
                        "Functions with callbacks must have an argument 'client'"
                    )

            if pass_stack:
                try:
                    type_hints.pop("stack")
                except KeyError:
                    raise ArgumentError(
                        "Functions asking for stack trace must have an argument 'stack'"
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

            # Wrap function with input and output conversions
            @wraps(func)
            async def wrapped_func(
                runtime: RuntimeClient,
                stack_trace: bytes,
                inputs: StructValue,
            ) -> StructValue:
                try:
                    with span(tracer, name="decoding inputs to python type"):
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

                if callback:
                    python_inputs["client"] = runtime
                if pass_stack:
                    python_inputs["stack"] = stack_trace
                try:
                    python_outputs = await func(**python_inputs)
                except Exception as error:
                    raise NodeExecutionError(error) from error

                try:
                    with span(tracer, name="encoding outputs from python type"):
                        return_type = hint_outputs if struct_output else return_hint
                        outputs = TierkreisValue.from_python(
                            python_outputs, return_type
                        )

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

            # Convert type hints into tierkreis types
            type_inputs = Row.from_python(hint_inputs)
            type_outputs = Row.from_python(hint_outputs)
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
                declaration=FunctionDeclaration(
                    type_scheme=type_scheme.to_proto(),
                    description=getdoc(func) or "",
                    input_order=_get_ordered_names(hint_inputs),
                    output_order=_get_ordered_names(hint_outputs),
                ),
            )
            return func

        return decorator
