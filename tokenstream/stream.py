__all__ = [
    "TokenStream",
    "SyntaxRules",
    "CheckpointCommit",
]

import re
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import (
    Any,
    Callable,
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
CheckpointCommit = Callable[[], None]


def extra_field(**kwargs: Any) -> Any:
    return field(repr=False, init=False, hash=False, compare=False, **kwargs)


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
        (?P<word>[a-z]+)|(?P<newline>\n)|(?P<whitespace>\s+)

    location
        Tracks the position of the next token to extract in the input string.

        Generally you'll probably want to use ``stream.current.location`` instead
        because the :attr:`location` attribute doesn't roll back with checkpoints
        and when the stream resets to a previous token.

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

    regex_cache
        A cache that keeps a reference to the compiled regular expression associated
        to each set of syntax rules.
    """

    source: str
    syntax_rules: SyntaxRules = extra_field(default=())
    regex: "re.Pattern[str]" = extra_field()

    location: SourceLocation = extra_field()

    index: int = extra_field(default=-1)
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
        """Compile the syntax rules.

        Called automatically upon instanciation and when the syntax rules change.
        Should be considered internal.
        """
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
        if self.index + 1 < len(self.tokens):
            self.tokens = self.tokens[: self.index + 1]
        if self.index >= 0:
            self.location = self.current.end_location

    @contextmanager
    def syntax(self, **kwargs: str) -> Iterator[None]:
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
        """
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
        InvalidSyntax: hello world 123
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
        skip: Optional[Iterable[str]] = None,
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
        return self.tokens[self.index]

    @property
    def previous(self) -> Token:
        """The previous token.

        This is the token extracted immediately before the current one, so
        it's not affected by the :meth:`ignore` method.
        """
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

        This is useful for error messages and visuallizing the
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
        end_pos = self.location.pos + len(value)
        end_lineno = self.location.lineno + value.count("\n")

        if (line_start := value.rfind("\n")) == -1:
            end_colno = self.location.colno + len(value)
        else:
            end_colno = len(value) - line_start

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
        """Raise an invalid syntax exception.

        Should be considered internal. Used by various methods to add
        location information to exceptions.
        """
        if self.index >= 0:
            exc.location = self.current.end_location
        else:
            exc.location = SourceLocation(pos=0, lineno=1, colno=1)
        return exc

    def generate_tokens(self) -> Iterator[Token]:
        """Extract tokens from the input string.

        Should be considered internal. This is the underlying generator being driven
        by the stream.
        """
        while self.location.pos < len(self.source):
            if match := self.regex.match(self.source, self.location.pos):
                assert match.lastgroup

                if (
                    self.tokens
                    and self.indentation
                    and self.current.type == "whitespace"
                    and self.current.location.colno == 1
                    and match.lastgroup not in self.indentation_skip
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
        """
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
        """Collect tokens matching the given patterns.

        Calling the method without any arguments is identical to iterating over the
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
        """
        if not patterns:
            yield from self
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
        while token := self.peek():
            if not token.match(*patterns):
                break
            yield next(self)

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
        UnexpectedToken: Expected number but got word 'hello'

        The method will also raise and exception if the stream ended.

        >>> stream = TokenStream("hello world")
        >>> with stream.syntax(word=r"[a-z]+"):
        ...     stream.expect("word").value
        ...     stream.expect("word").value
        ...     stream.expect("word").value
        Traceback (most recent call last):
        UnexpectedEOF: Expected word but reached end of file

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
            raise self.emit_error(UnexpectedToken(token, patterns))
        else:
            raise self.emit_error(UnexpectedEOF(patterns))

    def get(self, *patterns: TokenPattern) -> Optional[Token]:
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
        if token := self.peek():
            if token.match(*patterns):
                return next(self)
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
        if token := self.peek():
            if token.match(*patterns):
                return next(self)
            else:
                raise self.emit_error(UnexpectedToken(token, patterns))
        else:
            raise self.emit_error(UnexpectedEOF(patterns))

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
        InvalidSyntax: foo
        """
        if self.peek():
            raise self.emit_error(InvalidSyntax(self.head()))

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

        You can use the returned ``commit()`` function to keep the state of the stream at the end of the ``with`` statement.

        >>> stream = TokenStream("hello world")
        >>> with stream.syntax(word=r"[a-z]+"):
        ...     with stream.checkpoint() as commit:
        ...         stream.expect("word").value
        ...         commit()
        ...     stream.expect("word").value
        'hello'
        'world'
        """
        previous_index = [self.index]

        try:
            yield lambda: previous_index.clear()
        finally:
            if previous_index:
                self.index = previous_index[0]