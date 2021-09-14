"""A basic S-expression parser.

Example usage:
    $ python sexp.py '123'
    123
    $ python sexp.py 'hello'
    'hello'
    $ python sexp.py '(hello world)'
    ['hello', 'world']
    $ python sexp.py '(foo (bar) thing 9 hello 9)'
    ['foo', ['bar'], 'thing', 9, 'hello', 9]
    $ python sexp.py '(hello world'
    UnexpectedEOF: Expected brace ')' but reached end of file.
"""


import sys
from typing import Any

from tokenstream import InvalidSyntax, TokenStream


def parse_sexp(stream: TokenStream) -> Any:
    with stream.syntax(brace=r"\(|\)", number=r"\d+", name=r"\w+"):
        brace, number, name = stream.expect(("brace", "("), "number", "name")
        if brace:
            return [parse_sexp(stream) for _ in stream.peek_until(("brace", ")"))]
        elif number:
            return int(number.value)
        elif name:
            return name.value


if __name__ == "__main__":
    try:
        stream = TokenStream(" ".join(sys.argv[1:]))
        result = parse_sexp(stream)
        stream.expect_eof()
        print(repr(result))
    except InvalidSyntax as exc:
        print(f"{exc.__class__.__name__}: {exc}")
