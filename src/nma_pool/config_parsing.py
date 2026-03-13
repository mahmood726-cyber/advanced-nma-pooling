"""Shared helpers for strict config coercion."""

from __future__ import annotations

import math
from typing import Any


_TRUE_STRINGS = {"1", "true", "t", "yes", "y", "on"}
_FALSE_STRINGS = {"0", "false", "f", "no", "n", "off"}


def parse_bool_value(raw: Any, *, field_name: str) -> bool:
    """Parse a user-provided boolean without Python truthiness surprises."""

    if isinstance(raw, bool):
        return raw
    if isinstance(raw, int) and raw in {0, 1}:
        return bool(raw)
    if isinstance(raw, float) and math.isfinite(raw) and raw in {0.0, 1.0}:
        return bool(int(raw))
    if isinstance(raw, str):
        value = raw.strip().lower()
        if value in _TRUE_STRINGS:
            return True
        if value in _FALSE_STRINGS:
            return False
    raise ValueError(
        f"{field_name} must be a boolean or one of: "
        "true/false, yes/no, on/off, 1/0."
    )
