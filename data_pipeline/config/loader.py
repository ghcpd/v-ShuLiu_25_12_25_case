"""Config loader + pydantic validation for parser configs (versioned)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from pydantic import BaseModel, Field, ValidationError


class SignalSpec(BaseModel):
    offset: int
    length: int
    scale: float = 1.0


class ParserConfig(BaseModel):
    version: str
    module: str
    parser_version: str
    byte_order: str
    parse_mode: str
    signal_map: Dict[str, SignalSpec]
    second_parse: Dict[str, Any] = Field(default_factory=dict)


def load_config(version: str, data_dir: Path) -> ParserConfig:
    path = data_dir / f"sample_config_{version}.json" if version != "v1" else data_dir / "sample_config_v1.json"
    if not path.exists():
        raise FileNotFoundError(path)
    raw = json.loads(path.read_text(encoding="utf-8"))
    try:
        return ParserConfig.parse_obj(raw)
    except ValidationError as e:
        raise
