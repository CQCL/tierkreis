from dataclasses import dataclass
import inspect
from logging import getLogger
from types import NoneType
from typing import Any, get_args
from pydantic import BaseModel
from tierkreis.controller.data.core import DictConvertible, PortID, TKType
from tierkreis.exceptions import TierkreisError

logger = getLogger(__name__)


class TierkreisWorkerError(TierkreisError):
    pass


@dataclass
class FunctionSpec:
    name: str
    namespace: str
    ins: dict[PortID, type[TKType] | str]
    outs: dict[PortID, type[TKType] | str]

    def _parse_annotation(self, annotation: type | None) -> type[TKType] | str:
        if annotation is None:
            return NoneType

        if annotation in get_args(TKType):
            return annotation

        if inspect.isclass(annotation):
            if issubclass(annotation, (BaseModel, DictConvertible)):
                return annotation.__name__

        raise TierkreisWorkerError(f"Unsupported annotation {annotation}.")

    def add_inputs(self, annotations: dict[str, Any]) -> None:
        for name, annotation in annotations.items():
            self.ins[name] = self._parse_annotation(annotation)

    def add_outputs(self, annotation: type | None) -> None:
        if annotation is None:
            self.outs["value"] = NoneType
            return

        self._parse_annotation(annotation)
        if issubclass(annotation, BaseModel):
            for field, info in annotation.model_fields.items():
                self.outs[field] = self._parse_annotation(info.annotation)
        else:
            self.outs["value"] = annotation


@dataclass
class Namespace:
    name: str
    functions: list[FunctionSpec]

    def add_from_annotations(self, name: str, annotations: dict[str, Any]) -> None:
        try:
            fn = FunctionSpec(name=name, namespace=self.name, ins={}, outs={})
            fn.add_inputs({k: v for k, v in annotations.items() if k != "return"})
            fn.add_outputs(annotations["return"])
            self.functions.append(fn)
        except TierkreisWorkerError as exc:
            logger.info(
                f"Error adding function {name} to {self.name} namespace.", exc_info=exc
            )
