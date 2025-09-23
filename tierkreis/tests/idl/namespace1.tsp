@portmapping
model A {
  name: Record<string>;
  age: uint8;
}

model B {
  name: Record<string>;
  age: uint8;
}

model C<T> {
  a: Array<integer>;
  b: B;
  t: T;
}
interface TestNamespace {
  foo(a: integer, b: string): A;
  bar(): B;
  z<T>(c: C<T>): C<T>;
}
