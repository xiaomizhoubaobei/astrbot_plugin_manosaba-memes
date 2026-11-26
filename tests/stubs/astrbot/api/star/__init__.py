"""astrbot.api.star 桩：Star 基类、Context 与数据目录工具。"""

from pathlib import Path
from typing import Any


class Context:
    """宿主上下文桩。"""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        pass


class Star:
    """插件基类桩。"""

    def __init__(self, context: Any) -> None:
        self.context = context


class StarTools:
    """宿主工具桩：把测试期数据目录指到临时目录。"""

    DATA_DIR: Path = Path("/tmp/astrbot-stub-data")

    @classmethod
    def get_data_dir(cls) -> Path:
        return cls.DATA_DIR
