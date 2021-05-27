import setuptools
import pathlib
import os
from subprocess import check_call
from setuptools.command.develop import develop

setuptools.setup(
    name = "tierkreis.runtime",
    description = "Library for building tierkreis workers.",
    version = "0.0.1",
    packages = setuptools.find_namespace_packages(include = "tierkreis.*"),
)
