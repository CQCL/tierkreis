import subprocess
from tierkreis.controller.data.location import WorkerCallArgs


def run_command(command: str, call_args: WorkerCallArgs) -> None:
    with open(call_args.logs_path or call_args.error_path, "a") as lfh:
        with open(call_args.error_path, "a") as efh:
            proc = subprocess.Popen(
                ["bash"],
                start_new_session=True,
                stdin=subprocess.PIPE,
                stderr=efh,
                stdout=lfh,
            )
            proc.communicate(f"{command} ".encode(), timeout=10)
