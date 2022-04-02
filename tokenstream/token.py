__all__ = [
    "Token",
    "TokenPattern",
    "explain_patterns",
]


from typing import NamedTuple, Tuple, TypeVar, Union

from .location import SourceLocation, set_location

T = TypeVar("T")


TokenPattern = Union[str, Tuple[str, str]]


def explain_patterns(patterns: Tuple[TokenPattern, ...]) -> str:
    """Return a message describing the given patterns."""
    token_types = list(
        sorted(
            {
                pattern if isinstance(pattern, str) else f"{pattern[0]} {pattern[1]!r}"
                for pattern in patterns
            }
        )
    )
    if not token_types:
        return "anything"
    if len(token_types) == 1:
        return token_types[0]
    *head, before_last, last = token_types
    if len(head) > 6:
        *head, before_last = head[:6]
        last = f"{len(token_types) - 6} other tokens"
    return ", ".join(head + [f"{before_last} or {last}"])


class Token(NamedTuple):
    """Class representing a token."""

    type: str
    value: str
    location: SourceLocation
    end_location: SourceLocation

    def match(self, *patterns: TokenPattern) -> bool:
        """Match the token against one or more patterns.

        Each argument can be either a string corresponding to a token type or a tuple
        with a token type and a token value.

        >>> stream = TokenStream("hello world")
        >>> with stream.syntax(word=r"[a-z]+"):
        ...     print(f"{stream.expect().match(('word', 'hello')) = }")
        ...     print(f"{stream.expect().match('word') = }")
        stream.expect().match(('word', 'hello')) = True
        stream.expect().match('word') = True
        """
        for pattern in patterns:
            if isinstance(pattern, str):
                if self.type == pattern:
                    return True
            else:
                if self.type == pattern[0] and self.value == pattern[1]:
                    return True
        return False

    def emit_error(self, exc: T) -> T:
        """Add location information to invalid syntax exceptions.

        This works exactly like :meth:`tokenstream.stream.TokenStream.emit_error` but it
        associates the location of the token with the syntax error instead of the
        head of the stream.

        >>> stream = TokenStream("hello world")
        >>> with stream.syntax(word=r"[a-z]+"):
        ...     token = stream.expect()
        ...     exc = token.emit_error(InvalidSyntax("goodbye"))
        ...     raise exc
        Traceback (most recent call last):
        InvalidSyntax: goodbye
        >>> exc.location
        SourceLocation(pos=0, lineno=1, colno=1)
        >>> exc.end_location
        SourceLocation(pos=5, lineno=1, colno=6)
        """
        return set_location(exc, self)
