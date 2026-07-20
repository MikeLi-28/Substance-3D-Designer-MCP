from __future__ import annotations

import logging

from substance_designer_mcp import __main__
from substance_designer_mcp.logging_config import configure_logging


def test_logging_uses_stderr_not_stdout(capsys: object) -> None:
    configure_logging(level="INFO")

    logging.getLogger("substance_designer_mcp.test").info("bridge ready")

    captured = capsys.readouterr()  # type: ignore[attr-defined]
    assert captured.out == ""
    assert "bridge ready" in captured.err


def test_cli_runs_stdio_without_writing_stdout(monkeypatch: object, capsys: object) -> None:
    calls: list[str] = []

    class FakeServer:
        def run(self, transport: str) -> None:
            calls.append(transport)

    monkeypatch.setattr(__main__, "build_server", lambda *_args: FakeServer())  # type: ignore[attr-defined]

    __main__.main()

    captured = capsys.readouterr()  # type: ignore[attr-defined]
    assert captured.out == ""
    assert calls == ["stdio"]
