"""Plugin hooks placeholder"""

PLUGINS = {}


def register(name: str, handler):
    PLUGINS[name] = handler


def get(name: str):
    return PLUGINS.get(name)
