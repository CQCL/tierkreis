from typing import ForwardRef, NamedTuple


class TypeDecl(NamedTuple):
    name: str
    t: type | ForwardRef


class Method(NamedTuple):
    name: str
    decls: list[TypeDecl]
    return_type: type | ForwardRef


class Interface(NamedTuple):
    name: str
    methods: list[Method]


class Model(NamedTuple):
    id: str
    name: str
    decls: list[TypeDecl]
