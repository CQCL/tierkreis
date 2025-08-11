from tierkreis.codegen import format_namespace
from tierkreis.idl.parser import typespec_parser, NamespaceTransformer


def test_load_transform():
    txt = """
portmapping Dog {
  name: string;
  age: uint8;
}
struct Dog2 {
  name: string;
  age: uint8;
}
portmapping A {
    a: integer;
}
interface SampleInterface {
  foo(a: integer, b:string): Dog;
  new_dog(): Dog2;
  a(a: A): A;
}
"""
    tree = typespec_parser.parse(txt)
    ns = NamespaceTransformer().spec(tree)
    print(format_namespace(ns))
    assert False
