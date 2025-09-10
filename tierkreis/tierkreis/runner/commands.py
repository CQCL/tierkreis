from pathlib import Path

from tierkreis.controller.executor.consts import BASH_TKR_DIR


class StdOutIn:
    def __init__(self, input_file: Path, output_file: Path) -> None:
        self.input = input_file
        self.output = output_file

    def __call__(self, inner_command: str) -> str:
        return f"{inner_command} < {self.input} > {self.output}"


class WithCallArgs:
    def __init__(self, call_args_path: Path) -> None:
        self.call_args_path = call_args_path

    def __call__(self, inner_command: str) -> str:
        return f"{inner_command} {self.call_args_path}"


class TouchDone:
    def __init__(self, done_path: Path) -> None:
        self.done_path = done_path

    def __call__(self, inner_command: str) -> str:
        return f"{inner_command} && touch {self.done_path}"


class HandleError:
    def __init__(
        self, error_path: Path, error_logs_path: Path, logs_path: Path
    ) -> None:
        self.error_path = error_path
        self.error_logs_path = error_logs_path
        self.logs_path = logs_path

    def __call__(self, inner_command: str) -> str:
        return f"{inner_command} 2>{self.error_logs_path} 1>{self.logs_path} || touch {self.error_path}"


class UvRun:
    def __init__(self, uv_project_directory: str) -> None:
        self.project_dir = uv_project_directory

    def __call__(self, inner_command: str) -> str:
        return f"uv run --no-active --project {self.project_dir} {inner_command}"


class DockerRun:
    def __init__(self, container_name: str, tkr_dir: str = BASH_TKR_DIR) -> None:
        self.container = container_name
        self.tkr_dir = tkr_dir

    def __call__(self, inner_command: str) -> str:
        return f"docker run -d -v {self.tkr_dir}:/root/.tierkreis {self.container} bash -c '{inner_command}'"
