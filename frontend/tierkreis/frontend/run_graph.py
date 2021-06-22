"""Send requests to tierkreis server to execute a graph."""
from typing import Dict
import types
import requests
from requests.models import HTTPError
from tierkreis.core.values import TierkreisValue, StructValue
from tierkreis.core.tierkreis_graph import TierkreisFunction
import tierkreis.core.protos.tierkreis.graph as pg
import tierkreis.core.protos.tierkreis.runtime as pr


URL = "http://127.0.0.1:8080"


def run_graph(
    graph: pg.Graph, inputs: Dict[str, TierkreisValue]
) -> Dict[str, TierkreisValue]:
    """Run a graph and return results

    :param gb: Graph to run.
    :type gb: ProtoGraphBuilder
    :param inputs: Inputs to graph as map from label to value.
    :type inputs: PyValMap
    :raises HTTPError: If server returns an error.
    :return: Outputs as map from label to value.
    :rtype: PyValMap
    """

    req = pr.RunGraphRequest(
        graph=graph,
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
    out = pr.RunGraphResponse().parse(resp.content)
    outputs = StructValue.from_proto_dict(out.outputs.map).values
    return outputs


def sig_module_from_proto(pr_sig: pr.SignatureResponse) -> types.ModuleType:

    namespaces: Dict[str, Dict[str, TierkreisFunction]] = dict()
    for name, entry in pr_sig.entries.items():
        namespace, fname = name.split("/", 2)
        func = TierkreisFunction.from_proto(entry)
        if namespace in namespaces:
            namespaces[namespace][fname] = func
        else:
            namespaces[namespace] = {fname: func}
    module_dict: Dict[str, types.ModuleType] = dict()
    for namespace, entries in namespaces.items():
        namespace_mod = types.ModuleType(namespace)

        namespace_mod.__dict__.update(entries)
        module_dict[namespace] = namespace_mod

    run_sig = types.ModuleType(
        "RuntimeSignature", "Available namespaces in tierkreis runtime."
    )
    run_sig.__dict__.update(module_dict)
    return run_sig


def signature():
    """Run a graph and return results

    :param gb: Graph to run.
    :type gb: ProtoGraphBuilder
    :param inputs: Inputs to graph as map from label to value.
    :type inputs: PyValMap
    :raises HTTPError: If server returns an error.
    :return: Outputs as map from label to value.
    :rtype: PyValMap
    """

    resp = requests.get(
        URL + "/signature",
        headers={"content-type": "application/protobuf"},
    )
    if resp.status_code != 200:
        raise HTTPError(
            "Run request"
            f" failed with code {resp.status_code} and message {str(resp.content)}"
        )
    return sig_module_from_proto(pr.SignatureResponse().parse(resp.content))


# def type_(value: TierkreisValue):
#     """Run a graph and return results

#     :param gb: Graph to run.
#     :type gb: ProtoGraphBuilder
#     :param inputs: Inputs to graph as map from label to value.
#     :type inputs: PyValMap
#     :raises HTTPError: If server returns an error.
#     :return: Outputs as map from label to value.
#     :rtype: PyValMap
#     """

#     resp = requests.post(
#         URL + "/type",
#         headers={"content-type": "application/protobuf"},
#         data=bytes(pr.InferTypeRequest(value.to_proto())),
#     )
#     if resp.status_code != 200:
#         raise HTTPError(
#             "Run request"
#             f" failed with code {resp.status_code} and message {str(resp.content)}"
#         )
#     return pr.InferTypeResponse().parse(resp.content)
