from pathlib import Path
from typing import Callable, Protocol

from jinja2 import Environment, FileSystemLoader, Template
from tierkreis.controller.executor.hpc.job_spec import JobSpec


class HpcAdapter(Protocol):
    @property
    def template(self) -> Template: ...
    @property
    def command(self) -> str: ...

    def generate_script(self, spec: JobSpec, path: Path) -> None: ...
    def spec_from_script(self, batch_script: Path) -> JobSpec: ...


def _not_implemeneted(path: Path) -> JobSpec:
    raise NotImplementedError


class TemplateAdapter:
    _template: Template
    _command: str
    _parse_fn: Callable[[Path], JobSpec]

    def __init__(
        self,
        template_name: str,
        command: str,
        template_dir: str = ".",
        parse_fn: Callable[[Path], JobSpec] = _not_implemeneted,
    ) -> None:
        env = Environment(loader=FileSystemLoader(template_dir))
        self._template = env.get_template(template_name)
        self._command = command
        self._parse_fn = parse_fn

    @property
    def template(self) -> Template:
        return self._template

    @property
    def command(self) -> str:
        return self._command

    def generate_script(self, spec: JobSpec, path: Path) -> None:
        with open(path) as fh:
            fh.write(self._template.render(job=spec))

    def spec_from_script(self, batch_script: Path) -> JobSpec:
        return self._parse_fn(batch_script)
