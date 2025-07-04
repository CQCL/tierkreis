from dataclasses import dataclass, field
from logging import getLogger
from types import NoneType
from typing import Any
from tierkreis.controller.data.models import PModel, is_namedmodel
from tierkreis.controller.data.types import PType, ptype_from_annotation
from tierkreis.exceptions import TierkreisError

logger = getLogger(__name__)


class TierkreisWorkerError(TierkreisError):
    pass


@dataclass
class FunctionSpec:
    name: str
    namespace: str
    ins: dict[str, type[PType]]
    outs: type[PModel]

    def add_inputs(self, annotations: dict[str, Any]) -> None:
        for name, annotation in annotations.items():
            self.ins[name] = ptype_from_annotation(annotation)

    def add_outputs(self, annotation: Any) -> None:
        if annotation is None:
            self.outs = NoneType
            return

        if is_namedmodel(annotation):
            self.outs = annotation

        self.outs = ptype_from_annotation(annotation)


@dataclass
class Namespace:
    name: str
    functions: dict[str, FunctionSpec] = field(default_factory=lambda: {})

    def add_from_annotations(self, name: str, annotations: dict[str, Any]) -> None:
        try:
            fn = FunctionSpec(name=name, namespace=self.name, ins={}, outs=NoneType)
            fn.add_inputs({k: v for k, v in annotations.items() if k != "return"})
            fn.add_outputs(annotations["return"])
            print(annotations["return"])
            self.functions[fn.name] = fn
        except TierkreisError as exc:
            logger.warning(
                f"Error adding function {name} to {self.name} namespace.", exc_info=exc
            )
