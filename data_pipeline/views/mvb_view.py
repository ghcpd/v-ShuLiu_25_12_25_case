from .base_view import BaseView
from ..parsers.mvb_parser import MVBParser
from ..cache.lru import cache_manager
from ..sources import fetch_data
from typing import Dict, Any, Tuple
import hashlib

class MVBView(BaseView):
    def __init__(self):
        self.parser = MVBParser()

    def _get_cache_key(self, request: Dict[str, Any]) -> Tuple:
        # Structured key
        module = request.get('module', 'MVB')
        endpoint_id = request.get('endpointId', 'default')
        request_type = request.get('requestType', 'parse')
        config_version = request.get('configVersion', 'v1')
        time_start = request.get('timeStart')
        time_end = request.get('timeEnd')
        time_step = request.get('timeStep')
        train_no = request.get('trainNo')
        carriage = request.get('carriage')
        parse_mode = request.get('parseMode', 'standard')
        return (module, endpoint_id, request_type, config_version, time_start, time_end, time_step, train_no, carriage, parse_mode)

    def parse(self, request: Dict[str, Any]) -> Dict[str, Any]:
        key = self._get_cache_key(request)
        namespace = f"{request.get('module', 'MVB')}_primary"
        def compute():
            data = fetch_data(request)
            config = request.get('config', {})
            return self.parser.parse_primary(data, config)
        primary_data = cache_manager.get_or_compute(namespace, key, compute)
        # Secondary
        secondary_key = key + ('secondary',)
        namespace_sec = f"{request.get('module', 'MVB')}_secondary"
        def compute_sec():
            return self.parser.parse_secondary(primary_data, request.get('config', {}))
        secondary_data = cache_manager.get_or_compute(namespace_sec, secondary_key, compute_sec)
        return {'primary': primary_data, 'secondary': secondary_data}

    def plot(self, request: Dict[str, Any]) -> Dict[str, Any]:
        # Similar, but return plot data
        parsed = self.parse(request)
        # Simulate plotting
        return {'plot_data': parsed['secondary']}

    def download(self, request: Dict[str, Any]) -> Dict[str, Any]:
        # Return data for download
        parsed = self.parse(request)
        return {'download_data': parsed}