from abc import ABC
from dataclasses import dataclass


@dataclass
class TierkreisStruct(ABC):
    "Abstract base class for classes that should encode structs at runtime."
