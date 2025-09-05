import subprocess
from tierkreis.runner.uv_run import DockerRun, UvRun


def test_runner():
    uv_run = UvRun("~")
    docker_run = DockerRun("astral/uv:debian")
    x = docker_run(uv_run("python --version"))
    print(x)
    res = subprocess.run(["bash"], input=x.encode())
    print(res)
    assert False
