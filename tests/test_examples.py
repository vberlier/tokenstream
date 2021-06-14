import json

import pytest

from examples.calculator import calculate_sum
from examples.json import parse_json
from tokenstream import TokenStream


@pytest.mark.parametrize(
    "source",
    [
        "123",
        "1 + 2 + 3",
        "1 * 2 * 3",
        "1 + 2 * 3",
        "1 * 2 + 3",
        "1 + 2 - 3 * 4 / 5",
        "(1 + 2 - 3) * 4 / 5",
        "1 + (2 - 3) * 4 / 5",
        "((1) + (2 - (3)) * 4 / 5)",
    ],
)
def test_calculator(source: str):
    assert calculate_sum(TokenStream(source)) == eval(source)


@pytest.mark.parametrize(
    "source",
    [
        r'{"hello": "world"}',
        r'{"hello": [1, 2, 3, "thing"]}',
        r'{"hello": [1, 2, 3, "thing"], "other": {}}',
        r"123",
        r"{}",
        r"[]",
        r'"foo"',
    ],
)
def test_json(source: str):
    assert parse_json(TokenStream(source)) == json.loads(source)
