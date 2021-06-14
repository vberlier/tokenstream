__all__ = [
    "InvalidSyntax",
    "UnexpectedEOF",
    "UnexpectedToken",
]


from typing import Tuple

from .token import SourceLocation, Token, TokenPattern, explain_patterns


class InvalidSyntax(Exception):
    """Raised when the input contains invalid syntax."""

    location: SourceLocation

    def format(self, filename: str, message: str) -> str:
        """Return a string representing the error and its location in a given file."""
        return self.location.format(filename, str(self))


class UnexpectedEOF(InvalidSyntax):
    """Raised when the input ends unexpectedly."""

    expected_patterns: Tuple[TokenPattern, ...]

    def __init__(self, expected_patterns: Tuple[TokenPattern, ...] = ()):
        super().__init__(expected_patterns)
        self.expected_patterns = expected_patterns

    def __str__(self) -> str:
        if not self.expected_patterns:
            return "Reached end of file unexpectedly"
        return f"Expected {explain_patterns(self.expected_patterns)} but reached end of file"


class UnexpectedToken(InvalidSyntax):
    """Raised when the input contains an unexpected token."""

    token: Token
    expected_patterns: Tuple[TokenPattern, ...]

    def __init__(self, token: Token, expected_patterns: Tuple[TokenPattern, ...] = ()):
        super().__init__(token, expected_patterns)
        self.token = token
        self.expected_patterns = expected_patterns

    def __str__(self) -> str:
        return f"Expected {explain_patterns(self.expected_patterns)} but got {self.token.type} {self.token.value!r}"
