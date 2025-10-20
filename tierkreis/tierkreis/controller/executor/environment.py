from pathlib import Path
from tierkreis.controller.data.location import WorkerCallArgs


def create_env(
    call_args: WorkerCallArgs, base_dir: Path, export_values: bool
) -> dict[str, str]:
    env = {
        "checkpoints_directory": str(base_dir),
        "function_name": str(base_dir / call_args.function_name),
        "done_path": str(base_dir / call_args.done_path),
        "error_path": str(base_dir / call_args.error_path),
        "output_dir": str(base_dir / call_args.output_dir),
    }
    if call_args.logs_path is not None:
        env["logs_path"] = str(base_dir / call_args.logs_path)
    else:
        env["logs_path"] = str(base_dir / "logs")
    env |= {f"output_{k}_file": str(base_dir / v) for k, v in call_args.outputs.items()}
    env |= {f"input_{k}_file": str(base_dir / v) for k, v in call_args.inputs.items()}
    if not export_values:
        return env
    values = {}
    for k, v in call_args.inputs.items():
        with open(v) as fh:
            values[f"input_{k}_value"] = fh.read()
    return env
