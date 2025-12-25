# placeholder for plugin registration (extensions, codecs, transforms)

PLUGINS = {}


def register(name: str, obj):
    PLUGINS[name] = obj


def get(name: str):
    return PLUGINS.get(name)
