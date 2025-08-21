from dataclasses import dataclass
from typing import ForwardRef, Self, get_args, get_origin

from tierkreis.controller.data.types import format_ptype


type TypeSymbol = str | ForwardRef
type Generics = list[str]


@dataclass
class GenericType:
    t: TypeSymbol
    generics: Generics

    @classmethod
    def from_type(cls, t: type) -> "Self":
        origin, args = get_origin(t), get_args(t)
        if origin is None:
            ts = t.__name__
        else:
            ts = format_ptype(t)
            args = []
        return cls(ts, list(args))


@dataclass
class TypeDecl:
    name: str
    t: GenericType

    @classmethod
    def from_annotation(cls, k: str, t: type) -> "Self":
        return cls(k, GenericType.from_type(t))


@dataclass
class Method:
    name: str
    generics: Generics
    args: list[TypeDecl]
    return_type: GenericType
    return_type_is_portmapping: bool = False


@dataclass
class Interface:
    name: str
    methods: list[Method]


@dataclass
class Model:
    is_portmapping: bool
    name: str
    generics: Generics
    decls: list[TypeDecl]

    def __hash__(self) -> int:
        return hash(self.name)
