__all__ = [
    "Token",
    "TokenPattern",
    "SourceLocation",
    "explain_patterns",
]


from typing import NamedTuple, Tuple, Union

TokenPattern = Union[str, Tuple[str, str]]


def explain_patterns(patterns: Tuple[TokenPattern, ...]) -> str:
    """Return a message describing the given patterns."""
    token_types = [
        pattern if isinstance(pattern, str) else f"{pattern[0]} {pattern[1]!r}"
        for pattern in patterns
    ]
    if len(token_types) == 1:
        return token_types[0]
    *head, before_last, last = token_types
    return ", ".join(head + [f"{before_last} or {last}"])


class SourceLocation(NamedTuple):
    """Class representing a location within an input string."""

    pos: int
    lineno: int
    colno: int

    def format(self, filename: str, message: str) -> str:
        """Return a message formatted with the given filename and the current location."""
        return f"{filename}:{self.lineno}:{self.colno}: {message}"


class Token(NamedTuple):
    """Class representing a token."""

    type: str
    value: str
    location: SourceLocation
    end_location: SourceLocation

    def match(self, *patterns: TokenPattern) -> bool:
        """Match the token against one or more patterns."""
        for pattern in patterns:
            if isinstance(pattern, str):
                if self.type == pattern:
                    return True
            else:
                if self.type == pattern[0] and self.value == pattern[1]:
                    return True
        return False
