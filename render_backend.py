"""绘图后端适配层。

优先使用 sketchbook-py（Rust 原生渲染）；当它不可用（如 Python 3.15
暂无对应的预构建 wheel）时，自动回退到 Pillow 实现同样的 API 契约。
上层 drawer.py 只依赖本模块导出的符号，不直接 import sketchbook。
"""

from __future__ import annotations

import io
import logging
import os
import re
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

# 测试/特殊场景可通过该环境变量强制指定后端：sketchbook / pillow。
# 正常运行时留空，由工厂自行探测。
_BACKEND_OVERRIDE = os.environ.get("MANOSABA_RENDER_BACKEND", "").strip().lower()

# 中文方括号：正文里用 bracket_color 染色的部分。
_BRACKET_RE = re.compile(r"(【[^】]*】)")
# 用户以 \n 输入的换行与真实换行等价处理。
_NEWLINE_RE = re.compile(r"\\n|\n")

# 未显式给出 max_font_height 时的字号上限（像素）。
_DEFAULT_MAX_FONT_HEIGHT = 64


@dataclass
class DrawerRegion:
    """绘制区域，坐标为左上/右下。"""

    top_left_x: int
    top_left_y: int
    bottom_right_x: int
    bottom_right_y: int

    def width(self) -> int:
        """Return the region width."""
        return self.bottom_right_x - self.top_left_x

    def height(self) -> int:
        """Return the region height."""
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


def _to_rgba(color: Any) -> tuple[int, int, int, int]:
    """把颜色规整为 Pillow 可接受的 RGBA 四元组。"""
    if color is None:
        return (0, 0, 0, 255)
    if isinstance(color, (tuple, list)):
        values = list(color)
        if len(values) == 3:
            return (values[0], values[1], values[2], 255)
        if len(values) >= 4:
            return (values[0], values[1], values[2], values[3])
    raise ValueError(f"无法识别的颜色值: {color!r}")


def _wrap_text(text: str, font: Any, max_width: int) -> list[str]:
    """按像素宽度对每段文本做硬换行。"""
    lines: list[str] = []
    for paragraph in _NEWLINE_RE.split(text):
        if not paragraph:
            lines.append("")
            continue
        current = ""
        for char in paragraph:
            candidate = current + char
            if current and font.getlength(candidate) > max_width:
                lines.append(current)
                current = char
            else:
                current = candidate
        lines.append(current)
    return lines


def _fit_font(
    text: str,
    font_path: str,
    font_size_cap: int,
    max_width: int,
    region_height: int,
    line_spacing: float = 0.15,
) -> tuple[Any, list[str]]:
    """区域自适应字号：在字号/宽度/区域高度约束内挑最大字号并排版。

    从字号上限往下逐号尝试，取第一个满足「换行后每行不超宽、
    总行高不超区域高度」的字号。这样短文本用大字号，长文本自动缩小。
    """
    from PIL import ImageFont

    font_size_cap = max(1, int(font_size_cap))
    max_width = max(1, int(max_width))
    region_height = max(1, int(region_height))

    for size in range(font_size_cap, 0, -1):
        font = ImageFont.truetype(font_path, size)
        lines = _wrap_text(text, font, max_width)
        step = int(size * (1 + line_spacing))
        if step * len(lines) <= region_height:
            return font, lines

    # 极端窄区域：返回最小字号，至少给出一行。
    font = ImageFont.truetype(font_path, 1)
    return font, [text[:1]]


def _draw_colored_line(
    draw: Any, x: int, y: int, line: str, font: Any, style: TextStyle
) -> None:
    """逐段绘制一行，【】内的文字用 bracket_color 染色。"""
    for part in _BRACKET_RE.split(line):
        if not part:
            continue
        color = style.bracket_color if part.startswith("【") else style.color
        draw.text((x, y), part, font=font, fill=_to_rgba(color))
        x += int(draw.textlength(part, font=font))


