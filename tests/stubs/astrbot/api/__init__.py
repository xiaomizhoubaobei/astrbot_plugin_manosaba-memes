"""astrbot.api 桩：提供静默 logger。"""

import logging

logger = logging.getLogger("astrbot-stub")
logger.addHandler(logging.NullHandler())
