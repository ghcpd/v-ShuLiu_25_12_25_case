"""Simple logging utilities (struct-like)"""
import logging

logger = logging.getLogger("data_pipeline")
if not logger.handlers:
    h = logging.StreamHandler()
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    h.setFormatter(fmt)
    logger.addHandler(h)
    logger.setLevel(logging.INFO)


def log_info(msg: str, **kwargs):
    logger.info(msg + " %s", kwargs)


def log_error(msg: str, **kwargs):
    logger.error(msg + " %s", kwargs)
