"""Pydantic config models for parsing configuration."""
from pydantic import BaseModel
from typing import Optional, Dict, Any


class ParseConfig(BaseModel):
    version: str
    module: str
    parser_version: Optional[str]
    byte_order: Optional[str]
    parse_mode: Optional[str]
    signal_map: Optional[Dict[str, Any]]
    second_parse: Optional[Dict[str, Any]]

    class Config:
        extra = "forbid"
