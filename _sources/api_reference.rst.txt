API reference
=============

The API surface is intentionally minimal. The package provides a simple token class, a couple exceptions, and the main ``TokenStream`` abstraction. There are no third-party dependencies.

TokenStream
-----------

.. autoclass:: tokenstream.stream.TokenStream
    :members:

.. autoclass:: tokenstream.stream.CheckpointCommit
    :members:

Token
-----

.. autoclass:: tokenstream.token.Token
    :members:

Location
--------

.. autoclass:: tokenstream.location.SourceLocation
    :members:

.. autofunction:: tokenstream.location.set_location

Exceptions
----------

.. autoclass:: tokenstream.error.InvalidSyntax
    :show-inheritance:
    :members:

.. autoclass:: tokenstream.error.UnexpectedEOF
    :show-inheritance:
    :members:

.. autoclass:: tokenstream.error.UnexpectedToken
    :show-inheritance:
    :members:
