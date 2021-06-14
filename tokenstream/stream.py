__all__ = [
    "TokenStream",
]

import re
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import (
    Any,
    ClassVar,
    Dict,
    Iterable,
    Iterator,
    List,
    Optional,
    Set,
    Tuple,
    overload,
)

from .error import InvalidSyntax, UnexpectedEOF, UnexpectedToken
from .token import SourceLocation, Token, TokenPattern

SyntaxRules = Tuple[Tuple[str, str], ...]


def extra_field(**kwargs: Any) -> Any:
    return field(repr=False, init=False, hash=False, compare=False, **kwargs)


@dataclass
class TokenStream:
    """A versatile token stream for handwritten parsers."""

    source: str
    syntax_rules: SyntaxRules = ()
    regex: "re.Pattern[str]" = extra_field()

    location: SourceLocation = extra_field()

    index: int = -1
    tokens: List[Token] = extra_field(default_factory=list)
    indentation: List[int] = extra_field(default_factory=list)
    indentation_skip: Set[str] = extra_field(default_factory=set)

    generator: Iterator[Token] = extra_field()
    ignored_tokens: Set[str] = extra_field()

    regex_cache: ClassVar[Dict[SyntaxRules, "re.Pattern[str]"]] = {}

    def __post_init__(self) -> None:
        self.bake_regex()
        self.location = SourceLocation(pos=0, lineno=1, colno=1)
        self.generator = self.generate_tokens()
        self.ignored_tokens = {"whitespace", "newline"}

    def bake_regex(self) -> None:
        """Compile the syntax rules."""
        self.regex = re.compile(
            "|".join(
                f"(?P<{name}>{regex})"
                for name, regex in self.syntax_rules
                + (
                    ("newline", r"\n"),
                    ("whitespace", r"\s+"),
                )
            ),
            re.MULTILINE,
        )
        self.regex_cache[self.syntax_rules] = self.regex

    def crop(self) -> None:
        """Clear upcoming precomputed tokens."""
        if self.index + 1 < len(self.tokens):
            self.tokens = self.tokens[: self.index + 1]
        if self.index >= 0:
            self.location = self.current.end_location

    @contextmanager
    def syntax(self, **kwargs: str) -> Iterator[None]:
        """Extend token syntax using regular expressions."""
        previous_syntax = self.syntax_rules
        self.syntax_rules = tuple(kwargs.items()) + tuple(
            (k, v) for k, v in previous_syntax if k not in kwargs
        )

        if regex := self.regex_cache.get(self.syntax_rules):
            self.regex = regex
        else:
            self.bake_regex()

        self.crop()

        try:
            yield
        finally:
            self.syntax_rules = previous_syntax

    @contextmanager
    def reset_syntax(self, **kwargs: str) -> Iterator[None]:
        """Overwrite the existing syntax rules."""
        previous_syntax = self.syntax_rules
        self.syntax_rules = ()

        try:
            with self.syntax(**kwargs):
                yield
        finally:
            self.syntax_rules = previous_syntax

    @contextmanager
    def indent(
        self,
        enable: bool = True,
        skip: Optional[Iterable[str]] = None,
    ) -> Iterator[None]:
        """Enable or disable indentation."""
        previous_indentation = self.indentation
        self.indentation = [0] if enable else []

        previous_skip = self.indentation_skip
        if skip is not None:
            self.indentation_skip = set(skip)

        self.crop()

        try:
            yield
        finally:
            self.indentation = previous_indentation
            self.indentation_skip = previous_skip

    @contextmanager
    def intercept(self, *token_types: str) -> Iterator[None]:
        """Intercept tokens matching the given types."""
        previous_ignored = self.ignored_tokens
        self.ignored_tokens = self.ignored_tokens - set(token_types)

        try:
            yield
        finally:
            self.ignored_tokens = previous_ignored

    @contextmanager
    def ignore(self, *token_types: str) -> Iterator[None]:
        """Ignore tokens matching the given types."""
        previous_ignored = self.ignored_tokens
        self.ignored_tokens = self.ignored_tokens | set(token_types)

        try:
            yield
        finally:
            self.ignored_tokens = previous_ignored

    @property
    def current(self) -> Token:
        """The current token."""
        return self.tokens[self.index]

    @property
    def previous(self) -> Token:
        """The previous token."""
        return self.tokens[self.index - 1]

    @property
    def leftover(self) -> str:
        """The remaining input."""
        pos = self.current.end_location.pos if self.index >= 0 else 0
        return self.source[pos:]

    def head(self, characters: int = 50) -> str:
        """Preview the characters ahead of the current token."""
        pos = self.current.end_location.pos if self.index >= 0 else 0
        value = self.source[pos : pos + characters]
        return value.partition("\n")[0]

    def emit_token(self, token_type: str, value: str = "") -> Token:
        """Generate a token in the token stream."""
        end_pos = self.location.pos + len(value)
        end_lineno = self.location.lineno + value.count("\n")

        if (line_start := value.rfind("\n")) == -1:
            end_colno = self.location.colno + len(value)
        else:
            end_colno = end_pos - line_start + 1

        token = Token(
            type=token_type,
            value=value,
            location=self.location,
            end_location=SourceLocation(end_pos, end_lineno, end_colno),
        )

        self.location = token.end_location
        self.tokens.append(token)

        self.index = len(self.tokens) - 1

        return token

    def emit_error(self, exc: InvalidSyntax) -> InvalidSyntax:
        """Raise an invalid syntax exception."""
        if self.index >= 0:
            exc.location = self.current.end_location
        else:
            exc.location = SourceLocation(pos=0, lineno=1, colno=1)
        return exc

    def generate_tokens(self) -> Iterator[Token]:
        """Extract tokens from the input string."""
        while self.location.pos < len(self.source):
            if match := self.regex.match(self.source, self.location.pos):
                assert match.lastgroup

                if (
                    self.tokens
                    and self.indentation
                    and self.current.type == "whitespace"
                    and self.current.location.colno == 1
                    and match.lastgroup not in self.ignored_tokens
                ):
                    indent = len(self.current.value.expandtabs())

                    while indent < self.indentation[-1]:
                        self.emit_token("dedent")
                        self.indentation.pop()
                        yield self.current

                    if indent > self.indentation[-1]:
                        self.emit_token("indent")
                        self.indentation.append(indent)
                        yield self.current

                self.emit_token(match.lastgroup, match.group())
                yield self.current
            else:
                raise self.emit_error(InvalidSyntax(self.head()))

        while len(self.indentation) > 1:
            self.emit_token("dedent")
            self.indentation.pop()
            yield self.current

    def __iter__(self) -> "TokenStream":
        return self

    def __next__(self) -> Token:
        if self.index + 1 < len(self.tokens):
            self.index += 1
        else:
            next(self.generator)

        if self.current.type in self.ignored_tokens:
            return next(self)

        return self.current

    def peek(self, n: int = 1) -> Optional[Token]:
        """Peek around the current token."""
        previous_index = self.index
        token = None

        try:
            while n < 0:
                if self.index <= 0:
                    return None

                while self.index > 0:
                    self.index -= 1
                    if self.current.type not in self.ignored_tokens:
                        token = self.current
                        break
                n += 1

            for _ in range(n):
                for token in self:
                    break
                else:
                    return None
        finally:
            self.index = previous_index

        return token

    def peek_until(self, *patterns: TokenPattern) -> Iterator[Token]:
        """Collect tokens until one of the given patterns matches."""
        while token := self.peek():
            if token.match(*patterns):
                next(self)
                return
            yield token
        raise self.emit_error(UnexpectedEOF(patterns))

    @overload
    def collect(self) -> Iterator[Token]:
        ...

    @overload
    def collect(self, pattern: TokenPattern) -> Iterator[Token]:
        ...

    @overload
    def collect(
        self,
        pattern1: TokenPattern,
        pattern2: TokenPattern,
        *patterns: TokenPattern,
    ) -> Iterator[List[Optional[Token]]]:
        ...

    def collect(self, *patterns: TokenPattern) -> Iterator[Any]:
        """Collect tokens matching the given patterns."""
        if not patterns:
            return self

        while token := self.peek():
            matches = [token if token.match(pattern) else None for pattern in patterns]

            if not any(matches):
                break

            next(self)

            if len(matches) == 1:
                yield matches[0]
            else:
                yield matches

    @overload
    def expect(self) -> Token:
        ...

    @overload
    def expect(self, pattern: TokenPattern) -> Token:
        ...

    @overload
    def expect(
        self,
        pattern1: TokenPattern,
        pattern2: TokenPattern,
        *patterns: TokenPattern,
    ) -> List[Optional[Token]]:
        ...

    def expect(self, *patterns: TokenPattern) -> Any:
        """Match the given patterns and raise an exception if the next token doesn't match."""
        for result in self.collect(*patterns):
            return result

        if token := self.peek():
            raise self.emit_error(UnexpectedToken(token, patterns))
        else:
            raise self.emit_error(UnexpectedEOF(patterns))

    def get(self, *patterns: TokenPattern) -> Optional[Token]:
        """Return the next token if it matches any of the given patterns."""
        if token := self.peek():
            if token.match(*patterns):
                return next(self)
        return None

    def expect_any(self, *patterns: TokenPattern) -> Token:
        """Make sure that the next token matches one of the given patterns or raise an exception."""
        if token := self.peek():
            if token.match(*patterns):
                return next(self)
            else:
                raise self.emit_error(UnexpectedToken(token, patterns))
        else:
            raise self.emit_error(UnexpectedEOF(patterns))

    def expect_eof(self) -> None:
        """Raise an exception if there is leftover input."""
        if self.peek():
            raise self.emit_error(InvalidSyntax(self.head()))
