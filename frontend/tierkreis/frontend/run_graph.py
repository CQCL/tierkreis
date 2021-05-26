import os
from subprocess import run
from pathlib import Path
import requests
from requests.models import HTTPError
from .proto_graph_builder import ProtoGraphBuilder
from .values import (
    PyValMap,
    write_vals_to_file,
    read_vals_from_file,
    proto_to_valmap,
    valmap_to_proto,
)
from .graph_pb2 import RunRequest, RunResponse


def run_graph(gb: ProtoGraphBuilder, inputs: PyValMap) -> PyValMap:
    URL = "http://127.0.0.1:8080"

    req = RunRequest()
    req.graph.CopyFrom(gb.graph)
    valmap_to_proto(inputs, req.inputs)

    resp = requests.post(
        URL + "/run",
        headers={"content-type": "application/protobuf"},
        data=req.SerializeToString(),
    )
    if resp.status_code != 200:
        raise HTTPError(
            f"Run request failed with code {resp.status_code} and message {resp.content}"
        )
    out = RunResponse()
    out.ParseFromString(resp.content)

    outputs = proto_to_valmap(out.outputs)

    return outputs
