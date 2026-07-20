from __future__ import annotations

from substance_designer_mcp_plugin.compatibility.detector import detect_compatibility

from tests.fakes.sd_api import build_fake_designer


def test_sd16_reports_real_machine_verified_baseline_with_runtime_capabilities() -> None:
    fake = build_fake_designer("16.0.3")

    result = detect_compatibility(fake.application)

    assert result["designer_version"] == "16.0.3"
    assert result["verification_status"] == "verified"
    assert result["compatibility_status"] == "supported"
    assert result["verified_versions"] == ["16.0.3"]
    assert result["warning"] is None
    assert result["capabilities"]["graph_read"]["available"] is True
    assert result["capabilities"]["graph_read"]["real_machine_verified"] is True
    assert result["capabilities"]["connection_write"]["real_machine_verified"] is True
    assert (
        result["capabilities"]["graph_read"]["verification_source"]
        == "Substance 3D Designer 16.0.3 compatibility baseline"
    )


def test_new_public_authoring_capabilities_are_available_but_not_falsely_verified() -> None:
    fake = build_fake_designer("16.0.3")

    result = detect_compatibility(fake.application)

    for name in (
        "package_create",
        "graph_create",
        "graph_snapshot",
        "graph_output_write",
        "graph_patch",
        "bitmap_import",
        "package_save_as",
        "package_export_sbsar",
        "ui_open_graph",
    ):
        assert result["capabilities"][name]["available"] is True
        assert result["capabilities"][name]["real_machine_verified"] is False
        assert (
            result["capabilities"][name]["verification_source"]
            == "Adobe Substance 3D Designer 16.0.3 Python API documentation"
        )


def test_other_sd16_version_is_untested_but_uses_capability_detection() -> None:
    fake = build_fake_designer("16.1.0")

    result = detect_compatibility(fake.application)

    assert result["verification_status"] == "untested"
    assert result["compatibility_status"] == "capability_detected"
    assert result["verified_versions"] == ["16.0.3"]
    assert result["warning"] == "This Designer version has not been individually tested."
    assert result["capabilities"]["package_read"]["available"] is True
    assert result["capabilities"]["package_read"]["real_machine_verified"] is False


def test_unknown_new_major_is_experimental_and_not_claimed_supported() -> None:
    fake = build_fake_designer("17.0.0")

    result = detect_compatibility(fake.application)

    assert result["verification_status"] == "untested"
    assert result["compatibility_status"] == "experimental"
    assert result["verified_versions"] == ["16.0.3"]
    assert result["warning"] == (
        "This Designer major version has not been verified. Available tools are enabled "
        "through runtime capability detection."
    )
    assert result["capabilities"]["package_read"]["available"] is True


def test_older_major_is_unsupported_without_disabling_diagnostics() -> None:
    fake = build_fake_designer("15.2.0")

    result = detect_compatibility(fake.application)

    assert result["verification_status"] == "untested"
    assert result["compatibility_status"] == "unsupported"
    assert result["verified_versions"] == ["16.0.3"]
    assert result["warning"] == (
        "This Designer version is outside the Designer 16 compatibility baseline."
    )
    assert result["capabilities"]["application_info"]["available"] is True


def test_missing_ui_manager_disables_only_ui_capabilities() -> None:
    fake = build_fake_designer()
    fake.application.ui_mgr = None  # type: ignore[assignment]

    result = detect_compatibility(fake.application)

    assert result["capabilities"]["package_read"]["available"] is True
    assert result["capabilities"]["active_graph"]["available"] is False


def test_no_active_graph_does_not_claim_node_dependent_write_capabilities() -> None:
    fake = build_fake_designer()
    fake.application.ui_mgr.graph = None

    result = detect_compatibility(fake.application)

    assert result["capabilities"]["connection_write"]["available"] is False
    assert result["capabilities"]["parameter_write"]["available"] is False
