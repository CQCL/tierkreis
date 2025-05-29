#!/usr/bin/env python

import logging

from pathlib import Path
import sys
from typing import Literal
from google.protobuf.compiler.plugin_pb2 import (
    CodeGeneratorRequest,
    CodeGeneratorResponse,
)
from pydantic import BaseModel


logger = logging.getLogger(__name__)
FieldType = type | Literal["group", "message", "enum"]
type_from_int: dict[int, FieldType] = {
    1: float,
    2: float,
    3: int,
    4: int,
    5: int,
    6: int,
    7: int,
    8: bool,
    9: str,
    10: "group",
    11: "message",
    12: bytes,
    13: int,
    14: "enum",
    15: int,
    16: int,
    17: int,
    18: int,
}


def process(req: CodeGeneratorRequest, res: CodeGeneratorResponse) -> None:
    pass


class _Field(BaseModel):
    name: str
    field_type: FieldType
    type_name: str


class _Message(BaseModel):
    name: str
    fields: list[_Field]


class _Method(BaseModel):
    name: str
    input_type: str
    output_type: str


class _Service(BaseModel):
    name: str
    methods: list[_Method]


def print_type(field: _Field) -> str:
    match field.field_type:
        case "group" | "enum":
            raise NotImplementedError(f"{field.field_type} not recognised")
        case "message":
            return field.type_name
        case type():
            return field.field_type.__name__


def print_message(message: _Message) -> str:
    s = f"""
@dataclass
class {message.name}:
    """
    for field in message.fields:
        s += f'{field.name}: "{print_type(field)}"\n    '
    return s


def print_messages(messages: dict[str, _Message]) -> str:
    s = "from dataclasses import dataclass\n"
    s += "from abc import ABC, abstractmethod\n\n"
    s += "\n".join([print_message(v) for _, v in messages.items()])
    return s


def print_service(service: _Service) -> str:
    s = f"""
class {service.name}(ABC):
    """
    for method in service.methods:
        s += "@abstractmethod\n    "
        s += "@staticmethod\n    "
        s += f"def {method.name}({method.name}_request: {method.input_type}) -> {method.output_type}: ...\n    "
    return s


def main() -> None:
    request = CodeGeneratorRequest.FromString(sys.stdin.buffer.read())
    response = CodeGeneratorResponse()
    messages: dict[str, _Message] = {}
    for proto_file in request.proto_file:
        for desc in proto_file.message_type:
            message = _Message(name=desc.name, fields=[])
            for field_desc in desc.field:
                field = _Field(
                    field_type=type_from_int[field_desc.type],
                    type_name=field_desc.type_name.replace(".", ""),
                    name=field_desc.name,
                )
                message.fields.append(field)
            messages[desc.name] = message

        for desc in proto_file.service:
            service = _Service(name=desc.name, methods=[])
            for method_desc in desc.method:
                method = _Method(
                    name=method_desc.name,
                    input_type=method_desc.input_type.replace(".", ""),
                    output_type=method_desc.output_type.replace(".", ""),
                )
                service.methods.append(method)

            logger.error(service)

            if proto_file.name in request.file_to_generate:
                f = CodeGeneratorResponse.File()
                f.content = print_messages(messages)
                f.content += "\n"
                f.content += print_service(service)

                f.name = "tkr_" + Path(proto_file.name).stem + ".py"
                response.file.append(f)

    sys.stdout.buffer.write(response.SerializeToString())


if __name__ == "__main__":
    main()
