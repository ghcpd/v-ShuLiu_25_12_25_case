"""Request/config validation models (pydantic)."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, validator


class RequestSchema(BaseModel):
    module: str
    requestType: str
    configVersion: str
    timeStart: datetime
    timeEnd: datetime
    timeStep: str
    trainNo: str
    carriage: str
    parse_mode: Optional[str] = None

    @validator("timeEnd")
    def end_after_start(cls, v, values):
        if "timeStart" in values and v <= values["timeStart"]:
            raise ValueError("timeEnd must be after timeStart")
        return v


class ConfigSchema(BaseModel):
    version: str
    module: str
