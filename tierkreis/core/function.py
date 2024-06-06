"""FunctionName class."""

from dataclasses import dataclass, field
from typing import List

import tierkreis.core.protos.tierkreis.v1alpha1.graph as pg
import tierkreis.core.protos.tierkreis.v1alpha1.signature as ps


@dataclass
class FunctionName:
    """A unique identifier for a function, specified by it's name and the
    qualified namespace it belongs to.
    """

    name: str
    namespaces: List[str] = field(default_factory=list)

    @classmethod
    def from_proto(cls, pg_entry: pg.FunctionName) -> "FunctionName":
        return cls(
            pg_entry.name,
            pg_entry.namespaces,
        )

    def to_proto(self) -> pg.FunctionName:
        return pg.FunctionName(
            name=self.name,
            namespaces=self.namespaces,
        )

    @classmethod
    def parse(cls, to_parse: str) -> "FunctionName":
        """Parse from a string in the format \"namespace::name\"."""
        atoms = to_parse.split("::")
        name = atoms.pop(-1)
        return cls(name, atoms)

    def __str__(self):
        return "::".join(self.namespaces + [self.name])


FunctionDeclaration = ps.FunctionDeclaration
