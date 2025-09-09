from dataclasses import dataclass
from typing import Optional

from tierkreis.core.values import TierkreisType


@dataclass
class Foo:
    head: int
    tail: Optional["Foo"]


# Test of breaking change in betterproto to 2.0.0b7 where
# an AttributeError is raised when trying to access a None oneof
def test_proto_roundtrip():
    tkval = TierkreisType.from_python(Foo)
    protoval = tkval.to_proto()
    tkval_from_proto = TierkreisType.from_proto(protoval)
    assert tkval == tkval_from_proto
