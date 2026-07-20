"""Small service helpers for Adobe array and coordinate wrappers."""

from __future__ import annotations

from typing import Any, Iterator, List


def iter_api_array(value: Any) -> Iterator[Any]:
    """Iterate SDArray or a strict offline fake without exposing it."""

    if value is None:
        return
    if hasattr(value, "getSize") and hasattr(value, "getItem"):
        for index in range(int(value.getSize())):
            yield value.getItem(index)
        return
    yield from value


def position_to_list(value: Any) -> List[float]:
    """Serialize Adobe float2 or a test tuple."""

    if hasattr(value, "x") and hasattr(value, "y"):
        return [float(value.x), float(value.y)]
    return [float(value[0]), float(value[1])]
