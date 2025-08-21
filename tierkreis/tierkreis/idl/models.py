from typing import NamedTuple

from tierkreis.idl.type_symbols import TypeSymbol


class TypeDecl(NamedTuple):
    name: str
    t: TypeSymbol


class Method(NamedTuple):
    name: str
    generics: list[str]
    args: list[TypeDecl]
    return_type: TypeSymbol
    return_type_is_portmapping: bool = False


class Interface(NamedTuple):
    name: str
    methods: list[Method]


class Model(NamedTuple):
    is_portmapping: bool
    name: str
    generics: list[str]
    decls: list[TypeDecl]

    def __hash__(self) -> int:
        return hash(self.name)
