import re
from itertools import islice

import pytest

from tokenstream import (
    INITIAL_LOCATION,
    SourceLocation,
    Token,
    TokenStream,
    UnexpectedToken,
)


def test_basic():
    stream = TokenStream("hello world")

    with stream.syntax(word=r"\w+"):
        assert [token.value for token in stream] == ["hello", "world"]


def test_expect():
    stream = TokenStream("hello world")

    with stream.syntax(word=r"\w+"):
        assert stream.expect().value == "hello"
        assert stream.expect().value == "world"


def test_expect_type():
    stream = TokenStream("hello world")

    with stream.syntax(word=r"\w+"):
        assert stream.expect("word").value == "hello"
        assert stream.expect("word").value == "world"


def test_expect_fail():
    stream = TokenStream("hello world")

    with stream.syntax(number=r"\d+", word=r"\w+"):
        assert stream.expect("word").value == "hello"

        with pytest.raises(
            UnexpectedToken, match="Expected number but got word 'world'"
        ):
            stream.expect("number").value


def test_peek():
    stream = TokenStream("hello world")

    with stream.syntax(word=r"\w+"):
        assert stream.peek() is stream.expect()


def test_peek_multiple():
    stream = TokenStream("hello world")

    with stream.syntax(word=r"\w+"):
        token = stream.peek(2)
        stream.expect()
        assert stream.expect() is token


def test_peek_backwards():
    stream = TokenStream("hello world")

    with stream.syntax(word=r"\w+"):
        first = stream.expect()
        stream.expect()
        assert first is stream.peek(-1)


def test_reject_whitespace():
    stream = TokenStream("hello world")

    with stream.syntax(word=r"\w+"), stream.intercept("whitespace", "newline"):
        assert stream.ignored_tokens == {"eof"}

        stream.expect("word").value
        with pytest.raises(
            UnexpectedToken, match="Expected word but got whitespace ' '"
        ):
            stream.expect("word").value


def test_ignore_comments():
    stream = TokenStream(
        """
        # this is a comment
        hello # also a comment
        world
        """
    )

    with stream.syntax(word=r"\w+", comment=r"#.+$"), stream.ignore("comment"):
        assert [token.value for token in stream] == ["hello", "world"]


def test_whitespace():
    stream = TokenStream("    \t  ")
    with stream.intercept("whitespace"):
        assert stream.expect("whitespace").value == "    \t  "


def test_indent():
    source = """
hello
    world
"""
    stream = TokenStream(source)

    with stream.syntax(word=r"\w+"), stream.indent():
        stream.expect("word")
        stream.expect("indent")
        stream.expect("word")
        stream.expect("dedent")


def test_indent_comment():
    source = """
hello
        # some comment
    world
    """
    stream = TokenStream(source)

    with stream.syntax(word=r"\w+", comment=r"#.+$"), stream.indent(skip=["comment"]):
        stream.expect("word")
        stream.expect("comment")
        stream.expect("indent")
        stream.expect("word")
        stream.expect("dedent")


def test_indent_dedent():
    source = """
hello
    world
thing
"""
    stream = TokenStream(source)

    with stream.syntax(word=r"\w+"), stream.indent():
        stream.expect("word")
        stream.expect("indent")
        stream.expect("word")
        stream.expect("dedent")
        stream.expect("word")


def test_indent_whitespace():
    source = "hello\n    \nworld"
    stream = TokenStream(source)

    with stream.syntax(word=r"\w+"), stream.indent():
        stream.expect("word")
        stream.expect("word")


def test_indent_tricky():
    stream = TokenStream(
        "hello\n"
        "\n"
        "    world\n"
        "\n"
        "    foo\n"
        "        bar\n"
        "\n"
        "        \n"
        "\n"
        "    aaa\n"
        "        bbb\n"
    )

    with stream.syntax(word=r"[a-z]+"), stream.indent():
        stream.expect("word")
        stream.expect("indent")
        stream.expect("word")
        stream.expect("word")
        stream.expect("indent")
        stream.expect("word")
        stream.expect("dedent")
        stream.expect("word")
        stream.expect("indent")
        stream.expect("word")
        stream.expect("dedent")
        stream.expect("dedent")


def test_checkpoint():
    stream = TokenStream("hello world")

    with stream.syntax(word=r"\w+"):
        with stream.checkpoint():
            assert next(stream).value == "hello"
            assert next(stream).value == "world"
        assert [token.value for token in stream] == ["hello", "world"]


def test_checkpoint_commit():
    stream = TokenStream("hello world")

    with stream.syntax(word=r"\w+"):
        with stream.checkpoint() as commit:
            assert next(stream).value == "hello"
            assert next(stream).value == "world"
            commit()
        assert [token.value for token in stream] == []


