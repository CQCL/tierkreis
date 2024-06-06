"""Simple pure-Python implementation of the Tierkreis runtime protocol. Allows execution of
graphs with Python workers. Does not support type checking or connecting to
workers over the network."""

from .python_runtime import PyRuntime
