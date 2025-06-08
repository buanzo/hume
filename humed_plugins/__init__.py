import importlib
import pkgutil

_plugins = {}
plugin_config_templates = {}


def load_plugins():
    global _plugins, plugin_config_templates
    for loader, name, is_pkg in pkgutil.iter_modules(__path__):
        module = importlib.import_module(f"{__name__}.{name}")
        method = getattr(module, 'TRANSFER_METHOD', name)
        _plugins[method] = module
        cfg = getattr(module, 'CONFIG_TEMPLATE', None)
        if cfg is not None:
            plugin_config_templates[method] = cfg
    return _plugins


def get_plugin(name):
    return _plugins.get(name)
