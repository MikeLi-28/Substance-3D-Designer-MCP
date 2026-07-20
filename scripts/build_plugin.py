"""Build a deterministic, distributable Designer plugin ZIP."""

from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path


def build_plugin(source: Path, output_dir: Path) -> Path:
    """Package one validated plugin directory under its own archive root."""

    source = Path(source).resolve()
    output_dir = Path(output_dir).resolve()
    manifest_path = source / "pluginInfo.json"
    if not source.is_dir() or not manifest_path.is_file():
        raise ValueError("Plugin source must contain pluginInfo.json.")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    version = str(manifest["version"])
    output_dir.mkdir(parents=True, exist_ok=True)
    archive = output_dir / (f"{source.name}-{version}.zip")
    package_files = [
        path
        for path in source.rglob("*")
        if path.is_file()
        and path != manifest_path
        and "__pycache__" not in path.parts
        and path.suffix != ".pyc"
    ]
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        entries = [(source.name + "/pluginInfo.json", manifest_path)]
        entries.extend(
            (
                source.name + "/" + source.name + "/" + path.relative_to(source).as_posix(),
                path,
            )
            for path in package_files
        )
        for relative, path in sorted(entries, key=lambda item: item[0]):
            info = zipfile.ZipInfo(relative, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            bundle.writestr(info, path.read_bytes())
    return archive


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        type=Path,
        default=Path("sd_plugin/substance_designer_mcp_plugin"),
    )
    parser.add_argument("--output", type=Path, default=Path("artifacts"))
    arguments = parser.parse_args()
    archive = build_plugin(arguments.source, arguments.output)
    print(archive)


if __name__ == "__main__":
    main()
