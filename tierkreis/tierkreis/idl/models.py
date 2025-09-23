from dataclasses import dataclass
from types import NoneType
from typing import Annotated, Mapping, Self, Sequence, TypeVar, get_args, get_origin

from tierkreis.controller.data.types import _is_generic
from tierkreis.exceptions import TierkreisError

type ElementaryType = (
    type[int]
    | type[float]
    | type[bytes]
    | type[str]
    | type[bool]
    | type[NoneType]
    | type[Mapping]
    | type[Sequence]
    | str  # Custom type e.g. forward reference
)


@dataclass
class GenericType:
    origin: ElementaryType
    args: "Sequence[GenericType | str]"

    @classmethod
    def from_type(cls, t: type) -> "Self":
        if get_origin(t) is Annotated:
            return cls.from_type(get_args(t)[0])

        if _is_generic(t):
            return cls(str(t), [])

        args, origin = get_args(t), get_origin(t)
        if not args:
            return cls(t, [])

        if args and origin:
            subargs = []
            for arg in args:
                if isinstance(arg, TypeVar) or isinstance(arg, TypeVar):
                    subargs.append(str(arg))
                else:
                    subargs.append(cls.from_type(arg))

            return cls(origin, subargs)

        raise TierkreisError(f"Expected generic type. Got {t}")

    @staticmethod
    def _generics(t: "GenericType | str"):
        if _is_generic(t):
            return str(t)

        if isinstance(t, str):
            return [t]

        if t.args == []:
            return []

        outs = []
        for arg in t.args:
            outs.extend(GenericType._generics(arg))
        return outs

    def generics(self) -> list[str]:
        return GenericType._generics(self)


@dataclass
class TypedArg:
    name: str
    t: GenericType


@dataclass
class Method:
    name: GenericType
    args: list[TypedArg]
    return_type: GenericType
    return_type_is_portmapping: bool = False


@dataclass
class Interface:
    name: str
    methods: list[Method]


@dataclass
class Model:
    is_portmapping: bool
    t: GenericType
    decls: list[TypedArg]

    def __hash__(self) -> int:
        return hash(self.t.origin)
