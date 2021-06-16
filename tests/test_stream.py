from tokenstream import TokenStream


def test_basic():
    stream = TokenStream("hello world")

    with stream.syntax(word=r"\w+"):
        assert [token.value for token in stream] == ["hello", "world"]


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