class _PillowDrawer:
    """链式绘制器：paste_image / draw_text / finish。"""

    def __init__(self, base_image: str, font: str) -> None:
        from PIL import Image

        self.image = Image.open(base_image).convert("RGBA")
        self.font = font

    def paste_image(
        self, image: str, region: DrawerRegion, style: PasteStyle
    ) -> "_PillowDrawer":
        """把图片贴到指定区域，处理缩放与 alpha 合成策略。"""
        from PIL import Image

        with Image.open(image) as src_image:
            src = src_image.convert("RGBA")
            width, height = region.width(), region.height()
            if not style.allow_upscale and (src.width > width or src.height > height):
                src = src.crop((0, 0, min(width, src.width), min(height, src.height)))
            if src.width < width or src.height < height:
                canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
                canvas.alpha_composite(src, (0, 0))
                src = canvas
            # keep_alpha=False：把透明像素与黑色底合成，避免透出下层。
            if not style.keep_alpha:
                base = Image.new("RGBA", src.size, (0, 0, 0, 255))
                base.alpha_composite(src)
                src = base
            self.image.alpha_composite(src, (region.top_left_x, region.top_left_y))
        return self

    def draw_text(
        self, text: str, region: DrawerRegion, style: TextStyle
    ) -> "_PillowDrawer":
        """在区域里绘制文本，含自适应字号与【】染色。"""
        from PIL import ImageDraw

        font_size_cap = style.max_font_height or _DEFAULT_MAX_FONT_HEIGHT
        font, lines = _fit_font(
            text,
            self.font,
            font_size_cap,
            region.width(),
            region.height(),
            style.line_spacing,
        )
        draw = ImageDraw.Draw(self.image)
        step = int(font.size * (1 + (style.line_spacing or 0)))
        y = region.top_left_y
        for line in lines:
            _draw_colored_line(draw, region.top_left_x, y, line, font, style)
            y += step
        return self

    def finish(self) -> bytes:
        """完成绘制，返回 PNG 字节。"""
        buffer = io.BytesIO()
        self.image.convert("RGB").save(buffer, format="PNG")
        return buffer.getvalue()


class _PillowTextFitDrawer:
    """自适应文本渲染器：在底图上叠加素描本 overlay 并绘制文本。"""

    def __init__(
        self,
        base_image: str,
        font: str,
        overlay_image: str,
        region: DrawerRegion,
    ) -> None:
        self.base_image = base_image
        self.font = font
        self.overlay_image = overlay_image
        self.region = region

    def draw(self, text: str, style: TextStyle) -> bytes:
        """绘制文本并返回 PNG 字节。"""
        from PIL import Image, ImageDraw

        canvas = Image.open(self.base_image).convert("RGBA")
        # 素描本叠加层放在文字之前，确保文字浮在最上层。
        with Image.open(self.overlay_image) as overlay:
            canvas.alpha_composite(overlay.convert("RGBA"), (0, 0))

        font_size_cap = style.max_font_height or _DEFAULT_MAX_FONT_HEIGHT
        font, lines = _fit_font(
            text,
            self.font,
            font_size_cap,
            self.region.width(),
            self.region.height(),
            style.line_spacing,
        )

        draw = ImageDraw.Draw(canvas)
        step = int(font.size * (1 + (style.line_spacing or 0)))
        top = self.region.top_left_y + max(
            0, (self.region.height() - step * len(lines)) // 2
        )
        for index, line in enumerate(lines):
            width = int(draw.textlength(line, font=font))
            x = self.region.top_left_x + max(0, (self.region.width() - width) // 2)
            _draw_colored_line(draw, x, top + index * step, line, font, style)

        buffer = io.BytesIO()
        canvas.convert("RGB").save(buffer, format="PNG")
        return buffer.getvalue()


def _load_backend() -> str:
    """决定使用哪个后端，并记录选择结果。"""
    if _BACKEND_OVERRIDE in ("sketchbook", "pillow"):
        logger.info("渲染后端由环境变量指定：%s", _BACKEND_OVERRIDE)
        return _BACKEND_OVERRIDE

    try:
        import sketchbook  # noqa: F401  # type: ignore[import-not-found]

        logger.info("渲染后端：sketchbook")
        return "sketchbook"
    except Exception as exc:  # ImportError / OSError（缺失原生扩展）等
        logger.warning("sketchbook 不可用（%s），回退到 Pillow 渲染", exc)
        return "pillow"


_BACKEND = _load_backend()

# 用 Any 显式标注：两种后端的类来自不同模块，mypy 无法证明它们同型；
# 运行时它们都遵守同一份 API 契约（见 tests/stubs/sketchbook/__init__.py）。
Drawer: Any
TextFitDrawer: Any
if _BACKEND == "pillow":
    Drawer = _PillowDrawer
    TextFitDrawer = _PillowTextFitDrawer
else:
    import sketchbook as _sketchbook  # type: ignore[import-not-found]

    Drawer = _sketchbook.Drawer
    TextFitDrawer = _sketchbook.TextFitDrawer
