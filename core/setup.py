import setuptools
import pathlib
import os
from subprocess import check_call
from setuptools.command.develop import develop


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


class CustomDevelopCommand(develop):
    uninstall = False

    def run(self):
        develop.run(self)

    def install_for_development(self):
        develop.install_for_development(self)
        generate_proto_code()


setuptools.setup(
    name="tierkreis.core",
    version="0.0.1",
    description="Common definitions and functions for tierkreis.",
    packages=setuptools.find_namespace_packages(include="tierkreis.*"),
    cmdclass={
        "develop": CustomDevelopCommand,
    },
)
