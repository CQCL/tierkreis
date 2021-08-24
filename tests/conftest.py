import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--docker",
        action="store_true",
        help="Whether to use docker container for server rather than local binary",
    )
