"""Small allow-list registry with write serialization."""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any, Callable, Dict, Mapping, Optional

from ..errors import ErrorCode, PluginError

Handler = Callable[[Dict[str, Any]], Any]
Validator = Callable[[Dict[str, Any]], Dict[str, Any]]


@dataclass(frozen=True)
class Command:
    handler: Handler
    validator: Optional[Validator]
    write: bool
    destructive: bool


class CommandRegistry:
    """Register and execute only explicitly allowed commands."""

    def __init__(self) -> None:
        self._commands: Dict[str, Command] = {}
        self._write_lock = threading.Lock()

    def register(
        self,
        name: str,
        handler: Handler,
        *,
        validator: Optional[Validator] = None,
        write: bool = False,
        destructive: bool = False,
    ) -> None:
        if name in self._commands:
            raise ValueError(f"Command {name} is already registered.")
        self._commands[name] = Command(handler, validator, write, destructive)

    def execute(self, name: str, arguments: Mapping[str, Any]) -> Any:
        """Validate and execute one allow-listed command."""

        command = self._commands.get(name)
        if command is None:
            raise PluginError(
                ErrorCode.UNSUPPORTED_CAPABILITY,
                "The requested command is not supported.",
                {"command": name},
            )
        normalized = dict(arguments)
        if command.destructive and normalized.get("confirm") is not True:
            raise PluginError(
                ErrorCode.DESTRUCTIVE_CONFIRMATION_REQUIRED,
                "This operation requires confirm=true.",
            )
        if command.validator is not None:
            normalized = command.validator(normalized)
        if command.write:
            with self._write_lock:
                return command.handler(normalized)
        return command.handler(normalized)

    def names(self) -> list[str]:
        """Return registered command names in stable sorted order."""

        return sorted(self._commands)
