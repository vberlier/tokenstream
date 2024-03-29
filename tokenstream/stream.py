__all__ = [
    "TokenStream",
    "SyntaxRules",
    "Preprocessor",
    "CheckpointCommit",
    "BAKED_REGEX_CACHE",
]

import re
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import (
    Any,
    Callable,
    ContextManager,
    Iterable,
    Iterator,
    Sequence,
    TypeVar,
    overload,
)

from .error import InvalidSyntax, UnexpectedEOF, UnexpectedToken
from .location import INITIAL_LOCATION, SourceLocation, set_location
from .token import Token, TokenPattern

T = TypeVar("T")


SyntaxRules = tuple[tuple[str, str], ...]

Preprocessor = Callable[
    [str], tuple[str, Sequence[SourceLocation], Sequence[SourceLocation]]
]


def extra_field(**kwargs: Any) -> Any:
    return field(repr=False, init=False, hash=False, compare=False, **kwargs)


@dataclass
class CheckpointCommit:
    """Handle for managing checkpoints.

    Attributes
    ----------
    index
        The index of the stream when the checkpoint was created.

    rollback
        Whether the checkpoint should be rolled back or not. This attribute is set to
        ``False`` when the handle is invoked as a function.
    """

    index: int
    rollback: bool = True

    def __call__(self) -> None:
        self.rollback = False


BAKED_REGEX_CACHE: dict[Any, dict[SyntaxRules, re.Pattern[str]]] = {}


