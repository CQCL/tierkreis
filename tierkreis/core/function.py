"""TierkreisFunction encapsulation of available function signatures"""
from dataclasses import dataclass
from typing import List
import tierkreis.core.protos.tierkreis.signature as ps
from tierkreis.core.types import TypeScheme


@dataclass
class TierkreisFunction:
    """TierkreisFunction encapsulation of available function signatures"""

    name: str
    type_scheme: TypeScheme
    docs: str
    input_order: List[str]
    output_order: List[str]

    @classmethod
    def from_proto(cls, pr_entry: ps.FunctionDeclaration) -> "TierkreisFunction":
        return cls(
            pr_entry.name,
            TypeScheme.from_proto(pr_entry.type_scheme),
            pr_entry.description,
            pr_entry.input_order,
            pr_entry.output_order,
        )

    def to_proto(self) -> ps.FunctionDeclaration:
        return ps.FunctionDeclaration(
            name=self.name,
            type_scheme=self.type_scheme.to_proto(),
            description=self.docs or "",
            input_order=self.input_order,
            output_order=self.output_order,
        )
