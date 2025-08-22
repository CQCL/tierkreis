from dataclasses import dataclass
from types import NoneType
from typing import Mapping, Sequence

type ElementaryType = (
    type[int]
    | type[float]
    | type[bytes]
    | type[str]
    | type[bool]
    | type[NoneType]
    | type[Mapping]
    | type[Sequence]
    | str
)


@dataclass
class GenericType:
    origin: ElementaryType
    args: "Sequence[GenericType | str]"


type Generics = list[str]


@dataclass
class TypeDecl:
    name: str
    t: GenericType


@dataclass
class Method:
    name: GenericType
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
    t: GenericType
    decls: list[TypeDecl]

    def __hash__(self) -> int:
        return hash(self.t.origin)


def format_ident(name: str, generics: list[str]):
    g = f"[{', '.join(generics)}]" if generics else ""
    return f"{name}{g}"
