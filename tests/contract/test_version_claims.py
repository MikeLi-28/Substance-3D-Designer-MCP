from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

ENGLISH_COMPATIBILITY_TABLE = """| Substance Designer version | Status |
|---|---|
| 16.0.3 | Supported baseline; 1.1.0 authoring extensions are not yet real-machine verified |
| Other released 16.x versions | Unverified; capabilities are detected at runtime |
| Newer major versions | Experimental and unverified |"""

CHINESE_COMPATIBILITY_TABLE = """| Substance Designer 版本 | 状态 |
|---|---|
| 16.0.3 | 受支持基线；1.1.0 authoring 扩展尚未完成真机验证 |
| 其他已发布的 16.x 版本 | 未验证；按运行时能力探测启用功能 |
| 更新的主版本 | 实验性且未验证 |"""

CURRENT_PUBLIC_FILES = (
    "README.md",
    "README.zh-CN.md",
    "CHANGELOG.md",
    "docs/compatibility.md",
    "docs/installation.md",
    "docs/architecture.md",
    "SECURITY.md",
    "pyproject.toml",
)


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_readmes_use_the_same_precise_compatibility_status() -> None:
    english = _read("README.md")
    chinese = _read("README.zh-CN.md")

    assert english.startswith("# Substance-3D-Designer-MCP\n")
    assert chinese.startswith("# Substance-3D-Designer-MCP\n")
    assert ENGLISH_COMPATIBILITY_TABLE in english
    assert (
        "A version is marked as fully tested only after the plugin and MCP tools have been "
        "exercised in a real Substance Designer installation. Capability detection does not "
        "replace real-version testing."
    ) in english
    assert CHINESE_COMPATIBILITY_TABLE in chinese
    assert (
        "只有在真实 Substance Designer 安装环境中完成插件加载和 MCP 工具测试后，具体版本"
        "才会被标记为“已完整测试”。能力探测不能代替真实版本测试。"
    ) in chinese


def test_readmes_offer_chinese_first_language_navigation() -> None:
    english = _read("README.md")
    chinese = _read("README.zh-CN.md")

    assert "[中文](README.zh-CN.md) | **English**" in english[:200]
    assert "**中文** | [English](README.md)" in chinese[:200]


def test_current_public_files_do_not_make_broad_or_stale_version_claims() -> None:
    forbidden = (
        "Substance 3D Designer 16+",
        "Startup path partially verified",
        "Graph/node operations remain unverified",
        "Supports all SD 16+ versions",
        "Fully compatible with future versions",
        "SD 17 supported",
    )

    for relative in CURRENT_PUBLIC_FILES:
        text = _read(relative)
        for phrase in forbidden:
            assert phrase not in text, f"{relative} contains stale claim: {phrase}"


def test_compatibility_document_separates_detection_from_verification() -> None:
    text = _read("docs/compatibility.md")

    assert "Version detection" in text
    assert "Runtime capability detection" in text
    assert "Compatibility adapter" in text
    assert (
        "Capability detection means the project can identify whether a required API is present."
    ) in text
    assert ("It does not prove that an untested Designer version is fully compatible.") in text
    assert (
        "能力探测只能确认当前运行环境中是否存在所需 API，不能证明一个未经测试的 Designer "
        "版本完全兼容。"
    ) in text


def test_package_metadata_points_to_the_public_repository_without_16_plus_claim() -> None:
    text = _read("pyproject.toml")

    assert (
        'description = "A secure MCP server for Adobe Substance 3D Designer '
        'with a 16.0.3 real-machine verified baseline."'
    ) in text
    assert "https://github.com/MikeLi-28/Substance-3D-Designer-MCP" in text
    assert '"Development Status :: 5 - Production/Stable"' in text
