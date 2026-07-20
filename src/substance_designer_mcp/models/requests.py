"""Strict reusable request models for MCP tool schemas."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MoveSpec(StrictRequest):
    node_identifier: str = Field(min_length=1)
    position: tuple[float, float]


class ParameterValue(StrictRequest):
    value: Any


class UsageSpec(StrictRequest):
    name: str = Field(min_length=1, max_length=128)
    components: str = Field(min_length=1, max_length=16)
    color_space: str = Field(min_length=1, max_length=128)


class AtomicPatchNode(StrictRequest):
    alias: str = Field(pattern=r"^[A-Za-z][A-Za-z0-9_-]{0,63}$")
    kind: Literal["atomic"]
    definition_id: str = Field(min_length=1, max_length=256)
    position: tuple[float, float]


class InstancePatchNode(StrictRequest):
    alias: str = Field(pattern=r"^[A-Za-z][A-Za-z0-9_-]{0,63}$")
    kind: Literal["instance"]
    resource: dict[str, Any]
    position: tuple[float, float]


PatchNode = Annotated[AtomicPatchNode | InstancePatchNode, Field(discriminator="kind")]


class PatchParameter(StrictRequest):
    node: str = Field(pattern=r"^[A-Za-z][A-Za-z0-9_-]{0,63}$")
    property_id: str = Field(min_length=1, max_length=256)
    value: Any


class PatchConnection(StrictRequest):
    source_node: str = Field(pattern=r"^[A-Za-z][A-Za-z0-9_-]{0,63}$")
    source_property: str = Field(min_length=1, max_length=256)
    target_node: str = Field(pattern=r"^[A-Za-z][A-Za-z0-9_-]{0,63}$")
    target_property: str = Field(min_length=1, max_length=256)


class GraphPatch(StrictRequest):
    version: Literal["1.0"]
    nodes: list[PatchNode] = Field(min_length=1, max_length=100)
    parameters: list[PatchParameter] = Field(default_factory=list, max_length=300)
    connections: list[PatchConnection] = Field(default_factory=list, max_length=300)
