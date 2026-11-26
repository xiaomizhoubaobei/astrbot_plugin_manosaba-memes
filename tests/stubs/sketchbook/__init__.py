"""sketchbook 最小桩（仅测试用），对齐 sketchbook-py 0.2.x 的 API 形态。

桩不渲染真实图片，但忠实执行链式调用并记录产物，使 drawer.py 的逻辑
（路径选择、坐标计算、链式调用顺序、字节返回）可被单测覆盖。
"""

from dataclasses import dataclass
from typing import Any, List, Tuple


@dataclass
class DrawerRegion:
    """绘制区域（四坐标为左上/右下）。"""

    top_left_x: int
    top_left_y: int
    bottom_right_x: int
    bottom_right_y: int

    def __init__(
        self, top_left_x: int, top_left_y: int, bottom_right_x: int, bottom_right_y: int
    ) -> None:
        self.top_left_x = top_left_x
        self.top_left_y = top_left_y
        self.bottom_right_x = bottom_right_x
        self.bottom_right_y = bottom_right_y

    def width(self) -> int:
        return self.bottom_right_x - self.top_left_x

    def height(self) -> int:
        return self.bottom_right_y - self.top_left_y


@dataclass
class TextStyle:
    """文本样式。"""

    color: Any = (0, 0, 0, 255)
    bracket_color: Any = (128, 0, 128, 255)
    max_font_height: Any = None
    line_spacing: float = 0.15


@dataclass
class PasteStyle:
    """粘贴样式。"""

    padding: int = 0
    keep_alpha: bool = True
    allow_upscale: bool = False


class _BaseDrawer:
    """抽屉基类：记录操作，输出固定 PNG 字节魔数。"""

    PNG_MAGIC = b"\x89PNG\r\n\x1a\n"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.base_image = kwargs.get("base_image", args[0] if args else None)
        self.font = kwargs.get("font", args[1] if len(args) > 1 else None)
        self.operations: List[Tuple[str, Any]] = []

    def draw(self, text: str, style: Any = None) -> bytes:
        """TextFitDrawer.draw：记录文本并返回假 PNG 字节。"""
        self.operations.append(("draw", text))
        return self.PNG_MAGIC + text.encode("utf-8")


class TextFitDrawer(_BaseDrawer):
    """自适应文本渲染器桩。"""

    pass


class Drawer(_BaseDrawer):
    """链式绘制器桩。"""

    def draw_text(self, text: str, region: Any = None, style: Any = None) -> "Drawer":
        self.operations.append(("text", text))
        return self

    def paste_image(
        self, image: Any, region: Any = None, style: Any = None
    ) -> "Drawer":
        self.operations.append(("paste", image))
        return self

    def finish(self) -> bytes:
        """完成绘制，返回带操作摘要的假 PNG 字节。"""
        return self.PNG_MAGIC + "|".join(str(op[1]) for op in self.operations).encode(
            "utf-8"
        )
