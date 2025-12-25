from ..views.mvb_view import MVBView
from ..views.phm_view import PHMView
from typing import Dict, Any

class Router:
    def __init__(self):
        self.views = {
            'MVB': MVBView(),
            'PHM': PHMView(),
        }

    def route(self, request: Dict[str, Any]):
        module = request.get('module', 'MVB')
        request_type = request.get('requestType', 'parse')
        view = self.views.get(module)
        if view:
            if request_type == 'parse':
                return view.parse(request)
            elif request_type == 'plot':
                return view.plot(request)
            elif request_type == 'download':
                return view.download(request)
        return {'error': 'Invalid module or request type'}