@dataclass
class TokenStream:
    r"""A versatile token stream for handwritten parsers.

    The stream is iterable and will yield all the extracted tokens one after the other.

    >>> stream = TokenStream("hello world")
    >>> with stream.syntax(word=r"\w+"):
    ...     print([token.value for token in stream])
    ['hello', 'world']

    Attributes
    ----------
    source
        The input string.

        >>> stream = TokenStream("hello world")
        >>> stream.source
        'hello world'

    preprocessor
        A preprocessor that will emit source location mappings for the transformed input.

    syntax_rules
        A tuple of ``(token_type, pattern)`` pairs that define the recognizable tokens.

        >>> stream = TokenStream("hello world")
        >>> with stream.syntax(word=r"[a-z]+"):
        ...     print(stream.syntax_rules)
        (('word', '[a-z]+'),)

    regex
        The compiled regular expression generated from the syntax rules.

        >>> stream = TokenStream("hello world")
        >>> with stream.syntax(word=r"[a-z]+"):
        ...     print(stream.regex.pattern)
        (?P<word>[a-z]+)|(?P<newline>\r?\n)|(?P<whitespace>[ \t]+)|(?P<invalid>.+)

    index
        The index of the current token in the list of extracted tokens.

        You can technically mutate this attribute directly if you want to
        reset the stream back to a specific token, but you should probably
        use the higher-level :meth:`checkpoint` method for this.

    tokens
        A list accumulating all the extracted tokens.

        The list contains all the extracted tokens, even the ones ignored
        when using the :meth:`ignore` method. For this reason you shouldn't
        try to index into the list directly. Use methods like :meth:`expect`,
        :meth:`peek`, or :meth:`collect` instead.

    indentation
        A list that keeps track of the indentation levels when indentation is enabled.
        The list is empty when indentation is disabled.

    indentation_skip
        A set of token types for which the token stream shouldn't emit indentation
        changes.

        Can be set using the ``skip`` argument of the :meth:`indent` method.

    generator
        An instance of the :meth:`generate_tokens` generator that the stream iterates
        iterates through to extract and emit tokens.

        Should be considered internal.

    ignored_tokens
        A set of token types that the stream skips over when iterating, peeking,
        and expecting tokens.

    data
        A dictionary holding arbitrary user data.

    regex_module
        The module to use for compiling regex patterns. Uses the built-in :mod:`re`
        module by default. It's possible to swap it out for https://github.com/mrabarnett/mrab-regex
        by specifying the module as keyword argument when creating a new :class:`TokenStream`.

    regex_cache
        A cache that keeps a reference to the compiled regular expression associated
        to each set of syntax rules.
    """

    source: str
    syntax_rules: SyntaxRules = extra_field(default=())
    regex: re.Pattern[str] = extra_field()

    preprocessor: Preprocessor | None = field(default=None)
    preprocessed_source: str = extra_field()
    source_mappings: Sequence[SourceLocation] = extra_field(default_factory=list)
    preprocessed_mappings: Sequence[SourceLocation] = extra_field(default_factory=list)

    preprocessed_pos: int = extra_field(default=0)
    preprocessed_lineno: int = extra_field(default=1)
    preprocessed_colno: int = extra_field(default=1)
    preprocessed_locations: list[SourceLocation] = extra_field(default_factory=list)

    index: int = extra_field(default=-1)
    tokens: list[Token] = extra_field(default_factory=list)
    indentation: list[int] = extra_field(default_factory=list)
    indentation_skip: set[str] = extra_field(default_factory=set)

    generator: Iterator[Token] = extra_field()
    ignored_tokens: set[str] = extra_field()

    data: dict[str, Any] = extra_field(default_factory=dict)

    regex_module: Any = field(default=re, repr=False)
    regex_cache: dict[SyntaxRules, re.Pattern[str]] = extra_field()

    def __post_init__(self) -> None:
        if self.preprocessor:
            self.preprocessed_source, *mappings = self.preprocessor(self.source)
            self.source_mappings, self.preprocessed_mappings = mappings
        else:
            self.preprocessed_source = self.source

        self.generator = self.generate_tokens()
        self.ignored_tokens = {"whitespace", "newline", "eof"}
        self.regex_cache = BAKED_REGEX_CACHE.setdefault(self.regex_module, {})
        self.bake_regex()

    def bake_regex(self) -> None:
        """Compile the syntax rules.

        Called automatically upon instantiation and when the syntax rules change.
        Should be considered internal.
        """
        if regex := self.regex_cache.get(self.syntax_rules):
            self.regex = regex
            return

        self.regex = self.regex_module.compile(
            "|".join(
                f"(?P<{name}>{regex})"
                for name, regex in self.syntax_rules
                + (
                    ("newline", r"\r?\n"),
                    ("whitespace", r"[ \t]+"),
                    ("invalid", r".+"),
                )
            ),
            self.regex_module.MULTILINE,
        )

        self.regex_cache[self.syntax_rules] = self.regex

    def crop(self) -> None:
        """Clear upcoming precomputed tokens.

        >>> stream = TokenStream("hello world")
        >>> with stream.syntax(word=r"[a-z]+"):
        ...     word = stream.expect("word")
        ...     with stream.checkpoint():
        ...         word = stream.expect("word")
        ...     print(stream.tokens[-1].value)
        ...     stream.crop()
        ...     print(stream.tokens[-1].value)
        world
        hello

        Mostly used to ensure consistency in some of the provided context managers.
        Should be considered internal.
        """
        del self.tokens[self.index + 1 :]
        del self.preprocessed_locations[self.index + 1 :]
        self.preprocessed_pos, self.preprocessed_lineno, self.preprocessed_colno = (
            self.preprocessed_locations[self.index] if self.index >= 0 else (0, 1, 1)
        )

    @contextmanager
    def syntax(self, **kwargs: str | None) -> Iterator[None]:
        """Extend token syntax using regular expressions.

        The keyword arguments associate regular expression patterns to token types. The method returns a context manager during which the specified tokens will be recognized.

        >>> stream = TokenStream("hello world 123")
        >>> with stream.syntax(word=r"[a-z]+", number=r"[0-9]+"):
        ...     stream.expect("word").value
        ...     stream.expect("word").value
        ...     stream.expect("number").value
        'hello'
        'world'
        '123'

        Nesting multiple :meth:`syntax` calls will combine the rules.

        >>> stream = TokenStream("hello world 123")
        >>> with stream.syntax(word=r"[a-z]+"):
        ...     with stream.syntax(number=r"[0-9]+"):
        ...         stream.expect("word").value
        ...         stream.expect("word").value
        ...         stream.expect("number").value
        'hello'
        'world'
        '123'

        You can also disable a previous rule by using ``None``.

        >>> stream = TokenStream("hello world 123")
        >>> with stream.syntax(word=r"[a-z]+"):
        ...     with stream.syntax(number=r"[0-9]+", word=None):
        ...         stream.expect("word").value
        Traceback (most recent call last):
        UnexpectedToken: Expected word but got invalid 'hello world 123'.
        """
        previous_syntax = self.syntax_rules
        previous_regex = self.regex

        for key, value in previous_syntax:
            kwargs.setdefault(key, value)

        self.syntax_rules = tuple(
            (key, value) for key, value in kwargs.items() if value
        )

        self.bake_regex()
        self.crop()

        try:
            yield
        finally:
            self.syntax_rules = previous_syntax
            self.regex = previous_regex
            self.crop()

    @contextmanager
    def reset_syntax(self, **kwargs: str) -> Iterator[None]:
        """Overwrite the existing syntax rules.

        This method lets you temporarily overwrite the existing rules instead
        of extending them.

        >>> stream = TokenStream("hello world 123")
        >>> with stream.syntax(word=r"[a-z]+"):
        ...     with stream.reset_syntax(number=r"[0-9]+"):
        ...         stream.expect("word").value
        ...         stream.expect("word").value
        ...         stream.expect("number").value
        Traceback (most recent call last):
        UnexpectedToken: Expected word but got invalid 'hello world 123'.
        """
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
        skip: Iterable[str] | None = None,
    ) -> Iterator[None]:
        r"""Enable or disable indentation.

        When indentation is enabled the token stream will track the current indentation
        level and emit ``indent`` and ``dedent`` tokens when the indentation level changes.
        The ``indent`` and ``dedent`` tokens are always balanced, every ``indent`` token
        will be ultimately paired with a ``dedent`` token.

        >>> stream = TokenStream("hello\n\tworld")
        >>> with stream.syntax(word=r"[a-z]+"), stream.indent():
        ...     stream.expect("word").value
        ...     stream.expect("indent").value
        ...     stream.expect("word").value
        ...     stream.expect("dedent").value
        'hello'
        ''
        'world'
        ''

        The ``skip`` argument allows you to prevent some types of tokens from triggering
        indentation changes. The most common use-case would be ignoring indentation
        introduced by comments.

        .. code-block::

            with stream.syntax(word=r"[a-z]+", comment=r"#.+$"), stream.indent(skip=["comment"]):
                stream.expect("word")
                stream.expect("indent")
                stream.expect("word")
                stream.expect("dedent")

        You can also use the :meth:`indent` method to temporarily disable indentation
        by specifying ``enable=False``. This is different from simply ignoring
        ``indent`` and ``dedent`` tokens with the :meth:`ignore` method because
        it clears the indentation stack and if you decide to re-enable indentation
        afterwards the indentation level will start back at 0.

        .. code-block::

            with stream.indent(enable=False):
                ...
        """
        previous_indentation = self.indentation
        self.indentation = [0] if enable else []

        previous_skip = self.indentation_skip
        self.indentation_skip = set(skip if skip is not None else []) | {"newline"}

        self.crop()

        try:
            yield
        finally:
            self.indentation = previous_indentation
            self.indentation_skip = previous_skip

    @contextmanager
    def intercept(self, *token_types: str) -> Iterator[None]:
        r"""Intercept tokens matching the given types.

        This tells the stream to not skip over previously ignored tokens
        or tokens ignored by default like ``newline`` and ``whitespace``.

        >>> stream = TokenStream("hello world\n")
        >>> with stream.syntax(word=r"[a-z]+"), stream.intercept("newline", "whitespace"):
        ...     stream.expect("word").value
        ...     stream.expect("whitespace").value
        ...     stream.expect("word").value
        ...     stream.expect("newline").value
        'hello'
        ' '
        'world'
        '\n'

        You can use the :meth:`ignore` method to ignore previously intercepted tokens.
        """
        previous_ignored = self.ignored_tokens
        self.ignored_tokens = self.ignored_tokens - set(token_types)

        try:
            yield
        finally:
            self.ignored_tokens = previous_ignored

    @contextmanager
    def ignore(self, *token_types: str) -> Iterator[None]:
        """Ignore tokens matching the given types.

        This tells the stream to skip over tokens matching any of the given types.

        >>> stream = TokenStream("hello 123 world")
        >>> with stream.syntax(word=r"[a-z]+", number=r"[0-9]+"), stream.ignore("number"):
        ...     stream.expect("word").value
        ...     stream.expect("word").value
        'hello'
        'world'

        You can use the :meth:`intercept` method to stop ignoring tokens.
        """
        previous_ignored = self.ignored_tokens
        self.ignored_tokens = self.ignored_tokens | set(token_types)

        try:
            yield
        finally:
            self.ignored_tokens = previous_ignored

    @property
    def current(self) -> Token:
        """The current token.

        Can only be accessed if the stream started extracting tokens.
        """
        if self.index < 0:
            raise IndexError("Token index out of range.")
        return self.tokens[self.index]

    @property
    def previous(self) -> Token:
        """The previous token.

        This is the token extracted immediately before the current one, so
        it's not affected by the :meth:`ignore` method.
        """
        if self.index <= 0:
            raise IndexError("Token index out of range.")
        return self.tokens[self.index - 1]

    @property
    def leftover(self) -> str:
        """The remaining input.

        >>> stream = TokenStream("hello world")
        >>> with stream.syntax(word=r"[a-z]+"):
        ...     stream.expect("word").value
        ...     stream.leftover
        'hello'
        ' world'
        """
        pos = self.current.end_location.pos if self.index >= 0 else 0
        return self.source[pos:]

    def head(self, characters: int = 50) -> str:
        """Preview the characters ahead of the current token.

        This is useful for error messages and visualizing the
        input following the current token.

        >>> stream = TokenStream("hello world")
        >>> with stream.syntax(word=r"[a-z]+"):
        ...     stream.expect("word").value
        ...     stream.head()
        'hello'
        ' world'

        The generated string is truncated to 50 characters by default but you
        can change this with the ``characters`` argument.
        """
        pos = self.current.end_location.pos if self.index >= 0 else 0
        value = self.source[pos : pos + characters]
        return value.partition("\n")[0]

    def emit_token(self, token_type: str, value: str = "") -> Token:
        """Generate a token in the token stream.

        Should be considered internal. Used by the :meth:`generate_tokens` method.
        """
        location = SourceLocation(
            self.preprocessed_pos,
            self.preprocessed_lineno,
            self.preprocessed_colno,
        )

        end_location = location.skip_over(value)

        (
            self.preprocessed_pos,
            self.preprocessed_lineno,
            self.preprocessed_colno,
        ) = end_location

        token = Token(
            type=token_type,
            value=value,
            location=location.map(self.preprocessed_mappings, self.source_mappings),
            end_location=end_location.map(
                self.preprocessed_mappings, self.source_mappings
            ),
        )

        self.preprocessed_locations.append(end_location)
        self.tokens.append(token)

        self.index = len(self.tokens) - 1

        return token

    def emit_error(self, exc: T) -> T:
        """Add location information to invalid syntax exceptions.

        >>> stream = TokenStream("hello world")
        >>> raise stream.emit_error(InvalidSyntax("foo"))
        Traceback (most recent call last):
        InvalidSyntax: foo
        >>> with stream.syntax(word=r"[a-z]+"):
        ...     stream.expect().value
        'hello'
        >>> exc = stream.emit_error(InvalidSyntax("foo"))
        >>> exc.location
        SourceLocation(pos=5, lineno=1, colno=6)
        """
        return set_location(
            exc,
            self.current.end_location if self.index >= 0 else INITIAL_LOCATION,
        )

    def generate_tokens(self) -> Iterator[Token]:
        """Extract tokens from the input string.

        Should be considered internal. This is the underlying generator being driven
        by the stream.
        """

        def emit_dedent(level: int = 0) -> Iterator[Token]:
            while self.indentation and level < self.indentation[-1]:
                self.emit_token("dedent")
                self.indentation.pop()
                yield self.current

        while self.preprocessed_pos < len(self.preprocessed_source):
            match = self.regex.match(self.preprocessed_source, self.preprocessed_pos)

            assert match
            assert match.lastgroup

            if self.tokens and self.indentation:
                if (
                    self.current.type == "whitespace"
                    and self.current.location.colno == 1
                    and match.lastgroup not in self.indentation_skip
                ):
                    level = len(self.current.value.expandtabs())
                    yield from emit_dedent(level)

                    if level > self.indentation[-1]:
                        self.emit_token("indent")
                        self.indentation.append(level)
                        yield self.current

                elif self.current.type == "newline" and match.lastgroup not in [
                    "whitespace",
                    "newline",
                ]:
                    yield from emit_dedent()

            self.emit_token(match.lastgroup, match.group())
            yield self.current

        yield from emit_dedent()

        self.emit_token("eof")
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

    def peek(self, n: int = 1) -> Token | None:
        """Peek around the current token.

        The method returns the next token in the stream without advancing
        the stream to the next token.

        >>> stream = TokenStream("hello world")
        >>> with stream.syntax(word=r"[a-z]+"):
        ...     stream.peek().value
        ...     stream.expect("word").value
        'hello'
        'hello'

        You can also peek multiple tokens ahead.

        >>> stream = TokenStream("hello world")
        >>> with stream.syntax(word=r"[a-z]+"):
        ...     stream.peek(2).value
        ...     stream.expect("word").value
        'world'
        'hello'

        Negative values will let you peek backwards. It's generally better to use
        ``peek(-1)`` over the :attr:`previous` attribute because the :meth:`peek`
        method will take ignored tokens into account.

        >>> stream = TokenStream("hello world")
        >>> with stream.syntax(word=r"[a-z]+"):
        ...     stream.expect("word").value
        ...     stream.expect("word").value
        ...     stream.peek(-1).value
        'hello'
        'world'
        'hello'
        >>> stream.previous.value
        ' '
        """
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
        """Collect tokens until one of the given patterns matches.

        >>> stream = TokenStream("hello world; foo")
        >>> with stream.syntax(word=r"[a-z]+", semi=r";"):
        ...     for token in stream.peek_until("semi"):
        ...         stream.expect("word").value
        ...     stream.current.value
        ...     stream.leftover
        'hello'
        'world'
        ';'
        ' foo'

        The method will raise and error if the end of the stream is reached
        before encountering any of the given patterns.

        >>> stream = TokenStream("hello world foo")
        >>> with stream.syntax(word=r"[a-z]+", semi=r";"):
        ...     for token in stream.peek_until("semi"):
        ...         stream.expect("word").value
        Traceback (most recent call last):
        UnexpectedEOF: Expected semi but reached end of file.

        If the method is called without any pattern the iterator will
        yield tokens until the end of the stream.

        >>> stream = TokenStream("hello world")
        >>> with stream.syntax(word=r"[a-z]+"):
        ...     print([stream.expect("word").value for _ in stream.peek_until()])
        ['hello', 'world']
        """
        while token := self.peek():
            if token.match(*patterns):
                next(self)
                return
            yield token
        if patterns:
            raise self.emit_error(UnexpectedEOF(patterns))

    @overload
    def collect(self) -> Iterator[Token]:
        ...

    @overload
    def collect(self, pattern: TokenPattern, /) -> Iterator[Token]:
        ...

    @overload
    def collect(
        self,
        pattern1: TokenPattern,
        pattern2: TokenPattern,
        /,
        *patterns: TokenPattern,
    ) -> Iterator[list[Token | None]]:
        ...

    def collect(self, *patterns: TokenPattern) -> Iterator[Any]:
        """Collect tokens matching the given patterns.

        Calling the method without any arguments is similar to iterating over the
        stream directly. If you provide one or more arguments the iterator
        will stop if it encounters a token that doesn't match any of the given
        patterns.

        >>> stream = TokenStream("hello world; foo")
        >>> with stream.syntax(word=r"[a-z]+", semi=r";"):
        ...     for token in stream.collect("word"):
        ...         token.value
        ...     stream.leftover
        'hello'
        'world'
        '; foo'

        If you provide more than one pattern the method will yield a sequence
        of the same size where the token will be at the index of the pattern
        that matched the token.

        >>> stream = TokenStream("hello world 123")
        >>> with stream.syntax(word=r"[a-z]+", number=r"[0-9]+"):
        ...     for word, number in stream.collect("word", "number"):
        ...         if word:
        ...             print("word", word.value)
        ...         elif number:
        ...             print("number", number.value)
        word hello
        word world
        number 123

        There is one small difference between iterating over the stream directly and
        using the method without any argument. The :meth:`collect` method will raise
        an exception if it encounters an invalid token.

        >>> stream = TokenStream("foo")
        >>> with stream.syntax(number=r"[0-9]+"):
        ...     for token in stream.collect():
        ...         token
        Traceback (most recent call last):
        UnexpectedToken: Expected anything but got invalid 'foo'.

        When you iterate over the stream directly the tokens are unfiltered.

        >>> stream = TokenStream("foo")
        >>> with stream.syntax(number=r"[0-9]+"):
        ...     for token in stream:
        ...         token
        Token(type='invalid', value='foo', ...)

        """
        if not patterns:
            for token in self:
                if token.match("invalid"):
                    raise UnexpectedToken(token, patterns)
                yield token
            return

        while token := self.peek():
            matches = [token if token.match(pattern) else None for pattern in patterns]

            if not any(matches):
                break

            next(self)

            if len(matches) == 1:
                yield matches[0]
            else:
                yield matches

    def collect_any(self, *patterns: TokenPattern) -> Iterator[Token]:
        """Collect tokens matching one of the given patterns.

        The method is similar to :meth:`collect` but will always return
        a single value. This works pretty nicely with Python 3.10+ match statements.

        .. code-block::

            for token in stream.collect_any("word", "number"):
                match token:
                    case Token(type="word"):
                        print("word", token.value)
                    case Token(type="number"):
                        print("number", token.value)
        """
        if not patterns:
            yield from self.collect()
        elif len(patterns) == 1:
            yield from self.collect(patterns[0])
        else:
            for matches in self.collect(patterns[0], patterns[1], *patterns[2:]):
                yield next(filter(None, matches))

    @overload
    def expect(self) -> Token:
        ...

    @overload
    def expect(self, pattern: TokenPattern, /) -> Token:
        ...

    @overload
    def expect(
        self,
        pattern1: TokenPattern,
        pattern2: TokenPattern,
        /,
        *patterns: TokenPattern,
    ) -> list[Token | None]:
        ...

    def expect(self, *patterns: TokenPattern) -> Any:
        """Match the given patterns and raise an exception if the next token doesn't match.

        The :meth:`expect` method lets you retrieve tokens one at a time.

        >>> stream = TokenStream("hello world 123")
        >>> with stream.syntax(word=r"[a-z]+", number=r"[0-9]+"):
        ...     stream.expect().value
        ...     stream.expect().value
        ...     stream.expect().value
        'hello'
        'world'
        '123'

        You can provide a pattern and if the extracted token doesn't match the method will
        raise an exception.

        >>> stream = TokenStream("hello world 123")
        >>> with stream.syntax(word=r"[a-z]+", number=r"[0-9]+"):
        ...     stream.expect("number").value
        Traceback (most recent call last):
        UnexpectedToken: Expected number but got word 'hello'.

        The method will also raise and exception if the stream ended.

        >>> stream = TokenStream("hello world")
        >>> with stream.syntax(word=r"[a-z]+"):
        ...     stream.expect("word").value
        ...     stream.expect("word").value
        ...     stream.expect("word").value
        Traceback (most recent call last):
        UnexpectedEOF: Expected word but reached end of file.

        The method works a bit like :meth:`collect` and lets you know which pattern
        matched the extracted token if you provide more than one pattern.

        >>> stream = TokenStream("hello world 123")
        >>> with stream.syntax(word=r"[a-z]+", number=r"[0-9]+"):
        ...     word, number = stream.expect("word", "number")
        ...     if word:
        ...         print("word", word.value)
        ...     elif number:
        ...         print("number", number.value)
        word hello
        """
        for result in self.collect(*patterns):
            return result

        if token := self.peek():
            raise set_location(self.emit_error(UnexpectedToken(token, patterns)), token)
        else:
            raise self.emit_error(UnexpectedEOF(patterns))

    def get(self, *patterns: TokenPattern) -> Token | None:
        """Return the next token if it matches any of the given patterns.

        The method works a bit like :meth:`expect` but will return ``None``
        instead of raising an exception if none of the given patterns match.
        If there are no more tokens the method will also return ``None``.

        >>> stream = TokenStream("hello world 123")
        >>> with stream.syntax(word=r"[a-z]+", number=r"[0-9]+"):
        ...     stream.get("word").value
        ...     stream.get("number") is None
        ...     stream.get("word").value
        ...     stream.get("number").value
        ...     stream.get() is None
        'hello'
        True
        'world'
        '123'
        True
        """
        for result in self.collect(*patterns):
            return result if isinstance(result, Token) else next(filter(None, result))  # type: ignore
        return None

    def expect_any(self, *patterns: TokenPattern) -> Token:
        """Make sure that the next token matches one of the given patterns or raise an exception.

        The method is similar to :meth:`expect` but will always return
        a single value. This works pretty nicely with Python 3.10+ match statements.

        .. code-block::

            match stream.expect_any("word", "number"):
                case Token(type="word") as word:
                    print("word", word.value)
                case Token(type="number") as number:
                    print("number", number.value)
        """
        if not patterns:
            return self.expect()
        elif len(patterns) == 1:
            return self.expect(patterns[0])
        else:
            matches = self.expect(patterns[0], patterns[1], *patterns[2:])
            return next(filter(None, matches))

    def expect_eof(self) -> None:
        """Raise an exception if there is leftover input.

        >>> stream = TokenStream("hello world 123 foo")
        >>> with stream.syntax(word=r"[a-z]+", number=r"[0-9]+"):
        ...     for token in stream.collect("word"):
        ...         token.value
        ...     stream.expect("number").value
        'hello'
        'world'
        '123'
        >>> stream.expect_eof()
        Traceback (most recent call last):
        UnexpectedToken: Expected eof but got invalid 'foo'.
        """
        with self.intercept("eof"):
            for _ in self.collect("eof"):
                return

        if token := self.peek():
            raise set_location(self.emit_error(UnexpectedToken(token, ("eof",))), token)

    @contextmanager
    def checkpoint(self) -> Iterator[CheckpointCommit]:
        """Reset the stream to the current token at the end of the ``with`` statement.

        >>> stream = TokenStream("hello world")
        >>> with stream.syntax(word=r"[a-z]+"):
        ...     with stream.checkpoint():
        ...         stream.expect("word").value
        ...     stream.expect("word").value
        'hello'
        'hello'

        You can use the returned handle to keep the state of the stream
        at the end of the ``with`` statement. For more details check out
        :class:`CheckpointCommit`.

        >>> stream = TokenStream("hello world")
        >>> with stream.syntax(word=r"[a-z]+"):
        ...     with stream.checkpoint() as commit:
        ...         stream.expect("word").value
        ...         commit()
        ...     stream.expect("word").value
        'hello'
        'world'

        The context manager will swallow syntax errors until the handle
        commits the checkpoint.
        """
        commit = CheckpointCommit(self.index)

        try:
            yield commit
        except InvalidSyntax:
            if not commit.rollback:
                raise
        finally:
            if commit.rollback:
                self.index = commit.index

    @contextmanager
    def alternative(self, active: bool = True) -> Iterator[None]:
        """Keep going if the code within the ``with`` statement raises a syntax error.

        >>> stream = TokenStream("hello world 123")
        >>> with stream.syntax(word=r"[a-z]+", number=r"[0-9]+"):
        ...     stream.expect("word").value
        ...     stream.expect("word").value
        ...     with stream.alternative():
        ...         stream.expect("word").value
        ...     stream.expect("number").value
        'hello'
        'world'
        '123'

        You can optionally provide a boolean to deactivate the context manager
        dynamically.

        >>> stream = TokenStream("hello world 123")
        >>> with stream.syntax(word=r"[a-z]+", number=r"[0-9]+"):
        ...     with stream.alternative(False):
        ...         stream.expect("number").value
        Traceback (most recent call last):
        UnexpectedToken: Expected number but got word 'hello'.
        """
        if not active:
            yield
            return
        with self.checkpoint() as commit:
            yield
            commit()

    def choose(self, *args: T) -> Iterator[tuple[T, ContextManager[None]]]:
        """Iterate over each argument until one of the alternative succeeds.

        >>> stream = TokenStream("hello world 123")
        >>> with stream.syntax(word=r"[a-z]+", number=r"[0-9]+"):
        ...     while stream.peek():
        ...         for token_type, alternative in stream.choose("word", "number"):
        ...             with alternative:
        ...                 stream.expect(token_type).value
        'hello'
        'world'
        '123'
        """
        should_break = False
        exception: InvalidSyntax | None = None

        @contextmanager
        def alternative(active: bool):
            with self.alternative(active):
                nonlocal should_break, exception

                try:
                    yield
                    should_break = True

                except InvalidSyntax as exc:
                    if exception:
                        exception.add_alternative(exc)
                        if exc.location > exception.location:
                            exception = exc
                    else:
                        exception = exc
                    raise exception from None

        for i, arg in enumerate(args):
            yield arg, alternative(i < len(args) - 1)
            if should_break:
                break

    @contextmanager
    def provide(self, **data: Any):
        """Provide arbitrary user data.

        >>> stream = TokenStream("hello world")
        >>> with stream.provide(foo=123):
        ...     stream.data["foo"]
        123
        """
        to_restore: dict[str, Any] = {}
        to_remove: set[str] = set()

        for key, value in data.items():
            if key in self.data:
                to_restore[key] = self.data[key]
            else:
                to_remove.add(key)
            self.data[key] = value

        try:
            yield self
        finally:
            for key in to_remove:
                del self.data[key]
            self.data.update(to_restore)

    @contextmanager
    def reset(self, *args: str):
        """Temporarily reset arbitrary user data.

        >>> stream = TokenStream("hello world")
        >>> with stream.provide(foo=123):
        ...     stream.data["foo"]
        ...     with stream.reset("foo"):
        ...         stream.data
        ...     stream.data
        123
        {}
        {'foo': 123}
        """
        to_restore: dict[str, Any] = {}

        for key in args:
            if key in self.data:
                to_restore[key] = self.data[key]
                del self.data[key]

        try:
            yield self
        finally:
            self.data.update(to_restore)

    def copy(self) -> "TokenStream":
        """Return a copy of the stream.

        >>> stream = TokenStream("hello world")
        >>> with stream.syntax(word=r"[a-z]+"):
        ...     stream.expect("word").value
        ...     stream_copy = stream.copy()
        ...     stream.expect("word").value
        'hello'
        'world'
        >>> with stream_copy.syntax(letter=r"[a-z]"):
        ...     [token.value for token in stream_copy]
        ['w', 'o', 'r', 'l', 'd']
        """
        copy = TokenStream(self.source, regex_module=self.regex_module)

        copy.syntax_rules = self.syntax_rules
        copy.regex = self.regex

        copy.preprocessor = self.preprocessor
        copy.preprocessed_source = self.preprocessed_source
        copy.source_mappings = self.source_mappings
        copy.preprocessed_mappings = self.preprocessed_mappings

        copy.preprocessed_pos = self.preprocessed_pos
        copy.preprocessed_lineno = self.preprocessed_lineno
        copy.preprocessed_colno = self.preprocessed_colno
        copy.preprocessed_locations = list(self.preprocessed_locations)

        copy.index = self.index
        copy.tokens = list(self.tokens)
        copy.indentation = list(self.indentation)
        copy.indentation_skip = set(self.indentation_skip)

        copy.ignored_tokens = set(self.ignored_tokens)

        copy.data = dict(self.data)

        return copy
