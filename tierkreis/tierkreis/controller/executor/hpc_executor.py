import json
import logging
import shlex
import subprocess
from collections import defaultdict
from pathlib import Path

from pydantic import BaseModel

from tierkreis.exceptions import TierkreisError

logger = logging.getLogger(__name__)


class ExecutorConfig(BaseModel):
    command: list[str]
    cwd: Path | None = None
    env: dict[str, str] | None = None
    flags: dict[str, list[str]] | None = None


class HPCExecutor:
    def __init__(
        self,
        registry_path: Path,
        logs_path: Path,
        command: str,
        flags: list[str] | None = None,
        working_directory: Path | None = None,
        env_vars: dict[str, str] | None = None,
        additional_input: str | None = None,
    ) -> None:
        self.launchers_path = registry_path
        self.logs_path = logs_path
        self.errors_path = logs_path
        self.command: list[str] = shlex.split(command)
        self.working_directory: Path = working_directory or Path().cwd()
        self.env_vars: dict[str, str] = env_vars or {}
        self.additional_input: str = additional_input or ""
        self.flag_dict: dict[str, list[str]] = defaultdict(list)
        self._parse_flags_to_dict(flags)

    def run(self, launcher_name: str, node_definition_path: Path) -> int:
        logging.basicConfig(
            format="%(asctime)s: %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S%z",
            filename=self.logs_path,
            filemode="a",
            level=logging.INFO,
        )
        self.errors_path = node_definition_path.parent / "errors"
        logger.info("START %s %s", launcher_name, node_definition_path)

        with open(self.logs_path, "a") as lfh:
            with open(self.errors_path, "a") as efh:
                process = subprocess.run(
                    self.command + self.flags,
                    cwd=self.working_directory / launcher_name,
                    env=self.env_vars,
                    input=self.additional_input + " " + node_definition_path,
                    start_new_session=True,
                    capture_output=True,
                    universal_newlines=True,
                    stderr=efh,
                    stdout=lfh,
                )
        if process.returncode != 0:
            with open(self.errors_path, "a") as efh:
                efh.write(f"Error from {self.working_directory}:")
                efh.write(process.stderr)
            raise TierkreisError(
                f"Executor failed with return code {process.returncode}"
            )
        return int(process.stdout.rstrip())

    def add_flags(self, flags: str | list[str]) -> None:
        flag_strings = []
        if isinstance(flags, list):
            for flag in flags:
                flag_strings.extend(shlex.split(flag))
        else:
            flag_strings.extend(shlex.split(flag))
        self._parse_flags_to_dict(flag_strings)

    def add_flags_from_config_file(self, config_file: Path) -> None:
        with open(config_file, "r") as fh:
            for line in fh.readlines():
                if not line.startswith("#"):
                    self.add_flag(line.strip())

    @classmethod
    def from_config_file(
        cls,
        config_file: Path,
        registry_path: Path,
        logs_path: Path,
    ) -> "HPCExecutor":
        with open(config_file, "w") as fh:
            config = json.load(fh)

        return cls(
            registry_path, logs_path, command=" ".join(config["command"]), **config
        )

    def to_config(self, config_file: Path) -> None:
        config = ExecutorConfig(
            command=self.command,
            cwd=self.working_directory,
            env=self.env_vars,
            flags=self.flag_dict,
        )
        with open(config_file, "w+") as fh:
            json.dump(config.model_dump_json(), fh)

    def overwrite_flag(self, flag: str, value: str | list[str]) -> None:
        if isinstance(value, str):
            value = shlex.split(value)
        self.flag_dict[flag] = value

    def append_flag(self, flag: str, value: str | list[str]) -> None:
        if isinstance(value, str):
            value = shlex.split(value)
        self.flag_dict[flag].extend(value)

    def _parse_flags_to_dict(self, flags: list[str]) -> None:
        current = ""
        for flag in flags:
            if flag.startswith("-") or flag.startswith("--"):
                current = flag
                self.flag_dict[current].append("")
                continue
            self.flag_dict[current].append(flag)

    def _flags_to_list(self) -> list[str]:
        return [
            item for k, v in self.flag_dict.items() for item in [k] + v if item != ""
        ]
