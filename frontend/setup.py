from setuptools import setup, find_namespace_packages

setup(
    name="tierkreis.frontend",
    version="0.0.1",
    description="Client that can connect with a tierkreis server.",
    packages=find_namespace_packages(include="tierkreis.*"),
)
