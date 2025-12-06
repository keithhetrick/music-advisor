"""Compatibility wrapper forwarding to adapters_src.plugin_loader."""
from ma_audio_engine.adapters_src import plugin_loader as _pl

_PLUGINS_ROOT = _pl._PLUGINS_ROOT
_DEFAULT_CONFIG = _pl._DEFAULT_CONFIG
list_plugins = _pl.list_plugins
load_plugin = _pl.load_plugin
load_from_config = _pl.load_from_config
load_factory = _pl.load_factory

__all__ = [
    "_PLUGINS_ROOT",
    "_DEFAULT_CONFIG",
    "list_plugins",
    "load_plugin",
    "load_from_config",
    "load_factory",
]
