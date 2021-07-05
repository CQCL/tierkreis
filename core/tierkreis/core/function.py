"""TierkreisFunction encapsulation of available function signatures"""
from dataclasses import dataclass
import tierkreis.core.protos.tierkreis.graph as pg
from tierkreis.core.types import TypeScheme


@dataclass
class TierkreisFunction:
    """TierkreisFunction encapsulation of available function signatures"""

    name: str
    type_scheme: TypeScheme
    docs: str

    @classmethod
    def from_proto(cls, pr_entry: pg.SignatureEntry) -> "TierkreisFunction":
        return cls(
            pr_entry.name, TypeScheme.from_proto(pr_entry.type_scheme), pr_entry.docs
        )
