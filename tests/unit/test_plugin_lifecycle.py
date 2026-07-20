from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from substance_designer_mcp_plugin import initializeSDPlugin, uninitializeSDPlugin
from substance_designer_mcp_plugin.plugin import initialize_plugin, uninitialize_plugin

from tests.fakes.sd_api import build_fake_designer


class FakeDispatcher:
    pass


class FakeServer:
    instances: list[FakeServer] = []

    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs
        self.started = 0
        self.stopped = 0
        self.instances.append(self)

    def start(self) -> dict[str, Any]:
        self.started += 1
        return {"port": 1234}

    def stop(self) -> None:
        self.stopped += 1


def test_plugin_initialize_is_idempotent_and_uninitialize_stops_bridge(tmp_path: Path) -> None:
    fake = build_fake_designer()
    uninitialize_plugin()
    FakeServer.instances.clear()

    first = initialize_plugin(
        application=fake.application,
        adapter=fake.adapter,
        dispatcher=FakeDispatcher(),
        server_factory=FakeServer,
        session_path=tmp_path / "session.json",
    )
    second = initialize_plugin(
        application=fake.application,
        adapter=fake.adapter,
        dispatcher=FakeDispatcher(),
        server_factory=FakeServer,
        session_path=tmp_path / "session.json",
    )

    assert first is second
    assert len(FakeServer.instances) == 1
    assert FakeServer.instances[0].started == 1

    uninitialize_plugin()
    assert FakeServer.instances[0].stopped == 1


def test_designer_entry_points_are_callable() -> None:
    assert callable(initializeSDPlugin)
    assert callable(uninitializeSDPlugin)


def test_plugin_manifest_matches_official_metadata_shape() -> None:
    manifest_path = (
        Path(__file__).resolve().parents[2]
        / "sd_plugin"
        / "substance_designer_mcp_plugin"
        / "pluginInfo.json"
    )

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest == {
        "metadata_format_version": "1",
        "name": "substance_designer_mcp_plugin",
        "version": "1.1.0",
        "author": "substance-designer-mcp contributors",
        "min_designer_version": "16.0.0",
        "platform": "any",
    }