def test_checkpoint_error():
    stream = TokenStream("hello world 1 2 3 thing")

    def argument(stream: TokenStream) -> str | tuple[int, int, int]:
        with stream.checkpoint() as commit:
            triplet = (
                int(stream.expect("number").value),
                int(stream.expect("number").value),
                int(stream.expect("number").value),
            )
            commit()
            return triplet
        return stream.expect("word").value  # type: ignore

    with stream.syntax(number=r"\d+", word=r"\w+"):
        assert [argument(stream) for _ in stream.peek_until()] == [
            "hello",
            "world",
            (1, 2, 3),
            "thing",
        ]


def test_alternative():
    stream = TokenStream("hello world 1 2 3 thing")

    def argument(stream: TokenStream) -> str | tuple[int, int, int]:
        with stream.alternative():
            return (
                int(stream.expect("number").value),
                int(stream.expect("number").value),
                int(stream.expect("number").value),
            )
        return stream.expect("word").value  # type: ignore

    with stream.syntax(number=r"\d+", word=r"\w+"):
        assert [argument(stream) for _ in stream.peek_until()] == [
            "hello",
            "world",
            (1, 2, 3),
            "thing",
        ]


def test_choose():
    stream = TokenStream("hello world 1 2 3 thing")

    def word(stream: TokenStream) -> str:
        return stream.expect("word").value

    def triplet(stream: TokenStream) -> tuple[int, int, int]:
        return (
            int(stream.expect("number").value),
            int(stream.expect("number").value),
            int(stream.expect("number").value),
        )

    def argument(stream: TokenStream) -> str | tuple[int, int, int]:  # type: ignore
        for parser, alternative in stream.choose(word, triplet):
            with alternative:
                return parser(stream)

    with stream.syntax(number=r"\d+", word=r"\w+"):
        assert [argument(stream) for _ in stream.peek_until()] == [
            "hello",
            "world",
            (1, 2, 3),
            "thing",
        ]


def test_choose_append():
    stream = TokenStream("hello world 1 2 3 thing")
    result: list[str | tuple[int, int, int]] = []

    with stream.syntax(number=r"\d+", word=r"\w+"):
        while stream.peek():
            for argument_type, alternative in stream.choose("word", "triplet"):
                with alternative:
                    result.append(
                        stream.expect("word").value
                        if argument_type == "word"
                        else (
                            int(stream.expect("number").value),
                            int(stream.expect("number").value),
                            int(stream.expect("number").value),
                        )
                    )

    assert result == ["hello", "world", (1, 2, 3), "thing"]


def test_get():
    stream = TokenStream("hello world 1 2 3 thing")

    result: list[int] = []

    with stream.syntax(number=r"\d+", word=r"\w+"):
        while token := stream.get("number", "word"):
            if token.match("number"):
                result.append(int(token.value))
            elif stream.get(("word", "world")):
                result.append(777)

    assert result == [777, 1, 2, 3]


def test_eof():
    stream = TokenStream("hello world")

    with stream.syntax(word=r"\w+"), stream.intercept("eof"):
        stream.expect("word")

        with pytest.raises(UnexpectedToken, match="Expected eof but got word 'world'."):
            stream.expect_eof()

        stream.expect("word")
        stream.expect_eof()

    stream.expect_eof()


WRAP_REGEX = re.compile(r"(\\[ \t]*\r?\n[ \t]*)")


def wrap_lines(source: str) -> tuple[str, list[SourceLocation], list[SourceLocation]]:
    it = iter(WRAP_REGEX.split(source))
    text = next(it)

    result = [text]
    source_mappings: list[SourceLocation] = []
    preprocessed_mappings: list[SourceLocation] = []

    source_location = INITIAL_LOCATION.skip_over(text)
    preprocessed_location = source_location

    while True:
        try:
            backslash, text = islice(it, 2)
        except ValueError:
            break

        source_location = source_location.skip_over(backslash)
        source_mappings.append(source_location)
        preprocessed_mappings.append(preprocessed_location)

        result.append(text)
        source_location = source_location.skip_over(text)
        preprocessed_location = preprocessed_location.skip_over(text)

    return "".join(result), source_mappings, preprocessed_mappings


def test_wrap_line():
    source = r"""
        hello\
        world
        f\
        o\
        o

        bar
    """

    expected_preprocessing = """
        helloworld
        foo

        bar
    """

    stream = TokenStream(source, preprocessor=wrap_lines)
    assert stream.preprocessed_source == expected_preprocessing

    with stream.syntax(word=r"\w+"):
        assert list(stream) == [
            Token(
                type="word",
                value="helloworld",
                location=SourceLocation(pos=9, lineno=2, colno=9),
                end_location=SourceLocation(pos=29, lineno=3, colno=14),
            ),
            Token(
                type="word",
                value="foo",
                location=SourceLocation(pos=38, lineno=4, colno=9),
                end_location=SourceLocation(pos=61, lineno=6, colno=10),
            ),
            Token(
                type="word",
                value="bar",
                location=SourceLocation(pos=71, lineno=8, colno=9),
                end_location=SourceLocation(pos=74, lineno=8, colno=12),
            ),
        ]
