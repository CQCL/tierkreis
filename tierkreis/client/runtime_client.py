from abc import ABC, abstractmethod
from typing import Any, Dict

from tierkreis.core.signature import Signature
from tierkreis.core.tierkreis_graph import TierkreisGraph
from tierkreis.core.values import TierkreisValue


class RuntimeClient(ABC):
    @abstractmethod
    async def get_signature(self) -> Signature:
        ...

    @abstractmethod
    async def run_graph(
        self,
        graph: TierkreisGraph,
        /,
        **py_inputs: Any,
    ) -> Dict[str, TierkreisValue]:
        ...

    @abstractmethod
    async def type_check_graph(self, graph: TierkreisGraph) -> TierkreisGraph:
        ...

    @property
    def can_type_check(self) -> bool:
        return True
