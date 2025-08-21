from typing import ForwardRef, NamedTuple


class TypeDecl(NamedTuple):
    name: str
    t: type | ForwardRef


class Method(NamedTuple):
    name: str
    generics: list[str] | None
    decls: list[TypeDecl]
    return_type: type | ForwardRef


class Interface(NamedTuple):
    name: str
    methods: list[Method]


class Model(NamedTuple):
    is_portmapping: bool
    name: str
    generics: list[str] | None
    decls: list[TypeDecl]

    def __hash__(self) -> int:
        return hash(self.name)
