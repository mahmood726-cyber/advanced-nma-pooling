from __future__ import annotations

import pytest

from nma_pool.config_parsing import parse_bool_value


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (True, True),
        (False, False),
        (1, True),
        (0, False),
        (1.0, True),
        (0.0, False),
        ("true", True),
        ("FALSE", False),
        (" yes ", True),
        ("0", False),
        ("on", True),
        ("off", False),
    ],
)
def test_parse_bool_value_accepts_supported_representations(raw: object, expected: bool) -> None:
    assert parse_bool_value(raw, field_name="flag") is expected


@pytest.mark.parametrize("raw", [2, -1, 0.5, "maybe", "", None])
def test_parse_bool_value_rejects_ambiguous_values(raw: object) -> None:
    with pytest.raises(ValueError, match="flag must be a boolean"):
        parse_bool_value(raw, field_name="flag")
