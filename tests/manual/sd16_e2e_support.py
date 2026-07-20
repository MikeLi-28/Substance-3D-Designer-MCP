"""Dependency-free helpers for isolated Designer 16 real-machine verification."""

from __future__ import annotations

import argparse
import json
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any, Optional


class HarnessError(RuntimeError):
    """Raised when the harness cannot proceed without guessing."""


def make_check(passed: bool, evidence: object, error: object = None) -> dict[str, object]:
    result: dict[str, object] = {"passed": bool(passed), "evidence": evidence}
    if error is not None:
        result["error"] = error
    return result


def assert_no_existing_designer(process_names: list[str]) -> None:
    if any("substance 3d designer" in name.casefold() for name in process_names):
        raise HarnessError("Adobe Substance 3D Designer is already running.")


def redact(value: object, secrets: set[str], workspace: str) -> object:
    if isinstance(value, dict):
        return {
            str(key): (
                "<redacted>" if str(key).casefold() == "token" else redact(item, secrets, workspace)
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact(item, secrets, workspace) for item in value]
    if isinstance(value, tuple):
        return [redact(item, secrets, workspace) for item in value]
    if isinstance(value, str):
        cleaned = value.replace(workspace, "<workspace>") if workspace else value
        for secret in secrets:
            if secret:
                cleaned = cleaned.replace(secret, "<redacted>")
        return cleaned
    return value


def _numeric_sequence(value: object, size: int) -> Optional[list[float]]:
    if not isinstance(value, (list, tuple)) or len(value) != size:
        return None
    if any(isinstance(item, bool) or not isinstance(item, (int, float)) for item in value):
        return None
    return [float(item) for item in value]


def _next_parameter_value(type_id: str, current: object) -> object:
    normalized = type_id.casefold()
    if normalized == "bool" and isinstance(current, bool):
        return not current
    if normalized == "int" and isinstance(current, int) and not isinstance(current, bool):
        return current + 1
    if (
        normalized in {"float", "double"}
        and isinstance(current, (int, float))
        and not isinstance(current, bool)
    ):
        return round(float(current) + 0.125, 6)
    if normalized in {"string", "str"} and isinstance(current, str):
        return current + "_mcp"
    vector_sizes = {"float2": 2, "float3": 3, "float4": 4}
    if normalized in vector_sizes:
        parts = _numeric_sequence(current, vector_sizes[normalized])
        if parts is not None:
            return [round(item + 0.125, 6) for item in parts]
    if normalized in {"color", "colorrgba"}:
        parts = _numeric_sequence(current, 4)
        if parts is not None:
            return [round(min(1.0, max(0.0, item + 0.125)), 6) for item in parts[:3]] + [parts[3]]
    raise HarnessError("No supported writable parameter is available.")


def choose_parameter(properties: Sequence[Mapping[str, object]]) -> dict[str, object]:
    for prop in properties:
        if prop.get("direction") != "input":
            continue
        if prop.get("read_only") is True or prop.get("connected") is True:
            continue
        property_id = prop.get("property_id")
        type_id = prop.get("type_id")
        serialized = prop.get("value")
        if not isinstance(property_id, str) or not isinstance(type_id, str):
            continue
        if not isinstance(serialized, Mapping) or "value" not in serialized:
            continue
        try:
            valid_value = _next_parameter_value(type_id, serialized["value"])
        except HarnessError:
            continue
        return {
            "property_id": property_id,
            "valid_value": valid_value,
            "invalid_value": {"invalid": True},
        }
    raise HarnessError("No supported writable parameter is available.")


def choose_connection(
    source_properties: Sequence[Mapping[str, object]],
    target_properties: Sequence[Mapping[str, object]],
) -> dict[str, str]:
    outputs = [
        prop
        for prop in source_properties
        if prop.get("direction") == "output"
        and prop.get("connectable") is True
        and isinstance(prop.get("property_id"), str)
        and isinstance(prop.get("type_id"), str)
    ]
    inputs = [
        prop
        for prop in target_properties
        if prop.get("direction") == "input"
        and prop.get("connectable") is True
        and prop.get("connected") is not True
        and isinstance(prop.get("property_id"), str)
        and isinstance(prop.get("type_id"), str)
    ]
    for output in outputs:
        for input_property in inputs:
            if output["type_id"] == input_property["type_id"]:
                return {
                    "source_property": str(output["property_id"]),
                    "target_property": str(input_property["property_id"]),
                }
    raise HarnessError("No compatible connectable runtime properties are available.")


def aggregate_reports(
    reports: Sequence[Mapping[str, object]], required: Sequence[str]
) -> dict[str, object]:
    checks: dict[str, object] = {}
    for report in reports:
        phase_checks = report.get("checks")
        if isinstance(phase_checks, Mapping):
            checks.update({str(name): value for name, value in phase_checks.items()})
    missing = make_check(
        False,
        None,
        {
            "code": "MISSING_EVIDENCE",
            "message": "Required evidence was not produced.",
        },
    )
    for name in required:
        checks.setdefault(name, dict(missing))
    passed = all(
        isinstance(checks.get(name), Mapping) and checks[name].get("passed") is True
        for name in required
    )
    return {
        "status": "passed" if passed else "failed",
        "checks": checks,
        "phases": list(reports),
    }


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise HarnessError("A phase report must contain a JSON object.")
    return value


def _secrets(paths: Iterable[Path]) -> set[str]:
    secrets: set[str] = set()
    for path in paths:
        value = _load_json(path)
        token = value.get("token")
        if isinstance(token, str) and token:
            secrets.add(token)
    return secrets


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    aggregate = subparsers.add_parser("aggregate")
    aggregate.add_argument("--report", action="append", required=True, type=Path)
    aggregate.add_argument("--required-check", action="append", required=True)
    aggregate.add_argument("--secret-file", action="append", default=[], type=Path)
    aggregate.add_argument("--workspace", default="")
    aggregate.add_argument("--output", required=True, type=Path)
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    arguments = _parser().parse_args(argv)
    reports = [_load_json(path) for path in arguments.report]
    combined = aggregate_reports(reports, arguments.required_check)
    cleaned = redact(combined, _secrets(arguments.secret_file), arguments.workspace)
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(
        json.dumps(cleaned, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0 if combined["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
