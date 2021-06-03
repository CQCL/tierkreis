import os
from subprocess import run
from pathlib import Path
import requests
from requests.models import HTTPError
from .proto_graph_builder import ProtoGraphBuilder

from tierkreis.core.protos.tierkreis.graph import RunRequest, RunResponse, ValueMap
from tierkreis.core import PyValMap, encode_values, decode_values


def run_graph(gb: ProtoGraphBuilder, inputs: PyValMap) -> PyValMap:
    URL = "http://127.0.0.1:8080"

    req = RunRequest(graph=gb.graph, inputs=ValueMap(map=encode_values(inputs)))
    resp = requests.post(
        URL + "/run",
        headers={"content-type": "application/protobuf"},
        data=bytes(req),
    )
    if resp.status_code != 200:
        raise HTTPError(
            f"Run request"
            f" failed with code {resp.status_code} and message {resp.content}"
        )
    out = RunResponse().parse(resp.content)
    outputs = decode_values(out.outputs.map)

    return outputs
