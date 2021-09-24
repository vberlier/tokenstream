__all__ = [
    "SourceLocation",
    "set_location",
    "UNKNOWN_LOCATION",
]


from dataclasses import FrozenInstanceError, replace
from typing import Any, NamedTuple, TypeVar

T = TypeVar("T")


class SourceLocation(NamedTuple):
    """Class representing a location within an input string."""

    pos: int
    lineno: int
    colno: int

    @property
    def unknown(self) -> bool:
        """Whether the location is unknown.

        >>> location = UNKNOWN_LOCATION
        >>> location.unknown
        True
        """
        return self.pos < 0

    def format(self, filename: str, message: str) -> str:
        """Return a message formatted with the given filename and the current location.

        >>> SourceLocation(42, 3, 12).format("path/to/file.txt", "Some error message")
        'path/to/file.txt:3:12: Some error message'
        """
        return f"{filename}:{self.lineno}:{self.colno}: {message}"

    def with_horizontal_offset(self, offset: int) -> "SourceLocation":
        """Create a modified source location along the horizontal axis.

        >>> SourceLocation(0, 1, 1).with_horizontal_offset(41)
        SourceLocation(pos=41, lineno=1, colno=42)
        """
        if self.unknown:
            return self
        return SourceLocation(self.pos + offset, self.lineno, self.colno + offset)


UNKNOWN_LOCATION = SourceLocation(pos=-1, lineno=0, colno=0)


def set_location(
    obj: T,
    location: Any = UNKNOWN_LOCATION,
    end_location: Any = UNKNOWN_LOCATION,
) -> T:
    """Set the location and end_location attributes.

    The function returns the given object or a new instance if the object
    is a namedtuple or a frozen dataclass. The location can be copied from another
    object with location and end_location attributes.

    >>> token = Token("number", "123", UNKNOWN_LOCATION, UNKNOWN_LOCATION)
    >>> updated_token = set_location(token, SourceLocation(15, 6, 1))
    >>> updated_token
    Token(type='number', value='123', location=SourceLocation(pos=15, lineno=6, colno=1), end_location=SourceLocation(pos=15, lineno=6, colno=1))
    >>> updated_token = set_location(
    ...     updated_token,
    ...     end_location=updated_token.location.with_horizontal_offset(len(updated_token.value)),
    ... )
    >>> set_location(token, updated_token)
    Token(type='number', value='123', location=SourceLocation(pos=15, lineno=6, colno=1), end_location=SourceLocation(pos=18, lineno=6, colno=4))
    """
    if not isinstance(end_location, SourceLocation):
        end_location = getattr(end_location, "end_location", UNKNOWN_LOCATION)

    if not isinstance(location, SourceLocation):
        if end_location.unknown:
            end_location = getattr(location, "end_location", UNKNOWN_LOCATION)
        location = getattr(location, "location", UNKNOWN_LOCATION)

    if location.unknown:
        location = getattr(obj, "location", location)
    if end_location.unknown:
        end_location = getattr(obj, "end_location", end_location)

    end_location = max(location, end_location)

    if isinstance(obj, tuple):
        return obj._replace(location=location, end_location=end_location)  # type: ignore

    try:
        obj.location = location  # type: ignore
        obj.end_location = end_location  # type: ignore
    except FrozenInstanceError:
        return replace(obj, location=location, end_location=end_location)

    return obj
