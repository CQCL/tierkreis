from dataclasses import dataclass


type TypeSymbol = str
type Generics = list[str]


@dataclass
class TypeDecl:
    name: str
    t: TypeSymbol


@dataclass
class Method:
    name: str
    generics: Generics
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
    generics: Generics
    decls: list[TypeDecl]

    def __hash__(self) -> int:
        return hash(self.name)


def format_ident(name: str, generics: list[str]):
    g = f"[{', '.join(generics)}]" if generics else ""
    return f"{name}{g}"
