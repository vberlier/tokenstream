__all__ = [
    "InvalidSyntax",
    "UnexpectedEOF",
    "UnexpectedToken",
]


from typing import Sequence

from .location import SourceLocation
from .token import Token, TokenPattern, explain_patterns


class InvalidSyntax(Exception):
    """Raised when the input contains invalid syntax.

    Attributes
    ----------
    location
        The location of the error.
    """

    location: SourceLocation
    end_location: SourceLocation

    def __init__(self, *args: object) -> None:
        super().__init__(*args)
        self.location = SourceLocation(0, 1, 1)
        self.end_location = SourceLocation(0, 1, 1)

    def format(self, filename: str) -> str:
        """Return a string representing the error and its location in a given file.

        >>> try:
        ...     TokenStream("hello").expect()
        ... except InvalidSyntax as exc:
        ...     print(exc.format("path/to/my_file.txt"))
        path/to/my_file.txt:1:1: Expected anything but got invalid 'hello'.
        """
        return self.location.format(filename, str(self))


class UnexpectedEOF(InvalidSyntax):
    """Raised when the input ends unexpectedly.

    Attributes
    ----------
    expected_patterns
        The patterns that the parser was expecting instead of reaching end of the file.
    """

    expected_patterns: Sequence[TokenPattern]

    def __init__(self, expected_patterns: Sequence[TokenPattern] = ()):
        super().__init__(expected_patterns)
        self.expected_patterns = expected_patterns

    def __str__(self) -> str:
        if not self.expected_patterns:
            return "Reached end of file unexpectedly."
        return f"Expected {explain_patterns(self.expected_patterns)} but reached end of file."


class UnexpectedToken(InvalidSyntax):
    """Raised when the input contains an unexpected token.

    Attributes
    ----------
    token
        The unexpected token that was encountered.
    expected_patterns
        The patterns that the parser was expecting instead.
    """

    token: Token
    expected_patterns: Sequence[TokenPattern]

    def __init__(self, token: Token, expected_patterns: Sequence[TokenPattern] = ()):
        super().__init__(token, expected_patterns)
        self.token = token
        self.expected_patterns = expected_patterns

    def __str__(self) -> str:
        value = (
            self.token.value[:30] + "..."
            if len(self.token.value) > 32
            else self.token.value
        )
        if value:
            value = f" {value!r}"
        return f"Expected {explain_patterns(self.expected_patterns)} but got {self.token.type}{value}."
