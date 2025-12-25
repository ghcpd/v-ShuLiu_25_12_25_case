"""Validation helpers for ParserConfig."""
from __future__ import annotations

from ..config.schemas import ParserConfig
from typing import Dict, Any


def validate_config(cfg: Dict[str, Any]) -> ParserConfig:
    """Validate raw dict against ParserConfig pydantic model.
    Raises ValidationError on failure.
    """
    return ParserConfig.parse_obj(cfg)
