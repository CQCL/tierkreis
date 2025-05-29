from pathlib import Path
import subprocess


def compile_protos(proto_file: Path, output_dir: Path) -> None:
    main_file = Path(__file__).absolute().parent / "main.py"

    cmd: list[str] = ["protoc"]
    cmd.extend(["-I", str(proto_file.parent)])
    cmd.append(str(proto_file))
    cmd.extend(["--demo_out", str(output_dir)])
    cmd.append(f"--plugin=protoc-gen-demo={main_file}")

    subprocess.run(cmd)


if __name__ == "__main__":
    proto_file: Path = (
        Path(".")
        / "tierkreis"
        / "tierkreis"
        / "controller"
        / "builtins"
        / "builtins.proto"
    )
    compile_protos(proto_file.absolute(), Path(".").absolute())
