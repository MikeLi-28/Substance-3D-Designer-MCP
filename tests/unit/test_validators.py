from __future__ import annotations

import math

import pytest
from substance_designer_mcp_plugin.commands.validators import (
    require_keys,
    validate_node_identifiers,
    validate_position,
)
from substance_designer_mcp_plugin.errors import ErrorCode, PluginError


def test_require_keys_rejects_missing_and_unknown_arguments() -> None:
    with pytest.raises(PluginError) as missing:
        require_keys({}, required={"graph"}, optional={"detail"})
    with pytest.raises(PluginError) as unknown:
        require_keys({"graph": {}, "surprise": True}, required={"graph"}, optional=set())

    assert missing.value.code is ErrorCode.INVALID_PARAMETER
    assert unknown.value.code is ErrorCode.INVALID_PARAMETER


@pytest.mark.parametrize("value", [[1.0], [1.0, 2.0, 3.0], [math.inf, 2.0], ["x", 2.0]])
def test_validate_position_rejects_invalid_coordinates(value: object) -> None:
    with pytest.raises(PluginError) as caught:
        validate_position(value)

    assert caught.value.code is ErrorCode.INVALID_PARAMETER


def test_validate_position_normalizes_finite_numbers() -> None:
    assert validate_position([1, 2.5]) == [1.0, 2.5]


@pytest.mark.parametrize("value", [[], ["node"] * 101, ["node", ""], "node"])
def test_validate_node_identifiers_rejects_empty_oversized_or_invalid_lists(value: object) -> None:
    with pytest.raises(PluginError):
        validate_node_identifiers(value)
