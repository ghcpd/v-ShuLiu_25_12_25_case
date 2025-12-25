"""Pydantic schemas for parser configs (versioned)."""
from __future__ import annotations

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field, validator


class SignalSpec(BaseModel):
    offset: int
    length: int
    scale: float = 1.0


class SecondParse(BaseModel):
    plot_metrics: Optional[list[str]] = []
    downsample: Optional[Dict[str, Any]] = None


class ParserConfig(BaseModel):
    version: str = Field(...)
    module: str = Field(...)
    parser_version: str = Field(...)
    byte_order: str = Field("little")
    parse_mode: str = Field("standard")
    signal_map: Dict[str, SignalSpec] = Field(default_factory=dict)
    second_parse: Optional[SecondParse] = None

    @validator("version")
    def version_must_start_with_v(cls, v):
        if not str(v).startswith("v"):
            raise ValueError("version must start with 'v'")
        return v
