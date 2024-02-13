from dataclasses import dataclass, field

import tierkreis.core.protos.tierkreis.v1alpha1.graph as pg
import tierkreis.core.protos.tierkreis.v1alpha1.signature as ps
from tierkreis.core.function import FunctionDeclaration
from tierkreis.core.tierkreis_graph import Location
from tierkreis.core.types import TypeScheme
from tierkreis.core.utils import map_vals


@dataclass(frozen=True)
class Namespace:
    functions: dict[str, FunctionDeclaration]
    subspaces: dict[str, "Namespace"] = field(default_factory=dict)

    @classmethod
    def from_proto(cls, ps_entry: ps.Namespace) -> "Namespace":
        return cls(
            map_vals(ps_entry.functions, lambda v: v.decl),
            map_vals(ps_entry.subspaces, Namespace.from_proto),
        )

    def to_proto(self) -> ps.Namespace:
        return ps.Namespace(
            functions=map_vals(
                self.functions,
                lambda v: ps.NamespaceItem(
                    decl=v, locations=[pg.Location(location=[])]
                ),
            ),
            subspaces=map_vals(self.subspaces, lambda v: v.to_proto()),
        )

    def get(self, ns: list[str]):
        return self if ns == [] else self.subspaces[ns[0]].get(ns[1:])

    def all_namespaces(self) -> list[list[str]]:
        root: list[list[str]] = [[]]
        return root + [
            [k] + x for k, v in self.subspaces.items() for x in v.all_namespaces()
        ]

    @classmethod
    def empty(cls) -> "Namespace":
        return cls({})


@dataclass(frozen=True)
class Signature:
    root: Namespace
    aliases: dict[str, TypeScheme] = field(default_factory=dict)
    scopes: list[Location] = field(default_factory=list)

    @classmethod
    def from_proto(cls, ps_entry: ps.ListFunctionsResponse) -> "Signature":
        return cls(
            Namespace.from_proto(ps_entry.root),
            {k: TypeScheme.from_proto(v) for k, v in ps_entry.aliases.items()},
            ps_entry.scopes,
        )

    def to_proto(self) -> ps.ListFunctionsResponse:
        return ps.ListFunctionsResponse(
            root=self.root.to_proto(),
            aliases=map_vals(self.aliases, lambda v: v.to_proto()),
            scopes=self.scopes,
        )

    @classmethod
    def empty(cls) -> "Signature":
        return cls(Namespace.empty())
