import pathlib
import os
from subprocess import check_call


def generate_proto_code():
    proto_dir = "../../protos"
    output_dir = "./tierkreis/core/protos"

    if not os.path.exists(output_dir):
        os.mkdir(output_dir)

    proto_files = pathlib.Path().glob(proto_dir + "/**/*")
    proto_files = [str(proto) for proto in proto_files if proto.is_file()]
    check_call(
        ["protoc", "--python_betterproto_out=" + output_dir, "-I", proto_dir]
        + proto_files
    )


if __name__ == "__main__":
    generate_proto_code()
