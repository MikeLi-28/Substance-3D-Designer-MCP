from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.manual.sd16_e2e_support import (
    HarnessError,
    aggregate_reports,
    assert_no_existing_designer,
    choose_connection,
    choose_parameter,
    make_check,
    redact,
)


def test_process_guard_rejects_any_designer_process() -> None:
    with pytest.raises(HarnessError, match="already running"):
        assert_no_existing_designer(["Adobe Substance 3D Designer"])

    assert_no_existing_designer(["python", "explorer"])


def test_redact_removes_token_secret_and_workspace_path() -> None:
    value = {
        "token": "secret",
        "nested": [{"message": "secret in C:/e2e/package.sbs"}],
    }

    cleaned = redact(value, secrets={"secret"}, workspace="C:/e2e")
    encoded = json.dumps(cleaned)

    assert "secret" not in encoded
    assert "C:/e2e" not in encoded
    assert "<redacted>" in encoded
    assert "<workspace>" in encoded


@pytest.mark.parametrize(
    ("type_id", "current", "expected"),
    [
        ("bool", True, False),
        ("int", 3, 4),
        ("float", 1.0, 1.125),
        ("double", 2.0, 2.125),
        ("string", "name", "name_mcp"),
        ("float2", [0.0, 1.0], [0.125, 1.125]),
        ("float3", [0.0, 1.0, 2.0], [0.125, 1.125, 2.125]),
        ("float4", [0.0, 1.0, 2.0, 3.0], [0.125, 1.125, 2.125, 3.125]),
        ("colorrgba", [0.9, 0.2, 0.3, 1.0], [1.0, 0.325, 0.425, 1.0]),
    ],
)
def test_choose_parameter_returns_supported_writable_input(
    type_id: str, current: object, expected: object
) -> None:
    selected = choose_parameter(
        [
            {
                "direction": "input",
                "read_only": True,
                "type_id": "float",
                "value": {"value": 1.0},
            },
            {
                "direction": "input",
                "read_only": False,
                "connected": False,
                "type_id": type_id,
                "property_id": "candidate",
                "value": {"value": current},
            },
        ]
    )

    assert selected == {
        "property_id": "candidate",
        "valid_value": expected,
        "invalid_value": {"invalid": True},
    }


def test_choose_parameter_fails_closed_for_unsupported_inputs() -> None:
    with pytest.raises(HarnessError, match="supported writable"):
        choose_parameter(
            [
                {
                    "direction": "input",
                    "read_only": False,
                    "connected": False,
                    "type_id": "gradient",
                    "property_id": "gradient",
                    "value": {"value": []},
                }
            ]
        )


def test_choose_connection_intersects_runtime_types() -> None:
    pair = choose_connection(
        [
            {
                "direction": "output",
                "connectable": True,
                "type_id": "texture",
                "property_id": "out",
            }
        ],
        [
            {
                "direction": "input",
                "connectable": True,
                "connected": False,
                "type_id": "texture",
                "property_id": "in",
            }
        ],
    )

    assert pair == {"source_property": "out", "target_property": "in"}


def test_choose_connection_rejects_incompatible_runtime_types() -> None:
    with pytest.raises(HarnessError, match="compatible connectable"):
        choose_connection(
            [
                {
                    "direction": "output",
                    "connectable": True,
                    "type_id": "color",
                    "property_id": "out",
                }
            ],
            [
                {
                    "direction": "input",
                    "connectable": True,
                    "connected": False,
                    "type_id": "float",
                    "property_id": "in",
                }
            ],
        )


def test_aggregate_reports_fails_closed_when_evidence_is_missing() -> None:
    result = aggregate_reports(
        [
            {"checks": {"plugin_loaded": make_check(True, "Loaded")}},
            {"checks": {}},
            {"checks": {}},
        ],
        required=("plugin_loaded", "mcp_connected"),
    )

    assert result["status"] == "failed"
    assert result["checks"]["plugin_loaded"]["passed"] is True
    assert result["checks"]["mcp_connected"] == make_check(
        False,
        None,
        {
            "code": "MISSING_EVIDENCE",
            "message": "Required evidence was not produced.",
        },
    )


def test_aggregate_reports_passes_only_when_all_required_checks_pass() -> None:
    result = aggregate_reports(
        [
            {"checks": {"plugin_loaded": make_check(True, "Loaded")}},
            {"checks": {"mcp_connected": make_check(True, {"protocol": "1.0"})}},
        ],
        required=("plugin_loaded", "mcp_connected"),
    )

    assert result["status"] == "passed"


def test_aggregate_cli_writes_redacted_result(tmp_path: Path) -> None:
    report = tmp_path / "phase.json"
    output = tmp_path / "combined.json"
    report.write_text(
        json.dumps(
            {
                "checks": {"plugin_loaded": make_check(True, "Loaded")},
                "token": "top-secret",
            }
        ),
        encoding="utf-8",
    )

    from tests.manual.sd16_e2e_support import main

    result = main(
        [
            "aggregate",
            "--report",
            str(report),
            "--required-check",
            "plugin_loaded",
            "--workspace",
            str(tmp_path),
            "--output",
            str(output),
        ]
    )

    encoded = output.read_text(encoding="utf-8")
    assert result == 0
    assert "top-secret" not in encoded
    assert "<redacted>" in encoded


def test_aggregate_cli_accepts_windows_utf8_bom(tmp_path: Path) -> None:
    report = tmp_path / "phase.json"
    output = tmp_path / "combined.json"
    report.write_text(
        json.dumps({"checks": {"plugin_loaded": make_check(True, "Loaded")}}),
        encoding="utf-8-sig",
    )

    from tests.manual.sd16_e2e_support import main

    result = main(
        [
            "aggregate",
            "--report",
            str(report),
            "--required-check",
            "plugin_loaded",
            "--output",
            str(output),
        ]
    )

    assert result == 0
