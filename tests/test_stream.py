from typing import List, Tuple, Union

import pytest

from tokenstream import TokenStream, UnexpectedToken


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

        with pytest.raises(  # type: ignore
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
        assert len(stream.ignored_tokens) == 0

        stream.expect("word").value
        with pytest.raises(  # type: ignore
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

    def argument(stream: TokenStream) -> Union[str, Tuple[int, int, int]]:
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

    def argument(stream: TokenStream) -> Union[str, Tuple[int, int, int]]:
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

    def triplet(stream: TokenStream) -> Tuple[int, int, int]:
        return (
            int(stream.expect("number").value),
            int(stream.expect("number").value),
            int(stream.expect("number").value),
        )

    def argument(stream: TokenStream) -> Union[str, Tuple[int, int, int]]:  # type: ignore
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
    result: List[Union[str, Tuple[int, int, int]]] = []

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
