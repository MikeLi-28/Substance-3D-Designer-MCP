"""Secure publication and ownership-aware cleanup of the plugin session file."""

from __future__ import annotations

import contextlib
import json
import os
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from .protocol import PROTOCOL_VERSION


class SessionFile:
    """Own one published bridge session."""

    def __init__(
        self,
        path: Path,
        port: int,
        designer_version: str,
        plugin_version: str = "1.1.0",
    ) -> None:
        self.path = Path(path)
        self.port = port
        self.designer_version = designer_version
        self.plugin_version = plugin_version
        self._published: Optional[Dict[str, Any]] = None

    def publish(self) -> Dict[str, Any]:
        """Atomically publish a new random loopback session."""

        info: Dict[str, Any] = {
            "protocol_version": PROTOCOL_VERSION,
            "host": "127.0.0.1",
            "port": self.port,
            "token": secrets.token_hex(32),
            "pid": os.getpid(),
            "designer_version": self.designer_version,
            "plugin_version": self.plugin_version,
            "started_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(info, indent=2, sort_keys=True), encoding="utf-8")
        with contextlib.suppress(OSError):
            os.chmod(temporary, 0o600)
        os.replace(temporary, self.path)
        with contextlib.suppress(OSError):
            os.chmod(self.path, 0o600)
        self._published = info
        return dict(info)

    def cleanup(self) -> None:
        """Delete the file only if it still represents this process and token."""

        if self._published is None or not self.path.exists():
            return
        try:
            current = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        if (
            current.get("pid") == self._published["pid"]
            and current.get("token") == self._published["token"]
        ):
            with contextlib.suppress(FileNotFoundError):
                self.path.unlink()
