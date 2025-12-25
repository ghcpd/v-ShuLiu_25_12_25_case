"""Small structured logger used in tests (plugs into stdlib logging)."""
import logging
import json


def get_logger(name: str):
    logger = logging.getLogger(name)
    if not logger.handlers:
        h = logging.StreamHandler()
        fmt = logging.Formatter("%(message)s")
        h.setFormatter(fmt)
        logger.addHandler(h)
        logger.setLevel(logging.INFO)
    return logger


def log_structured(logger, **kwargs):
    logger.info(json.dumps(kwargs, default=str))
