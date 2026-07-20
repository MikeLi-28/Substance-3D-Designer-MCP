from __future__ import annotations

import tarfile
import zipfile
from pathlib import Path

from scripts.verify_release import scan_source_tree, verify_artifacts

ROOT = Path(__file__).resolve().parents[2]


def test_current_source_tree_has_no_high_risk_static_findings() -> None:
    issues = scan_source_tree(ROOT)

    assert issues == []


def test_scanner_detects_arbitrary_execution_subprocess_and_non_loopback(tmp_path: Path) -> None:
    source = tmp_path / "src" / "demo"
    source.mkdir(parents=True)
    (source / "bad.py").write_text(
        "import subprocess\ndef bad(value):\n    eval(value)\n    sock.bind(('0.0.0.0', 0))\n",
        encoding="utf-8",
    )

    issues = scan_source_tree(tmp_path)

    assert any("subprocess" in issue for issue in issues)
    assert any("eval" in issue for issue in issues)
    assert any("0.0.0.0" in issue for issue in issues)


def test_scanner_checks_plugin_python39_syntax(tmp_path: Path) -> None:
    plugin = tmp_path / "sd_plugin" / "demo"
    plugin.mkdir(parents=True)
    (plugin / "new_syntax.py").write_text(
        "match value:\n    case 1:\n        pass\n",
        encoding="utf-8",
    )

    issues = scan_source_tree(tmp_path)

    assert any("Python 3.9" in issue for issue in issues)


def test_artifact_verifier_rejects_unexpected_sdist_roots(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    dist.mkdir()
    sdist = dist / "substance_designer_mcp-1.1.0.tar.gz"
    unexpected_file = tmp_path / "extra.txt"
    unexpected_file.write_text("unexpected", encoding="utf-8")
    with tarfile.open(sdist, "w:gz") as bundle:
        bundle.add(
            unexpected_file,
            arcname="substance_designer_mcp-1.1.0/misc/extra.txt",
        )
    plugin_archive = tmp_path / "plugin.zip"
    with zipfile.ZipFile(plugin_archive, "w") as bundle:
        bundle.writestr(
            "substance_designer_mcp_plugin/pluginInfo.json",
            '{"version":"1.1.0"}',
        )

    issues = verify_artifacts(tmp_path, plugin_archive)

    assert any("unexpected top-level path: misc" in issue for issue in issues)
