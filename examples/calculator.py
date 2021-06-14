"""A basic calculator.

Example usage:
    $ python calculator.py 123
    123
    $ python calculator.py 1 + 6 / 3
    3.0
    $ python calculator.py '(2 + 9) / 3'
    3.6666666666666665
"""


import sys

from tokenstream import InvalidSyntax, TokenStream


def calculate_sum(stream: TokenStream) -> float:
    with stream.syntax(add=r"\+", sub=r"-"):
        result = calculate_product(stream)
        for add, sub in stream.collect("add", "sub"):
            if add:
                result += calculate_product(stream)
            elif sub:
                result -= calculate_product(stream)
        return result


def calculate_product(stream: TokenStream) -> float:
    with stream.syntax(mul=r"\*", div=r"/"):
        result = calculate_value(stream)
        for mul, div in stream.collect("mul", "div"):
            if mul:
                result *= calculate_value(stream)
            elif div:
                result /= calculate_value(stream)
        return result


def calculate_value(stream: TokenStream) -> float:  # type: ignore
    with stream.syntax(number=r"[0-9]+", brace=r"\(|\)"):
        number, brace = stream.expect("number", ("brace", "("))
        if number:
            return int(number.value)
        elif brace:
            result = calculate_sum(stream)
            stream.expect(("brace", ")"))
            return result


if __name__ == "__main__":
    try:
        stream = TokenStream(" ".join(sys.argv[1:]))
        result = calculate_sum(stream)
        stream.expect_eof()
        print(result)
    except InvalidSyntax as exc:
        print(f"{exc.__class__.__name__}: {exc}")
