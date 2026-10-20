"""Offline Noto 2D emoji and text layout; no system emoji font dependency."""
from dataclasses import dataclass
from functools import lru_cache
from io import BytesIO
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
import regex

ASSET_ROOT = Path(__file__).parent / "assets" / "noto_emoji"
GRAPHEMES = regex.compile(r"\X")
EMOJI = regex.compile(r"\p{Extended_Pictographic}|\p{Regional_Indicator}|\p{Emoji_Modifier}|\u20e3")


@dataclass(frozen=True)
class Token:
    text: str
    asset: str | None = None
    highlighted: bool = False


def has_emoji(text: str) -> bool:
    return EMOJI.search(text) is not None


@lru_cache(maxsize=1)
def asset_index() -> dict[str, str]:
    return json.loads((ASSET_ROOT / "index.json").read_text(encoding="utf-8"))


def tokenize(text: str) -> list[Token]:
    """Keep ZWJ, skin tone, flag, variation and keycap sequences indivisible."""
    tokens = []
    closing = []
    index = asset_index()
    for cluster in GRAPHEMES.findall(text.replace("\r\n", "\n").replace("\r", "\n").replace("\t", "    ")):
        if cluster in ("[", "【"):
            closing.append("]" if cluster == "[" else "】")
        highlighted = bool(closing)
        if has_emoji(cluster):
            key = "_".join(f"{ord(c):x}" for c in cluster if c not in "\ufe0e\ufe0f")
            asset = index.get(key)
            # Unknown/new sequences are labelled instead of being split into
            # misleading component emoji or drawn as missing-font boxes.
            tokens.append(Token(cluster if asset else "[表情]", asset, highlighted))
        else:
            tokens.append(Token(cluster, None, highlighted))
        if closing and cluster == closing[-1]:
            closing.pop()
    return tokens


@lru_cache(maxsize=16)
def _font(path: str, size: int):
    # FreeType otherwise holds the font file open on Windows, preventing a
    # plugin upgrade/removal while a cached size remains alive.
    return ImageFont.truetype(BytesIO(_font_bytes(path)), size)


@lru_cache(maxsize=2)
def _font_bytes(path: str) -> bytes:
    return Path(path).read_bytes()


@lru_cache(maxsize=128)
def _emoji(filename: str):
    # Callers only receive manifest names, never paths from user input.
    with Image.open(ASSET_ROOT / "png" / filename) as source:
        return source.convert("RGBA")


@dataclass
class Placement:
    token: Token
    width: float
    left_pad: float
    above: int
    below: int


@dataclass
class Line:
    items: list[Placement]
    width: float = 0
    above: int = 0
    below: int = 0


def layout(tokens: list[Token], font_path: str, size: int, width: int):
    font = _font(font_path, size)
    _, top, _, bottom = font.getbbox("国Ag", anchor="ls")
    lines = []
    line = Line([])

    def finish():
        nonlocal line
        if not line.items:
            line.above, line.below = -top, bottom
        lines.append(line)
        line = Line([])

    for token in tokens:
        if token.text == "\n":
            finish()
            continue
        if token.asset:
            above = round(size * 0.85)
            item = Placement(token, size, 0, above, size - above)
        else:
            left, top, right, bottom = font.getbbox(token.text, anchor="ls")
            pad = max(0, -left)
            advance = max(font.getlength(token.text), right) + pad
            item = Placement(token, advance, pad, max(0, -top), max(0, bottom))
        if line.items and line.width + item.width > width:
            finish()
        line.items.append(item)
        line.width += item.width
        line.above = max(line.above, item.above)
        line.below = max(line.below, item.below)
    finish()
    spacing = max(1, round(size * 0.15))
    height = sum(row.above + row.below for row in lines) + spacing * (len(lines) - 1)
    return lines, height, spacing


def render_mixed(text: str, font_path: str, width: int, height: int,
                 color=(0, 0, 0, 255), bracket_color=(128, 0, 128, 255),
                 max_font_size: int = 128) -> Image.Image:
    tokens = tokenize(text)
    # A transparent margin protects antialiasing at the region boundary.
    available_width, available_height = width - 4, height - 4
    low, high = 8, min(max_font_size, available_height)
    best = None
    while low <= high:
        size = (low + high) // 2
        lines, content_height, spacing = layout(tokens, font_path, size, available_width)
        if content_height <= available_height and all(line.width <= available_width for line in lines):
            best = size, lines, content_height, spacing
            low = size + 1
        else:
            high = size - 1
    if best is None:
        raise ValueError("文本或换行过多，无法在图片区域内清晰显示")
    size, lines, content_height, spacing = best
    font = _font(font_path, size)
    canvas = Image.new("RGBA", (width, height))
    pen = ImageDraw.Draw(canvas)
    y = (height - content_height) // 2
    for line in lines:
        x = (width - line.width) / 2
        baseline = y + line.above
        for item in line.items:
            if item.token.asset:
                source = _emoji(item.token.asset)
                # All packaged assets use a square canvas; retain that canvas
                # so e.g. flags and pigs align consistently without distortion.
                emoji = source.resize((size, size), Image.Resampling.LANCZOS)
                canvas.alpha_composite(emoji, (math.floor(x), baseline - item.above))
            else:
                pen.text((x + item.left_pad, baseline), item.token.text,
                         font=font, anchor="ls",
                         fill=bracket_color if item.token.highlighted else color)
            x += item.width
        y += line.above + line.below + spacing
    return canvas
