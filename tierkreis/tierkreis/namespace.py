from dataclasses import dataclass
from logging import getLogger
from types import NoneType
from typing import Any
from tierkreis.controller.data.core import (
    EmptyModel,
    PortID,
    TModel,
    TType,
    is_tmodel,
    is_ttype,
)
from tierkreis.exceptions import TierkreisWorkerError

logger = getLogger(__name__)


@dataclass
class FunctionSpec:
    name: str
    namespace: str
    ins: dict[PortID, type[TType]]
    outs: type[TModel]

    def add_inputs(self, annotations: dict[str, Any]) -> None:
        for name, annotation in annotations.items():
            if not is_ttype(annotation):
                raise TierkreisWorkerError(f"Expected TType found {annotation}")
            self.ins[name] = annotation

    def add_outputs(self, annotation: type | None) -> None:
        if annotation is None:
            self.outs = NoneType
            return

        if not is_tmodel(annotation):
            raise TierkreisWorkerError(f"Expected TModel found {annotation}.")

        self.outs = annotation


@dataclass
class Namespace:
    name: str
    functions: list[FunctionSpec]

    def add_from_annotations(self, name: str, annotations: dict[str, Any]) -> None:
        try:
            fn = FunctionSpec(name=name, namespace=self.name, ins={}, outs=EmptyModel)
            fn.add_inputs({k: v for k, v in annotations.items() if k != "return"})
            fn.add_outputs(annotations["return"])
            self.functions.append(fn)
        except TierkreisWorkerError as exc:
            logger.info(f"Error adding {name} to {self.name} namespace.", exc_info=exc)
