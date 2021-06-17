"""Send requests to tierkreis server to execute a graph."""
import requests
from requests.models import HTTPError
from tierkreis.core.values import TierkreisValue, StructValue
import tierkreis.core.protos.tierkreis.graph as pg

from .proto_graph_builder import ProtoGraphBuilder

URL = "http://127.0.0.1:8080"


def run_graph(
    graph_builder: ProtoGraphBuilder, inputs: dict[str, TierkreisValue]
) -> dict[str, TierkreisValue]:
    """Run a graph and return results

    :param gb: Graph to run.
    :type gb: ProtoGraphBuilder
    :param inputs: Inputs to graph as map from label to value.
    :type inputs: PyValMap
    :raises HTTPError: If server returns an error.
    :return: Outputs as map from label to value.
    :rtype: PyValMap
    """

    req = pg.RunRequest(
        graph=graph_builder.graph,
        inputs=pg.StructValue(map=StructValue(inputs).to_proto_dict()),
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
    out = pg.RunResponse().parse(resp.content)
    outputs = StructValue.from_proto_dict(out.outputs.map).values
    return outputs
