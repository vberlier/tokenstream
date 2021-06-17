# tokenstream

[![GitHub Actions](https://github.com/vberlier/tokenstream/workflows/CI/badge.svg)](https://github.com/vberlier/tokenstream/actions)
[![PyPI](https://img.shields.io/pypi/v/tokenstream.svg)](https://pypi.org/project/tokenstream/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/tokenstream.svg)](https://pypi.org/project/tokenstream/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)

> A versatile token stream for handwritten parsers.

```python
from tokenstream import TokenStream

def parse_sexp(stream: TokenStream):
    """A basic S-expression parser."""
    with stream.syntax(brace=r"\(|\)", number=r"\d+", name=r"\w+"):
        brace, number, name = stream.expect(("brace", "("), "number", "name")
        if brace:
            return [parse_sexp(stream) for _ in stream.peek_until(("brace", ")"))]
        elif number:
            return int(number.value)
        elif name:
            return name.value

print(parse_sexp(TokenStream("(hello (world 42))")))  # ['hello', ['world', 42]]
```

## Introduction

Writing recursive-descent parsers by hand can be quite elegant but it's often a bit more verbose than expected, especially when it comes to handling indentation and reporting proper syntax errors. This package provides a powerful general-purpose token stream that addresses these issues and more.

### Features

- Define the set of recognizable tokens dynamically with regular expressions
- Transparently skip over irrelevant tokens
- Expressive API for matching, collecting, peeking, and expecting tokens
- Clean error reporting with line numbers and column numbers
- Contextual support for indentation-based syntax
- Checkpoints for backtracking parsers
- Works well with Python 3.10+ match statements

Check out the [`examples`](https://github.com/vberlier/tokenstream/tree/main/examples) directory for practical examples.

## Installation

The package can be installed with `pip`.

```bash
pip install tokenstream
```

## Getting started

You can define tokens with the `syntax()` method. The keyword arguments associate regular expression patterns to token types. The method returns a context manager during which the specified tokens will be recognized.

```python
stream = TokenStream("hello world")

with stream.syntax(word=r"\w+"):
    print([token.value for token in stream])  # ['hello', 'world']
```

Check out the full [API reference](https://vberlier.github.io/tokenstream/api_reference/) for more details.

### Expecting tokens

The token stream is iterable and will yield all the extracted tokens one after the other. You can also retrieve tokens from the token stream one at a time by using the `expect()` method.

```python
stream = TokenStream("hello world")

with stream.syntax(word=r"\w+"):
    print(stream.expect().value)  # "hello"
    print(stream.expect().value)  # "world"
```

The `expect()` method lets you ensure that the extracted token matches a specified type and will raise an exception otherwise.

```python
stream = TokenStream("hello world")

with stream.syntax(number=r"\d+", word=r"\w+"):
    print(stream.expect("word").value)  # "hello"
    print(stream.expect("number").value)  # UnexpectedToken: Expected number but got word 'world'
```

### Filtering the stream

Newlines and whitespace are ignored by default. You can reject interspersed whitespace by intercepting the built-in `newline` and `whitespace` tokens.

```python
stream = TokenStream("hello world")

with stream.syntax(word=r"\w+"), stream.intercept("newline", "whitespace"):
    print(stream.expect("word").value)  # "hello"
    print(stream.expect("word").value)  # UnexpectedToken: Expected word but got whitespace ' '
```

The opposite of the `intercept()` method is `ignore()`. It allows you to ignore tokens and handle comments pretty easily.

```python
stream = TokenStream(
    """
    # this is a comment
    hello # also a comment
    world
    """
)

with stream.syntax(word=r"\w+", comment=r"#.+$"), stream.ignore("comment"):
    print([token.value for token in stream])  # ['hello', 'world']
```

### Indentation

To enable indentation you can use the `indent()` method. The stream will now yield balanced pairs of `indent` and `dedent` tokens when the indentation changes.

```python
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
```

To prevent some tokens from triggering unwanted indentation changes you can use the `skip` argument.

```python
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
```

### Checkpoints

The `checkpoint()` method returns a context manager that resets the stream to the current token at the end of the `with` statement. You can use the returned `commit()` function to keep the state of the stream at the end of the `with` statement.

```python
stream = TokenStream("hello world")

with stream.syntax(word=r"\w+"):
    with stream.checkpoint():
        print([token.value for token in stream])  # ['hello', 'world']
    with stream.checkpoint() as commit:
        print([token.value for token in stream])  # ['hello', 'world']
        commit()
    print([token.value for token in stream])  # []
```

### Match statements

Match statements make it very intuitive to process tokens extracted from the token stream. If you're using Python 3.10+ give it a try and see if you like it.

```python
from tokenstream import TokenStream, Token

def parse_sexp(stream: TokenStream):
    """A basic S-expression parser that uses Python 3.10+ match statements."""
    with stream.syntax(brace=r"\(|\)", number=r"\d+", name=r"\w+"):
        match stream.expect_any(("brace", "("), "number", "name"):
            case Token(type="brace"):
                return [parse_sexp(stream) for _ in stream.peek_until(("brace", ")"))]
            case Token(type="number") as number :
                return int(number.value)
            case Token(type="name") as name:
                return name.value
```

## Contributing

Contributions are welcome. Make sure to first open an issue discussing the problem or the new feature before creating a pull request. The project uses [`poetry`](https://python-poetry.org/).

```bash
$ poetry install
```

You can run the tests with `poetry run pytest`.

```bash
$ poetry run pytest
```

The project must type-check with [`pyright`](https://github.com/microsoft/pyright). If you're using VSCode the [`pylance`](https://marketplace.visualstudio.com/items?itemName=ms-python.vscode-pylance) extension should report diagnostics automatically. You can also install the type-checker locally with `npm install` and run it from the command-line.

```bash
$ npm run watch
$ npm run check
$ npm run verifytypes
```

The code follows the [`black`](https://github.com/psf/black) code style. Import statements are sorted with [`isort`](https://pycqa.github.io/isort/).

```bash
$ poetry run isort tokenstream examples tests
$ poetry run black tokenstream examples tests
$ poetry run black --check tokenstream examples tests
```

---

License - [MIT](https://github.com/vberlier/tokenstream/blob/main/LICENSE)
