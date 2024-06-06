from abc import ABC, abstractmethod
from typing import Any, Dict

from tierkreis.core.signature import Signature
from tierkreis.core.tierkreis_graph import TierkreisGraph
from tierkreis.core.values import TierkreisValue


class RuntimeClient(ABC):
    """Abstract class for clients which can run tierkreis graphs on a runtime."""

    @abstractmethod
    async def get_signature(self) -> Signature:
        """Get the signature of functions available on the runtime."""

    @abstractmethod
    async def run_graph(
        self,
        graph: TierkreisGraph,
        /,
        **py_inputs: Any,
    ) -> Dict[str, TierkreisValue]:
        """Execute a tierkreis graph on the runtime. Inputs are taken as keyword arguments and each keyword argument must match an input port of the graph.  Non-tierkreis values will be converted to tierkreis values if possible."""

    @abstractmethod
    async def type_check_graph(self, graph: TierkreisGraph) -> TierkreisGraph:
        """Type check a tierkreis graph on the runtime against the runtime signature."""

    @property
    def can_type_check(self) -> bool:
        """Whether the runtime supports type-checking graphs."""
        return True
