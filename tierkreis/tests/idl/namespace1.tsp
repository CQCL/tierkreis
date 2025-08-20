@portmapping
model A {
  name: Record<string>;
  age: uint8;
}

model B {
  name: Record<string>;
  age: uint8;
}

@portmapping
model C {
  a: Array<integer>;
  b: Array<B>;
}
interface TestNamespace {
  foo(a: integer, b: string): A;
  bar(): B;
  z(a: C): C;
}
