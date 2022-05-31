import glob
import os
import subprocess
from warnings import warn
import urllib.request
import maturin as default_backend  # type: ignore

# PEP 517 / 518 local (aka in-tree) backend for pip/build/etc.
# We expect to be run from the project root, i.e. python/
PROTO_INPUT_DIR = "../protos"
PROTO_OUTPUT_DIR = "./tierkreis/core/protos"
ANTLR_OUTPUT_DIR = "./tierkreis/frontend/tksl/antlr"
ANTLR_LOCAL_JAR_DIR = "../.antlr"
# This path intended for linux boxes.
# Building the sdist/wheel on Windows is not supported:
ANTLR_SYSTEM_JAR_DIR = "/usr/local/lib"
ANTLR_WILDCARD = "antlr-4.9*.jar"
ANTLR_URL = "https://github.com/antlr/website-antlr4/raw/gh-pages/download/antlr-4.9-complete.jar"


def get_antlr_jar_path() -> str:
    """
    Return an absolute path (suitable for passing to java -cp ...)
    to the .jar file containing the ANTLR installation,
    downloading if necessary.
    """
    local_jar_dir = os.path.join(os.getcwd(), ANTLR_LOCAL_JAR_DIR)
    for d in [ANTLR_SYSTEM_JAR_DIR, local_jar_dir]:
        jar_files = glob.glob(os.path.join(d, ANTLR_WILDCARD))
        if len(jar_files) == 0:
            continue
        jf = max(jar_files)  # Prefer 4.9.3 over 4.9, etc.
        print("Using", jf)
        return jf
    # Download - but don't bother if java not installed
    if subprocess.run(["java", "--version"]).returncode != 0:
        raise RuntimeError("java command unsuccessful, not found in PATH")
    with urllib.request.urlopen(ANTLR_URL) as url:
        if not os.path.exists(ANTLR_LOCAL_JAR_DIR):
            os.mkdir(ANTLR_LOCAL_JAR_DIR)
        _, fn = os.path.split(ANTLR_URL)
        fp = os.path.join(ANTLR_LOCAL_JAR_DIR, fn)
        with open(fp, "wb") as f:
            f.write(url.read())
        print("Downloaded to", fp)
        return os.path.join(local_jar_dir, fn)  # Absolute path


def generate_tksl_parser(force: bool):
    try:
        jar_file = get_antlr_jar_path()
        wd, outdir = os.path.split(ANTLR_OUTPUT_DIR)
        command = ["java", "-Xmx500M", "-cp", jar_file, "org.antlr.v4.Tool"]
        args = [
            "-o",
            outdir,
            "-Dlanguage=Python3",
            "-visitor",
            "-no-listener",
            "Tksl.g4",
        ]
        # Add "-atn" to generate lots of DOT output for debugging the parser
        subprocess.check_call(command + args, cwd=wd)
    except Exception as e:
        if force:
            raise RuntimeError("Cannot generate TKSL parser using ANTLR") from e
        else:
            warn(
                UserWarning(
                    "Cannot generate TKSL parser using ANTLR - TKSL will not operate", e
                )
            )


def generate_proto_code():
    proto_files = glob.glob(PROTO_INPUT_DIR + "/**/*.proto", recursive=True)
    assert len(proto_files) > 0

    if not os.path.exists(PROTO_OUTPUT_DIR):
        os.mkdir(PROTO_OUTPUT_DIR)

    subprocess.check_call(
        [
            "protoc",
            "--python_betterproto_out=" + PROTO_OUTPUT_DIR,
            "-I",
            PROTO_INPUT_DIR,
        ]
        + proto_files
    )


def build_sdist(*args, **kwargs):
    generate_tksl_parser(force=True)
    generate_proto_code()
    return default_backend.build_sdist(*args, **kwargs)


def build_wheel(*args, **kwargs):
    if os.path.exists(PROTO_INPUT_DIR):
        # Running from original source tree - maybe via "pip wheel"
        generate_tksl_parser(force=True)
        generate_proto_code()
    else:
        # Building wheel from sdist.
        # ANTLR files and protos should have been generated already
        # and placed into the sdist.
        proto_files_already_generated = glob.glob(
            PROTO_OUTPUT_DIR + "/tierkreis/**/*.py", recursive=True
        )
        assert len(proto_files_already_generated) > 0
        assert len(glob.glob(os.path.join(ANTLR_OUTPUT_DIR, "*.py"))) > 0
        assert len(glob.glob(os.path.join(ANTLR_OUTPUT_DIR, "*.interp"))) > 0
        # No generation required.
    return default_backend.build_wheel(*args, **kwargs)


get_requires_for_build_sdist = default_backend.get_requires_for_build_sdist

get_requires_for_build_wheel = default_backend.get_requires_for_build_wheel

prepare_metadata_for_build_wheel = default_backend.prepare_metadata_for_build_wheel

# PEP 660 defines additional hooks to support "pip install --editable":
def build_editable(*args, **kwargs):
    generate_tksl_parser(force=False)  # Allow local development without tksl
    generate_proto_code()
    return default_backend.build_editable(*args, **kwargs)


get_requires_for_build_editable = default_backend.get_requires_for_build_editable

prepare_metadata_for_build_editable = (
    default_backend.prepare_metadata_for_build_editable
)

if __name__ == "__main__":
    # Also support handrunning to regenerate python code from protos and ANTLR in-tree.
    path = os.path.dirname(os.path.dirname(__file__))
    print("Switching to", path)
    os.chdir(path)
    generate_tksl_parser(force=False)
    generate_proto_code()
