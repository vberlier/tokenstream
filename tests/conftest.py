from typing import Any

import pytest

import tokenstream


@pytest.fixture(autouse=True)
def add_tokenstream(doctest_namespace: dict[str, Any]):
    doctest_namespace.update(
        (name, getattr(tokenstream, name)) for name in tokenstream.__all__
    )
