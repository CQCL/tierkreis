"""Elementary parser and parser combinators.

Similar to https://github.com/drhagen/parsita
But https://github.com/drhagen/parsita/blob/83925f035d0777debfe5a6cb53b4944b4b5bcfe2/src/parsita/parsers/_sequential.py#L10
doesn't type check things correctly.
"""

import re
from typing import Callable, Never, overload

from tierkreis.exceptions import TierkreisError


class ParserError(TierkreisError): ...


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
        """Try the left parser and only if it fails try the right parser."""

        def f(ins: str):
            try:
                return self(ins)
            except ParserError:
                return other(ins)

        return Parser(f)

    def __and__[S](
        self, other: "Parser[S]" | Callable[[str], tuple[S, str]]
    ) -> "Parser[tuple[T,S]]":
        """Use the left parser and then use the right parser on the remaining input."""

        def f(ins: str):
            s, remaining = self(ins)
            t, remaining = other(remaining)
            return (s, t), remaining

        return Parser(f)

    def __lshift__[S](
        self, other: "Parser[S]" | Callable[[str], tuple[S, str]]
    ) -> "Parser[T]":
        """Use the left parser and then the right parser but discard the result of the right parser."""

        def f(ins: str):
            t, remaining = self(ins)
            _, remaining = other(remaining)
            return t, remaining

        return Parser(f)

    def __rshift__[S](
        self, other: "Parser[S]" | Callable[[str], tuple[S, str]]
    ) -> "Parser[S]":
        """Use the left parser and then the right parser but discard the result of the left parser."""

        def f(ins: str):
            _, remaining = self(ins)
            s, remaining = other(remaining)
            return s, remaining

        return Parser(f)

    def opt(self) -> "Parser[T|None]":
        """Make the parser optional; if it fails then return None and carry on."""

        def f(ins: str):
            try:
                return self(ins)
            except ParserError:
                return None, ins

        return Parser(f)

    def map[A](self, fn: Callable[[T], A]) -> "Parser[A]":
        """Apply `fn` to transform the output of the parser."""

        def f(ins: str):
            t, remaining = self(ins)
            return fn(t), remaining

        return Parser(f)

    def coerce[A](self, a: A) -> "Parser[A]":
        """Shorthand for maps that don't need an argument.

        Not strictly speaking required."""

        def f(ins: str):
            t, remaining = self(ins)
            return a, remaining

        return Parser(f)

    def rep(self, sep: "Parser[str] | None" = None) -> "Parser[list[T]]":
        """Repeatedly apply a parser with an optional separator.

        The results of the separator parser are discarded."""

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
        """Fail early if we find something we don't support.

        Not strictly speaking required."""

        def f(ins: str):
            self(ins)
            raise TierkreisError(f"{entity} not supported.")

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
@overload
def seq[A, B, C, D, E](
    *args: *tuple[Parser[A], Parser[B], Parser[C], Parser[D], Parser[E]],
) -> Parser[tuple[A, B, C, D, E]]: ...
def seq(*args: Parser) -> Parser[tuple]:
    """Run a sequence of parsers one after the other
    and collect their outputs in a tuple."""

    def f(ins: str):
        outs = []
        for arg in args:
            s, ins = arg(ins)
            outs.append(s)
        return tuple(outs), ins

    return Parser(f)


def lit(*args: str) -> Parser[str]:
    """If the input starts with one of the strings in `args`
    then take the string off the stream and return it."""

    def f(ins: str):
        for a in args:
            if ins.startswith(a):
                return a, ins[len(a) :]

        raise ParserError(f"lit: expected {args} found '{ins[:20]}'")

    return Parser(f)


def reg(regex: str) -> Parser[str]:
    """If start of the input matches the `regex`
    then take the matching text off the stream and return it.

    Please don't pass match groups within the regex; they will be taken care of."""

    def f(ins: str):
        r = re.compile("^(" + regex + ")")

        if a := r.match(ins):
            return a.group(0), ins[a.end() :]

        raise ParserError(f"reg: expected regex {regex} found '{ins[:20]}'")

    return Parser(f)
