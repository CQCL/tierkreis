from setuptools import setup, find_namespace_packages

setup(
    name = "tierkreis.frontend",
    version = "0.0.1",
    packages = find_namespace_packages(include = "tierkreis.*"),
)
