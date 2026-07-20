"""Stable JSON models used by MCP tool inputs and outputs."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class PackageRef(StrictModel):
    package_url: str = Field(min_length=1)
    file_path: str | None = None
    label: str | None = None


class GraphRef(StrictModel):
    package_url: str = Field(min_length=1)
    graph_identifier: str = Field(min_length=1)
    graph_type: str = "substance"


class NodeRef(StrictModel):
    package_url: str = Field(min_length=1)
    graph_identifier: str = Field(min_length=1)
    node_identifier: str = Field(min_length=1)
    definition_id: str = Field(min_length=1)
    label: str | None = None
    session_handle: str = Field(min_length=1)
    handle_lifetime: Literal["current_designer_session"] = "current_designer_session"


class LibraryResourceRef(StrictModel):
    package_url: str = Field(min_length=1)
    resource_identifier: str = Field(min_length=1)
    stable_key: str = Field(min_length=1)
    runtime_url: str = Field(min_length=1)
    label: str | None = None
    category: str | None = None
