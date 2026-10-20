"""Unit-test seams for AstrBot; no server, adapters, or plugin install involved."""
import base64
import importlib.util
import logging
from pathlib import Path
import sys
import types

ROOT = Path(__file__).resolve().parents[1]
NAME = "astrbot_plugin_manosaba_memes"
spec = importlib.util.spec_from_file_location(NAME, ROOT / "__init__.py")
package = importlib.util.module_from_spec(spec)
sys.modules[NAME] = package
spec.loader.exec_module(package)


class Image:
    def __init__(self, file):
        self.file = file

    @staticmethod
    def fromBytes(data):
        return Image("base64://" + base64.b64encode(data).decode())


class Star:
    def __init__(self, context):
        self.context = context


class Filters:
    @staticmethod
    def command(*args, **kwargs):
        return lambda fn: fn

    @staticmethod
    def regex(pattern, **kwargs):
        def wrap(fn):
            fn.trigger = pattern
            return fn
        return wrap


for name, attrs in {
    "astrbot": {},
    "astrbot.api": {"logger": logging.getLogger("test")},
    "astrbot.api.event": {"filter": Filters, "AstrMessageEvent": object},
    "astrbot.api.star": {"Context": object, "Star": Star, "StarTools": types.SimpleNamespace()},
    "astrbot.api.message_components": {"Image": Image},
}.items():
    module = types.ModuleType(name)
    module.__dict__.update(attrs)
    sys.modules[name] = module
