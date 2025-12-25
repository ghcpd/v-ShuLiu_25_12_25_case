"""Plot view which uses cache and parsers."""
from typing import Dict, Any
from ..cache.lru import LRUCacheManager
from ..parsers.mvb import parse_mvb
from ..parsers.phm import parse_phm


def handle_plot(request: Dict[str, Any], endpoint_id: str, cache: LRUCacheManager) -> Dict[str, Any]:
    module = request["module"]
    request_type = request.get("requestType", "plot")
    config_version = request.get("configVersion", "v1")
    time_start = request["timeStart"]
    time_end = request["timeEnd"]
    time_step = request.get("timeStep", "1s")
    train_no = request.get("trainNo", "")
    carriage = request.get("carriage", "")
    # parse mode from config typically
    parse_mode = request.get("parseMode", "standard")

    def compute():
        # in real system we'd fetch raw bytes; here use placeholder
        raw = b""""  # placeholder
        if module == "MVB":
            return parse_mvb(raw, {"version": config_version}, time_start, time_end, time_step)
        else:
            return parse_phm(raw, {"version": config_version}, time_start, time_end, time_step)

    return cache.get_or_compute(module=module, endpoint_id=endpoint_id, request_type=request_type,
                                config_version=config_version, time_start=time_start, time_end=time_end,
                                time_step=time_step, train_no=train_no, carriage=carriage,
                                parse_mode=parse_mode, compute_fn=compute)
