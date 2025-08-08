from tierkreis.codegen import format_namespace
from tierkreis.idl.parser import typespec_parser, NamespaceTransformer


def test_load_transform():
    txt = """
model Dog {
  name: string;
  age: uint8;
}
model Dog {
  name: string;
  age: uint8;
}
interface SampleInterface {
  foo(a: integer, b:string): int32;
  bar(): string;
}
"""
    tree = typespec_parser.parse(txt)
    ns = NamespaceTransformer().spec(tree)
    print(format_namespace(ns))
    assert False
