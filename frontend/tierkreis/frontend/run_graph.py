"""Send requests to tierkreis server to execute a graph."""
import requests
from requests.models import HTTPError
from tierkreis.core import PyValMap, decode_values, encode_values
from tierkreis.core.protos.tierkreis.graph import RunRequest, RunResponse, StructValue

from .proto_graph_builder import ProtoGraphBuilder

URL = "http://127.0.0.1:8080"


def run_graph(graph_builder: ProtoGraphBuilder, inputs: PyValMap) -> PyValMap:
    """Run a graph and return results

    :param gb: Graph to run.
    :type gb: ProtoGraphBuilder
    :param inputs: Inputs to graph as map from label to value.
    :type inputs: PyValMap
    :raises HTTPError: If server returns an error.
    :return: Outputs as map from label to value.
    :rtype: PyValMap
    """

    req = RunRequest(
        graph=graph_builder.graph, inputs=StructValue(map=encode_values(inputs))
    )
    resp = requests.post(
        URL + "/run",
        headers={"content-type": "application/protobuf"},
        data=bytes(req),
    )
    if resp.status_code != 200:
        raise HTTPError(
            "Run request"
            f" failed with code {resp.status_code} and message {str(resp.content)}"
        )
    out = RunResponse().parse(resp.content)
    outputs = decode_values(out.outputs.map)

    return outputs
