"""astrbot.api stub package.

The canonical logger lives in tests/conftest.py; pylint also resolves this
stub from the real checkout layout and needs the export.
"""

import logging

logger = logging.getLogger("astrbot-stub")
logger.addHandler(logging.NullHandler())

__all__ = ["logger"]
