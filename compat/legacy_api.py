from ..data_pipeline.routing.router import Router
from ..data_pipeline.config.config_loader import load_config

router = Router()

def parse(request_body: dict) -> dict:
    config = load_config(request_body.get('configVersion', 'v1'))
    request = {**request_body, 'config': config, 'requestType': 'parse'}
    return router.route(request)

def plot(request_body: dict) -> dict:
    config = load_config(request_body.get('configVersion', 'v1'))
    request = {**request_body, 'config': config, 'requestType': 'plot'}
    return router.route(request)

def download(request_body: dict) -> dict:
    config = load_config(request_body.get('configVersion', 'v1'))
    request = {**request_body, 'config': config, 'requestType': 'download'}
    return router.route(request)