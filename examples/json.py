"""A simplistic json parser.

Example usage:
    $ python json.py
    > [1, 2, 3, "hello"]
    [1, 2, 3, 'hello']
    > {
    .   "foo": "bar",
    .   "something": {"else": [42]}
    . }
    {'foo': 'bar', 'something': {'else': [42]}}
    > {"this": "\"that\""}
    {'this': '"that"'}
    > [}
    UnexpectedToken: Expected curly '{', bracket '[', string or number but got curly '}'.
"""


import re
from typing import Any

from tokenstream import InvalidSyntax, Token, TokenStream, UnexpectedEOF

ESCAPE_REGEX = re.compile(r"\\.")
ESCAPE_SEQUENCES = {
    r"\n": "\n",
    r"\"": '"',
    r"\\": "\\",
}


def unquote_string(token: Token) -> str:
    return ESCAPE_REGEX.sub(lambda match: ESCAPE_SEQUENCES[match[0]], token.value[1:-1])


def parse_json(stream: TokenStream) -> Any:
    with stream.syntax(
        curly=r"\{|\}",
        bracket=r"\[|\]",
        string=r'"(?:\\.|[^"\\])*"',
        number=r"\d+",
        colon=r":",
        comma=r",",
    ):
        curly, bracket, string, number = stream.expect(
            ("curly", "{"),
            ("bracket", "["),
            "string",
            "number",
        )

        if curly:
            result: Any = {}

            for key in stream.collect("string"):
                stream.expect("colon")
                result[unquote_string(key)] = parse_json(stream)

                if not stream.get("comma"):
                    break

            stream.expect(("curly", "}"))
            return result

        elif bracket:
            if stream.get(("bracket", "]")):
                return []

            result = [parse_json(stream)]

            for _ in stream.collect("comma"):
                result.append(parse_json(stream))

            stream.expect(("bracket", "]"))
            return result

        elif string:
            return unquote_string(string)

        elif number:
            return int(number.value)


if __name__ == "__main__":
    incomplete = ""

    while True:
        expression = incomplete + input(". " if incomplete else "> ")
        incomplete = ""

        try:
            stream = TokenStream(expression)
            result = parse_json(stream)
            stream.expect_eof()
            print(repr(result))
        except UnexpectedEOF:
            incomplete = expression
        except InvalidSyntax as exc:
            print(f"{exc.__class__.__name__}: {exc}")
