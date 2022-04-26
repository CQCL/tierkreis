import glob
import os
from subprocess import check_call

import maturin as default_backend  # type: ignore

# PEP 517 / 518 local (aka in-tree) backend for pip/build/etc.
# We expect to be run from the project root, i.e. python/
proto_dir = "../protos"
output_dir = "./tierkreis/core/protos"


def generate_proto_code():
    proto_files = glob.glob(proto_dir + "/**/*.proto", recursive=True)
    assert len(proto_files) > 0

    if not os.path.exists(output_dir):
        os.mkdir(output_dir)

    check_call(
        [
            "protoc",
            "--python_betterproto_out=" + output_dir,
            "-I",
            proto_dir,
        ]
        + proto_files
    )


def build_sdist(*args, **kwargs):
    generate_proto_code()
    return default_backend.build_sdist(*args, **kwargs)


def build_wheel(*args, **kwargs):
    if os.path.exists(proto_dir):
        # Running from original source tree - maybe via "pip wheel"
        generate_proto_code()
    else:
        # Building wheel from sdist.
        # Protos should have been generated already and placed into the sdist.
        proto_files_already_generated = glob.glob(
            output_dir + "/tierkreis/**/*.py", recursive=True
        )
        assert len(proto_files_already_generated) > 0
        # No generation required.
    return default_backend.build_wheel(*args, **kwargs)


get_requires_for_build_sdist = default_backend.get_requires_for_build_sdist

get_requires_for_build_wheel = default_backend.get_requires_for_build_wheel

prepare_metadata_for_build_wheel = default_backend.prepare_metadata_for_build_wheel

# PEP 660 defines additional hooks to support "pip install --editable":
def build_editable(*args, **kwargs):
    generate_proto_code()
    return default_backend.build_editable(*args, **kwargs)


get_requires_for_build_editable = default_backend.get_requires_for_build_editable

prepare_metadata_for_build_editable = (
    default_backend.prepare_metadata_for_build_editable
)

if __name__ == "__main__":
    # Also support handrunning to regenerate python code from protos in-tree.
    path = os.path.dirname(os.path.dirname(__file__))
    print("Switching to", path)
    os.chdir(path)
    generate_proto_code()
