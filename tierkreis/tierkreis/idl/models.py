from dataclasses import dataclass
from typing import ForwardRef

type TypeSymbol = str | ForwardRef


@dataclass
class TypeDecl:
    name: str
    t: TypeSymbol


@dataclass
class Method:
    name: str
    generics: list[str]
    args: list[TypeDecl]
    return_type: TypeSymbol
    return_type_is_portmapping: bool = False


@dataclass
class Interface:
    name: str
    methods: list[Method]


@dataclass
class Model:
    is_portmapping: bool
    name: str
    generics: list[str]
    decls: list[TypeDecl]

    def __hash__(self) -> int:
        return hash(self.name)
