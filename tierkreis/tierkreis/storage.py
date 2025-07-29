from tierkreis.controller.data.location import Loc
from tierkreis.controller.data.types import ptype_from_bytes
from tierkreis.controller.storage.protocol import ControllerStorage
from tierkreis.controller.storage.filestorage import (
    ControllerFileStorage as FileStorage,
)


def read_outputs(storage: ControllerStorage) -> dict[str, bytes] | bytes:
    out_ports = storage.read_output_ports(Loc())
    if len(out_ports) == 1 and "value" in out_ports:
        return ptype_from_bytes(storage.read_output(Loc(), "value"))
    return {k: ptype_from_bytes(storage.read_output(Loc(), k)) for k in out_ports}
