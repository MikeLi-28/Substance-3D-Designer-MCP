from __future__ import annotations

from pathlib import Path

import pytest
from substance_designer_mcp_plugin.errors import ErrorCode, PluginError
from substance_designer_mcp_plugin.services.container import ServiceContainer

from tests.fakes.sd_api import build_fake_designer


def _setup() -> tuple[ServiceContainer, object, dict, dict]:
    fake = build_fake_designer()
    services = ServiceContainer(fake.application, fake.adapter)
    package = services.package.list_packages()["packages"][0]
    graph = services.graph.get_active_graph()["graph"]
    return services, fake, package, graph


def test_import_bitmap_uses_explicit_embed_method_and_can_create_instance(
    tmp_path: Path,
) -> None:
    services, fake, package, graph = _setup()
    image = tmp_path / "source.png"
    image.write_bytes(b"fake png")

    result = services.delivery.import_bitmap(
        {
            "package": package,
            "file_path": str(image),
            "identifier": "source_bitmap",
            "embed_method": "linked",
            "graph": graph,
            "position": [96, 128],
        }
    )

    assert result["resource"]["resource_identifier"] == "source_bitmap"
    assert result["node"]["position"] == [96.0, 128.0]
    assert fake.adapter.imported_bitmaps[-1][1:] == (str(image.resolve()), "linked")


@pytest.mark.parametrize(
    "mutate",
    [
        lambda path: "relative.png",
        lambda path: str(path / "missing.png"),
        lambda path: str(path / "source.exe"),
    ],
)
def test_import_bitmap_rejects_unsafe_or_unsupported_paths(tmp_path: Path, mutate: object) -> None:
    services, fake, package, _graph = _setup()
    source = tmp_path / "source.exe"
    source.write_bytes(b"not a bitmap")
    file_path = mutate(tmp_path)  # type: ignore[operator]
    before = len(fake.package.resources)

    with pytest.raises(PluginError) as caught:
        services.delivery.import_bitmap(
            {
                "package": package,
                "file_path": file_path,
                "identifier": "source_bitmap",
                "embed_method": "linked",
            }
        )

    assert caught.value.code is ErrorCode.INVALID_PARAMETER
    assert len(fake.package.resources) == before


def test_import_bitmap_requires_graph_and_position_together(tmp_path: Path) -> None:
    services, _fake, package, graph = _setup()
    image = tmp_path / "source.png"
    image.write_bytes(b"fake png")

    with pytest.raises(PluginError) as missing_position:
        services.delivery.import_bitmap(
            {
                "package": package,
                "file_path": str(image),
                "identifier": "source_bitmap",
                "embed_method": "linked",
                "graph": graph,
            }
        )

    assert missing_position.value.code is ErrorCode.INVALID_PARAMETER

    with pytest.raises(PluginError) as non_finite:
        services.delivery.import_bitmap(
            {
                "package": package,
                "file_path": str(image),
                "identifier": "source_bitmap",
                "embed_method": "linked",
                "graph": graph,
                "position": [float("inf"), 0],
            }
        )
    assert non_finite.value.code is ErrorCode.INVALID_PARAMETER


def test_export_sbsar_requires_saved_package_and_explicit_settings(tmp_path: Path) -> None:
    services, fake, package, _graph = _setup()
    target = tmp_path / "material.sbsar"
    request = {
        "package": package,
        "file_path": str(target),
        "compression_mode": "best",
        "expose_output_size": True,
        "expose_pixel_size": False,
        "expose_random_seed": True,
        "icon_enabled": False,
        "overwrite": False,
    }

    result = services.delivery.export_sbsar(request)

    assert result["exported"] is True
    assert result["file_path"] == str(target.resolve())
    assert fake.adapter.sbsar_exports[-1] == {
        "package": fake.package,
        "file_path": str(target.resolve()),
        "compression_mode": "best",
        "expose_output_size": True,
        "expose_pixel_size": False,
        "expose_random_seed": True,
        "icon_enabled": False,
    }

    fake.package.file_path = ""
    unsaved_ref = services.package.list_packages()["packages"][0]
    with pytest.raises(PluginError) as unsaved:
        services.delivery.export_sbsar({**request, "package": unsaved_ref})
    assert unsaved.value.code is ErrorCode.SAVE_FAILED


def test_export_sbsar_rejects_bad_path_and_existing_target_without_opt_in(
    tmp_path: Path,
) -> None:
    services, _fake, package, _graph = _setup()
    target = tmp_path / "material.sbsar"
    target.write_bytes(b"occupied")
    base = {
        "package": package,
        "file_path": str(target),
        "compression_mode": "auto",
        "expose_output_size": True,
        "expose_pixel_size": False,
        "expose_random_seed": True,
        "icon_enabled": False,
        "overwrite": False,
    }

    with pytest.raises(PluginError) as exists:
        services.delivery.export_sbsar(base)
    with pytest.raises(PluginError) as suffix:
        services.delivery.export_sbsar({**base, "file_path": str(tmp_path / "bad.sbs")})
    with pytest.raises(PluginError) as compression:
        services.delivery.export_sbsar({**base, "compression_mode": "fastest"})

    assert exists.value.code is ErrorCode.INVALID_PARAMETER
    assert suffix.value.code is ErrorCode.INVALID_PARAMETER
    assert compression.value.code is ErrorCode.INVALID_PARAMETER
