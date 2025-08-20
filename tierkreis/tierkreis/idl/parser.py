"""Elementary parser and parser combinators."""

import re
from typing import Callable, Never, overload


class ParserError(Exception): ...


class Parser[T]:
    fn: Callable[[str], tuple[T, str]]

    def __init__(self, fn: Callable[[str], tuple[T, str]]):
        self.fn = fn

    def __call__(self, ins: str) -> tuple[T, str]:
        ins = ins.strip()
        return self.fn(ins)

    def __or__[S](
        self, other: "Parser[S]" | Callable[[str], tuple[S, str]]
    ) -> "Parser[T|S]":
        def f(ins: str):
            try:
                return self(ins)
            except ParserError:
                return other(ins)

        return Parser(f)

    def __and__[S](
        self, other: "Parser[S]" | Callable[[str], tuple[S, str]]
    ) -> "Parser[tuple[T,S]]":
        def f(ins: str):
            s, remaining = self(ins)
            t, remaining = other(remaining)
            return (s, t), remaining

        return Parser(f)

    def __lshift__[S](
        self, other: "Parser[S]" | Callable[[str], tuple[S, str]]
    ) -> "Parser[T]":
        def f(ins: str):
            t, remaining = self(ins)
            _, remaining = other(remaining)
            return t, remaining

        return Parser(f)

    def __rshift__[S](
        self, other: "Parser[S]" | Callable[[str], tuple[S, str]]
    ) -> "Parser[S]":
        def f(ins: str):
            _, remaining = self(ins)
            s, remaining = other(remaining)
            return s, remaining

        return Parser(f)

    def opt(self) -> "Parser[T|None]":
        def f(ins: str):
            try:
                return self(ins)
            except ParserError:
                return None, ins

        return Parser(f)

    def map[A](self, fn: Callable[[T], A]) -> "Parser[A]":
        def f(ins: str):
            t, remaining = self(ins)
            return fn(t), remaining

        return Parser(f)

    def coerce[A](self, a: A) -> "Parser[A]":
        def f(ins: str):
            t, remaining = self(ins)
            return a, remaining

        return Parser(f)

    def rep(self, sep: "Parser[str] | None" = None) -> "Parser[list[T]]":
        def f(ins: str):
            outs: list[T] = []
            while True:
                try:
                    t, ins = self(ins)
                    if sep:
                        try:
                            _, ins = sep(ins)
                        except ParserError:
                            pass
                    outs.append(t)
                except ParserError:
                    break
            return outs, ins

        return Parser(f)

    def fail(self, entity: str) -> "Parser[Never]":
        def f(ins: str):
            raise ParserError(f"{entity} not supported.")

        return Parser(f)


@overload
def seq[A, B](*args: *tuple[Parser[A], Parser[B]]) -> Parser[tuple[A, B]]: ...
@overload
def seq[A, B, C](
    *args: *tuple[Parser[A], Parser[B], Parser[C]],
) -> Parser[tuple[A, B, C]]: ...
@overload
def seq[A, B, C, D](
    *args: *tuple[Parser[A], Parser[B], Parser[C], Parser[D]],
) -> Parser[tuple[A, B, C, D]]: ...
def seq(*args: Parser) -> Parser[tuple]:
    def f(ins: str):
        outs = []
        for arg in args:
            s, ins = arg(ins)
            outs.append(s)
        return tuple(outs), ins

    return Parser(f)


def lit(*args: str) -> Parser[str]:
    def f(ins: str):
        for a in args:
            if ins.startswith(a):
                return a, ins[len(a) :]

        raise ParserError(f"lit: expected {args} found '{ins[:20]}'")

    return Parser(f)


def reg(regex: str) -> Parser[str]:
    def f(ins: str):
        r = re.compile("^(" + regex + ")")

        if a := r.match(ins):
            return a.group(0), ins[a.end() :]

        raise ParserError(f"reg: expected regex {regex} found '{ins[:20]}'")

    return Parser(f)
