class StdOutIn:
    def __init__(self, input_file: str, output_file: str) -> None:
        self.input = input_file
        self.output = output_file

    def __call__(self, inner_command: str) -> str:
        return f"{inner_command} < {self.input} > {self.output}"


class WithCallArgs:
    def __init__(self, call_args_path: str) -> None:
        self.call_args_path = call_args_path

    def __call__(self, inner_command: str) -> str:
        return f"{inner_command} {self.call_args_path}"


class TouchDone:
    def __init__(self, done_path: str) -> None:
        self.done_path = done_path

    def __call__(self, inner_command: str) -> str:
        return f"{inner_command} && touch {self.done_path}"


class UvRun:
    def __init__(self, uv_project_directory: str) -> None:
        self.project_dir = uv_project_directory

    def __call__(self, inner_command: str) -> str:
        return f"uv run --no-active --project {self.project_dir} {inner_command}"


class DockerRun:
    def __init__(self, container_name: str) -> None:
        self.container = container_name

    def __call__(self, inner_command: str) -> str:
        return f'docker run {self.container} bash -c "{inner_command}"'
