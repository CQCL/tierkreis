from pathlib import Path
from typing import Callable, Protocol

from tierkreis.controller.executor.hpc.job_spec import JobSpec


class HpcAdapter(Protocol):
    @property
    def adapter_name(self) -> str: ...
    @property
    def command(self) -> str: ...

    def generate_script(self, spec: JobSpec, path: Path) -> None: ...
    def spec_from_script(self, batch_script: Path) -> JobSpec: ...


def _not_implemented(path: Path) -> JobSpec:
    raise NotImplementedError


class TemplateAdapter:
    _command: str
    _template_fn: Callable[[JobSpec], str]
    _parse_fn: Callable[[Path], JobSpec]

    def __init__(
        self,
        template_fn: Callable[[JobSpec], str],
        command: str,
        parse_fn: Callable[[Path], JobSpec] = _not_implemented,
    ) -> None:
        self._template_fn = template_fn
        self._command = command
        self._parse_fn = parse_fn

    @property
    def adapter_name(self) -> str:
        return self._template_fn.__name__

    @property
    def command(self) -> str:
        return self._command

    def generate_script(self, spec: JobSpec, path: Path) -> None:
        with open(path, "w+", encoding="utf-8") as fh:
            fh.write(self._template_fn(spec))

    def spec_from_script(self, batch_script: Path) -> JobSpec:
        return self._parse_fn(batch_script)
