from __future__ import annotations

from typing import Any


class _Type:
    def getId(self) -> str:
        return "int2"


class _Value:
    def getType(self) -> _Type:
        return _Type()

    def get(self) -> list[int]:
        return [10, 10]


class FakePresetInput:
    def getIdentifier(self) -> str:
        return "$outputsize"

    def getValue(self) -> Any:
        return _Value()


class FakePreset:
    def __init__(self, label: str) -> None:
        self.label = label

    def getLabel(self) -> str:
        return self.label

    def getUserTags(self) -> str:
        return ""

    def getInputs(self) -> list[FakePresetInput]:
        return [FakePresetInput()]
