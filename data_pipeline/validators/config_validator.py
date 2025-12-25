"""Simple validator wrapper for parse configs."""
from typing import Dict, Any
from ..config.models import ParseConfig


def validate_config(cfg: Dict[str, Any]) -> ParseConfig:
    return ParseConfig(**cfg)
