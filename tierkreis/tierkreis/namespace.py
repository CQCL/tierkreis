from logging import getLogger
from typing import Any, get_args
from pydantic import BaseModel
from tierkreis.controller.data.core import PortID, TKType
from tierkreis.exceptions import TierkreisError

logger = getLogger(__name__)


class TierkreisWorkerError(TierkreisError):
    pass


class FunctionSpec(BaseModel):
    name: str
    ins: dict[PortID, TKType]
    outs: dict[PortID, TKType]

    @staticmethod
    def _parse_annotation(annotation: Any) -> TKType | None:
        if issubclass(annotation, BaseModel):
            return f"{annotation.__module__}.{annotation.__qualname__}"
        elif annotation not in get_args(TKType):
            raise TierkreisWorkerError(f"Unsupported annotation: {annotation}.")
        else:
            return annotation

    def add_inputs(self, annotations: dict[str, Any]) -> None:
        for name, annotation in annotations.items():
            if name == "return":
                continue

            if (t := self._parse_annotation(annotation)) is not None:
                self.ins[name] = t

    def add_outputs(self, annotation: Any) -> None:
        if issubclass(annotation, BaseModel):
            for field, info in annotation.model_fields.items():
                if (t := self._parse_annotation(info.annotation)) is not None:
                    self.outs[field] = t
        else:
            self.outs["value"] = annotation


class Namespace(BaseModel):
    name: str
    functions: list[FunctionSpec]

    def add_from_annotations(self, name: str, annotations: dict[str, Any]) -> None:
        try:
            fn = FunctionSpec(name=name, ins={}, outs={})
            fn.add_inputs({k: v for k, v in annotations.items() if k != "result"})
            fn.add_outputs(annotations["return"])
            self.functions.append(fn)
        except TierkreisWorkerError:
            logger.exception(f"Error adding function {name} to {self.name} namespace.")
