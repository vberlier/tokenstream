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

Writing recursive-descent parsers by hand can be quite elegant but it's often a bit more verbose than expected. In particular, handling indentation and reporting proper syntax errors can be pretty challenging. This package provides a powerful general-purpose token stream that addresses these issues and more.

### Features

- Define token types with regular expressions
- The set of recognizable tokens can be defined dynamically during parsing
- Transparently skip over irrelevant tokens
- Expressive API for matching, collecting, peeking, and expecting tokens
- Clean error reporting with line numbers and column numbers
- Natively understands indentation-based syntax
- Works well with Python 3.10+ match statements

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

The token stream is iterable and will yield all the extracted tokens one after the other.

## Match statements

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
