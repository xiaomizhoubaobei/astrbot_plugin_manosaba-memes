"""Unit-test seams for AstrBot; no server, adapters, or plugin install involved."""

import base64
import importlib.util
import logging
import sys
import tempfile
import types
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
NAME = "astrbot_plugin_manosaba_memes"
spec = importlib.util.spec_from_file_location(NAME, ROOT / "__init__.py")
assert spec is not None
assert spec.loader is not None
package = importlib.util.module_from_spec(spec)
sys.modules[NAME] = package
spec.loader.exec_module(package)


class Image:
    """Minimal AstrBot image component carrying a data URI."""

    def __init__(self, file: str) -> None:
        self.file = file

    @staticmethod
    def fromBytes(data: bytes) -> "Image":
        """Build an image component from raw bytes."""
        return Image("base64://" + base64.b64encode(data).decode())


class Star:
    """Minimal AstrBot Star base class."""

    def __init__(self, context: Any) -> None:
        self.context = context


class Filters:
    """Minimal AstrBot filter decorator stub."""

    @staticmethod
    def command(*args: Any, **kwargs: Any) -> Any:
        """Return a no-op command decorator."""
        return lambda fn: fn

    @staticmethod
    def regex(pattern: str, **kwargs: Any) -> Any:
        """Return a regex decorator recording the pattern."""

        def wrap(fn: Any) -> Any:
            fn.trigger = pattern
            return fn

        return wrap


STUB_MODULES: dict[str, dict[str, Any]] = {
    "astrbot": {},
    "astrbot.api": {"logger": logging.getLogger("test")},
    "astrbot.api.event": {"filter": Filters, "AstrMessageEvent": object},
    "astrbot.api.star": {
        "Context": object,
        "Star": Star,
        "StarTools": types.SimpleNamespace(
            get_data_dir=lambda name: Path(tempfile.gettempdir()) / name
        ),
    },
    "astrbot.api.message_components": {"Image": Image},
}

for name, attrs in STUB_MODULES.items():
    module = types.ModuleType(name)
    module.__dict__.update(attrs)
    sys.modules[name] = module
