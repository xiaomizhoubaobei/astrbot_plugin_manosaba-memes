import io
import re
from pathlib import Path
from typing import Optional, List, Tuple

from PIL import Image, ImageDraw, ImageFont

from .models import Character, Option, Statement
from .constants import (
    FACE_WHITELIST,
    TRIAL_IMAGE_WIDTH,
    TRIAL_IMAGE_HEIGHT,
    OPTION_WIDTH,
    OPTION_START_X,
    OPTION_SLOT_1_Y,
    OPTION_SLOT_2_Y,
    OPTION_SLOT_3_Y,
    MAX_OPTIONS_COUNT,
    STATEMENT_ICON_WIDTH,
    STATEMENT_ICON_HEIGHT,
    STATEMENT_OFFSET_X,
    STATEMENT_OFFSET_Y,
    TEXT_OFFSET_X,
    TEXT_WIDTH,
    TEXT_HEIGHT,
    MAX_FONT_HEIGHT,
    TEXT_COLOR,
    BRACKET_COLOR,
    ANAN_REGION_X,
    ANAN_REGION_Y,
    ANAN_REGION_WIDTH,
    ANAN_REGION_HEIGHT,
    MIN_FONT_SIZE,
    MAX_FONT_SIZE,
    TARGET_WIDTH_RATIO,
    FONT_SIZE_SEARCH_ITERATIONS,
    LINE_SPACING_RATIO,
    UPWARD_OFFSET_RATIO,
    SLOT_HEIGHTS,
    CHARACTER_IMAGE_X,
    WHITE_RGBA,
    BLACK_RGBA,
)

# 模块级正则表达式，避免重复编译
BRACKET_PATTERN_FULL = re.compile(
    r'(【[^】]*】|\[[^\]]*\]|（[^）]*）|\([^)]*\)|《[^》]*》|<[^>]*>|「[^」]*」|『[^』]*』)'
)
BRACKET_PATTERN_PURPLE = re.compile(r'【[^】]*】')

# 标点符号集合，避免重复创建
LINE_START_PUNCT = frozenset({
    '！', '？', '。', '，', '、', '；', '：', '"', "'", '（', '）', '【', '】', '《', '》', '「', '」', '『', '』', '…', '‥', '―', '～', '–', '-', '·'
})

# 图片缓存
_statement_image_cache = {}


PLUGIN_PATH = Path(__file__).parent


def get_anan_base_image(face: Optional[str] = None) -> str:
    """Get the base image path for Anan's face

    Args:
        face (Optional[str], optional): The face type to be used.
                                       Available: 害羞, 生气, 病娇, 无语, 开心.
                                       Defaults to None.

    Returns:
        str: The path to the base image

    Raises:
        ValueError: If face is not in the whitelist
    """
    if face is None:
        return str(PLUGIN_PATH / "assets/anan/base.png")

    if face not in FACE_WHITELIST:
        raise ValueError(f"Invalid face type: {face}. Must be one of {FACE_WHITELIST}")

    safe_face = Path(face).name
    return str(PLUGIN_PATH / "assets/anan" / f"{safe_face}.png")


def load_font(font_path: str, size: int) -> ImageFont.FreeTypeFont:
    """Load a font file with specified size

    Args:
        font_path: Path to the font file
        size: Font size in pixels

    Returns:
        ImageFont.FreeTypeFont: Loaded font

    Raises:
        IOError: If font file cannot be loaded
    """
    return ImageFont.truetype(font_path, size)


def wrap_text_by_chars(text: str, max_chars_per_line: int) -> List[str]:
    """Wrap text by character count (for CJK text without spaces)

    Args:
        text: Input text (may contain newlines)
        max_chars_per_line: Maximum characters per line

    Returns:
        List of wrapped lines
    """
    lines = []
    for paragraph in text.split('\n'):
        if not paragraph:
            lines.append('')
            continue

        chars = list(paragraph)
        current_line = ''

        for char in chars:
            test_line = current_line + char
            if len(test_line) <= max_chars_per_line:
                current_line = test_line
                continue

            if current_line and char in LINE_START_PUNCT:
                lines.append(current_line)
                current_line = char
                continue

            lines.append(current_line)
            current_line = char

        if current_line:
            lines.append(current_line)

    return lines


def wrap_text_with_brackets(text: str, max_chars_per_line: int) -> List[str]:
    """Wrap text keeping bracket content on single lines

    支持的括号类型: 【】[]（）()《》「」『』

    优化: 括号独占一行时，如果后续文本能合并则合并到同一行

    Args:
        text: 输入文本
        max_chars_per_line: 每行最大字符数

    Returns:
        换行后的文本行列表
    """
    lines = []

    for paragraph in text.split('\n'):
        if not paragraph:
            lines.append('')
            continue

        parts = BRACKET_PATTERN_FULL.split(paragraph)
        bracket_idx = 1

        for part in parts:
            if not part:
                bracket_idx += 1
                continue

            if bracket_idx % 2 == 1:
                lines.extend(wrap_text_by_chars(part, max_chars_per_line))
            else:
                lines.append(part)
            bracket_idx += 1

    lines = _merge_bracket_with_next_text(lines, max_chars_per_line)

    return lines


def _merge_bracket_with_next_text(lines: List[str], max_chars_per_line: int) -> List[str]:
    """合并括号行与后续文本行，节省空间

    例如: ['【赞同】', '后续文本'] -> ['【赞同】后续文本']

    Args:
        lines: 换行后的文本行列表
        max_chars_per_line: 每行最大字符数

    Returns:
        合并后的文本行列表
    """
    if not lines:
        return lines

    result = []
    i = 0

    while i < len(lines):
        current_line = lines[i]

        if i + 1 < len(lines) and _is_bracket_only(current_line):
            next_line = lines[i + 1]
            merged = current_line + next_line

            if len(merged) <= max_chars_per_line:
                result.append(merged)
                i += 2
                continue

        result.append(current_line)
        i += 1

    return result


def _is_bracket_only(text: str) -> bool:
    """检查文本是否仅为括号内容（可能有空白）

    Args:
        text: 要检查的文本

    Returns:
        True 如果文本仅为括号内容
    """
    stripped = text.strip()
    return bool(stripped) and BRACKET_PATTERN_FULL.fullmatch(stripped)


def calculate_dynamic_font_size(
    text: str,
    font_path: str,
    region_width: int,
    region_height: int,
    min_size: int = MIN_FONT_SIZE,
    max_size: int = MAX_FONT_SIZE
) -> Tuple[ImageFont.FreeTypeFont, List[str]]:
    """Calculate font size based on text length

    Args:
        text: Text to render
        font_path: Path to font file
        region_width: Available width for text
        region_height: Available height for text
        min_size: Minimum font size
        max_size: Maximum font size

    Returns:
        Tuple of (font, list of wrapped lines)
    """
    target_width = region_width * TARGET_WIDTH_RATIO
    max_chars_per_line = int(target_width / min_size)

    text_length = len(text.replace('\n', ''))
    needs_wrap = text_length > max_chars_per_line

    if needs_wrap:
        lines = wrap_text_with_brackets(text, max_chars_per_line)
        font_size = min_size
    else:
        lines = [text]
        font_size = _binary_search_font_size(
            text, font_path, target_width, region_width, min_size, max_size
        )

    try:
        final_font = load_font(font_path, font_size)
    except IOError:
        final_font = ImageFont.load_default()

    return final_font, lines


def _binary_search_font_size(
    text: str,
    font_path: str,
    target_width: float,
    region_width: int,
    min_size: int,
    max_size: int
) -> int:
    """Binary search for optimal font size

    Args:
        text: Text to measure
        font_path: Path to font file
        target_width: Target width to fill
        region_width: Maximum allowed width
        min_size: Minimum font size
        max_size: Maximum font size

    Returns:
        Optimal font size
    """
    font_cache = {}

    def get_width(size: int) -> float:
        if size in font_cache:
            return font_cache[size]
        try:
            font = load_font(font_path, size)
        except IOError:
            font = ImageFont.load_default()
        width = font.getbbox(text)[2]
        font_cache[size] = width
        return width

    best_size = min_size
    best_score = float('inf')

    for _ in range(FONT_SIZE_SEARCH_ITERATIONS):
        mid = (min_size + max_size) // 2
        if mid == min_size or mid == max_size:
            break

        width = get_width(mid)
        score = abs(width - target_width) if width <= region_width else width - region_width

        if score < best_score:
            best_score = score
            best_size = mid

        if width < target_width:
            min_size = mid + 1
        elif width > region_width:
            max_size = mid - 1
        else:
            break

    return best_size


def draw_line_with_brackets(
    draw: ImageDraw.Draw,
    text: str,
    font: ImageFont.FreeTypeFont,
    x: int,
    y: int,
    default_color: Tuple[int, int, int, int],
    bracket_color: Tuple[int, int, int, int]
) -> None:
    """Draw a single line of text, with 【】 content rendered in a different color

    Args:
        draw: ImageDraw.Draw context
        text: Text line to draw
        font: Font to use
        x: X coordinate to start drawing
        y: Y coordinate to start drawing
        default_color: Color for normal text
        bracket_color: Color for bracketed text 【】
    """
    matches = list(BRACKET_PATTERN_PURPLE.finditer(text))

    if not matches:
        draw.text((x, y), text, font=font, fill=default_color)
        return

    current_x = x
    last_end = 0
    for match in matches:
        # 绘制括号前的文本
        if match.start() > last_end:
            before = text[last_end:match.start()]
            draw.text((current_x, y), before, font=font, fill=default_color)
            current_x += font.getbbox(before)[2]

        # 绘制括号内容(使用指定颜色)
        bracket_text = match.group()
        draw.text((current_x, y), bracket_text, font=font, fill=bracket_color)
        current_x += font.getbbox(bracket_text)[2]
        last_end = match.end()

    # 绘制末尾剩余文本
    if last_end < len(text):
        remaining = text[last_end:]
        draw.text((current_x, y), remaining, font=font, fill=default_color)


def draw_text_with_lines(
    draw: ImageDraw.Draw,
    lines: List[str],
    font: ImageFont.FreeTypeFont,
    color: Tuple[int, int, int, int],
    region_x: int,
    region_y: int,
    region_width: int,
    region_height: int,
    align: str = "center"
) -> None:
    """Draw pre-wrapped text lines within a region with vertical centering

    Args:
        draw: ImageDraw.Draw context
        lines: Pre-wrapped text lines
        font: Font to use
        color: RGBA color tuple
        region_x: Region left edge
        region_y: Region top edge
        region_width: Region width
        region_height: Region height
        align: Text alignment - "left", "center", or "right"
    """
    if not lines:
        return

    line_heights = [font.getbbox(line)[3] - font.getbbox(line)[1] for line in lines]
    line_height = sum(line_heights) / len(line_heights)
    spacing = line_height * LINE_SPACING_RATIO
    total_height = sum(line_heights) + spacing * (len(lines) - 1)

    upward_offset = int(line_height * UPWARD_OFFSET_RATIO)
    current_y = region_y + (region_height - total_height) // 2 - upward_offset

    max_line_width = max(font.getbbox(line)[2] - font.getbbox(line)[0] for line in lines)
    align_offset = {
        "center": (region_width - max_line_width) // 2,
        "right": region_width - max_line_width,
    }
    x_offset = align_offset.get(align, 0)

    for i, line in enumerate(lines):
        current_x = region_x + x_offset

        draw_line_with_brackets(draw, line, font, current_x, current_y, color, BRACKET_COLOR)
        current_y += line_heights[i] + spacing


def draw_anan(text: str, face: Optional[str] = None) -> bytes:
    """Draw the image of what Anan says

    Args:
        text: 要绘制的文本
        face: 表情类型，可选值: 害羞, 生气, 病娇, 无语, 开心

    Returns:
        绘制完成的图片字节数据
    """
    font_path = str(PLUGIN_PATH / "assets/fonts/SourceHanSansSC-Bold.otf")
    base_image_path = get_anan_base_image(face)
    overlay_path = str(PLUGIN_PATH / "assets/anan/base_overlay.png")

    # 创建白色画布并粘贴底图
    base_img = Image.open(base_image_path).convert("RGBA")
    overlay_img = Image.open(overlay_path).convert("RGBA")

    result_img = Image.new("RGBA", base_img.size, WHITE_RGBA)
    result_img.paste(base_img, (0, 0))

    draw = ImageDraw.Draw(result_img)

    # 计算动态字号并换行
    font, lines = calculate_dynamic_font_size(
        text, font_path, ANAN_REGION_WIDTH, ANAN_REGION_HEIGHT
    )

    # 在安安文本区域内绘制换行后的文本
    draw_text_with_lines(
        draw,
        lines,
        font,
        TEXT_COLOR,
        ANAN_REGION_X,
        ANAN_REGION_Y,
        ANAN_REGION_WIDTH,
        ANAN_REGION_HEIGHT,
        align="center"
    )

    # 叠加覆盖层得到最终效果
    result_img = Image.alpha_composite(result_img, overlay_img)

    output = io.BytesIO()
    result_img.convert("RGB").save(output, format="PNG")
    return output.getvalue()


def get_statement_image(statement: Statement) -> str:
    """Get the image path for a statement type

    Args:
        statement (Statement): The statement type

    Returns:
        str: The path to the statement image

    Raises:
        ValueError: If statement type is not recognized
    """
    mapping = {
        Statement.AGREEMENT: "agreement.png",
        Statement.DOUBT: "doubt.png",
        Statement.PERJURY: "perjury.png",
        Statement.REFUTATION: "refutation.png",
        Statement.MAGIC_CHIYUSAISEI: "magic_chiyusaisei.png",
        Statement.MAGIC_EKITAISOUSA: "magic_ekitaisousa.png",
        Statement.MAGIC_FUYUU: "magic_fuyuu.png",
        Statement.MAGIC_GENSHI: "magic_genshi.png",
        Statement.MAGIC_HAKKA: "magic_hakka.png",
        Statement.MAGIC_IREKAWARI: "magic_irekawari.png",
        Statement.MAGIC_KAIRIKI: "magic_kairiki.png",
        Statement.MAGIC_MAJOGOROSHI: "magic_majogoroshi.png",
        Statement.MAGIC_MONOMANE: "magic_monomane.png",
        Statement.MAGIC_SENNOU: "magic_sennou.png",
        Statement.MAGIC_SENRIGAN: "magic_senrigan.png",
        Statement.MAGIC_SHINIMODORI: "magic_shinimodori.png",
        Statement.MAGIC_SHISENYUUDOU: "magic_shisenyuudou.png",
    }

    image_file = mapping.get(statement)
    if image_file is None:
        raise ValueError(f"未知的陈述类型: {statement}")

    return str(PLUGIN_PATH / "assets/trial" / image_file)


def load_statement_image(statement: Statement) -> Image.Image:
    """Load and cache a statement icon image

    Args:
        statement: The statement type

    Returns:
        Cached RGBA Image
    """
    if statement not in _statement_image_cache:
        path = get_statement_image(statement)
        _statement_image_cache[statement] = Image.open(path).convert("RGBA")
    return _statement_image_cache[statement]


def draw_trial(character: Character, options: List[Option]) -> bytes:
    """Draw the trial image for a character saying an option

    Args:
        character (Character): The character who is speaking
        options (List[Option]): The options being spoken

    Returns:
        bytes: The image bytes of the drawn image

    Raises:
        ValueError: If options count exceeds maximum limit
    """
    if len(options) > MAX_OPTIONS_COUNT:
        raise ValueError(f"选项数量过多，最多支持 {MAX_OPTIONS_COUNT} 个选项")

    if len(options) == 0:
        raise ValueError("选项数量不能为 0")

    font_path = str(PLUGIN_PATH / "assets/fonts/SourceHanSerifSC.otf")

    try:
        font = load_font(font_path, MAX_FONT_HEIGHT)
    except IOError:
        font = ImageFont.load_default()

    option_img_template = Image.open(str(PLUGIN_PATH / "assets/trial/option.png")).convert("RGBA")

    slot_heights = SLOT_HEIGHTS
    slot_y_positions = [OPTION_SLOT_1_Y, OPTION_SLOT_2_Y, OPTION_SLOT_3_Y]
    max_chars_per_line = int(TEXT_WIDTH * TARGET_WIDTH_RATIO / MAX_FONT_HEIGHT)

    all_modules = []

    # 步骤1: 换行并按高度限制拆分为多个模块
    for option in options:
        all_lines = wrap_text_with_brackets(option.text, max_chars_per_line)
        if not all_lines:
            all_lines = [option.text]

        line_heights = [font.getbbox(line)[3] - font.getbbox(line)[1] for line in all_lines]
        line_spacing = line_heights[0] * LINE_SPACING_RATIO if line_heights else 0

        available_text_height = TEXT_HEIGHT

        current_lines = []
        current_height = 0

        for line, line_h in zip(all_lines, line_heights):
            potential_height = current_height + line_spacing + line_h

            if current_lines and potential_height > available_text_height:
                all_modules.append((current_lines, option.statement))
                current_lines = [line]
                current_height = line_h
            else:
                current_lines.append(line)
                current_height = potential_height

        if current_lines:
            all_modules.append((current_lines, option.statement))

    if len(all_modules) > MAX_OPTIONS_COUNT * 3:
        raise ValueError(f"选项展开后模块数量过多，最多支持 {MAX_OPTIONS_COUNT} 个选项")

    images = []
    for i in range(0, len(all_modules), 3):
        page_modules = all_modules[i:i+3]

        # 步骤2: 创建底图并粘贴审判背景
        result_img = Image.new("RGBA", (TRIAL_IMAGE_WIDTH, TRIAL_IMAGE_HEIGHT), BLACK_RGBA)
        trial_bg = Image.open(str(PLUGIN_PATH / "assets/trial/background.png")).convert("RGBA")
        result_img.paste(trial_bg, (0, 0))

        # 步骤3: 粘贴角色图片(江贺或广)
        character_image = "ema.png" if character == Character.EMA else "hiro.png"
        character_img = Image.open(str(PLUGIN_PATH / "assets/trial" / character_image)).convert("RGBA")
        result_img.paste(character_img, (CHARACTER_IMAGE_X, 0))

        # 步骤4: 在各个槽位绘制选项模块
        for slot_idx, (lines, statement) in enumerate(page_modules):
            slot_y = slot_y_positions[slot_idx]
            slot_height = slot_heights[slot_idx]

            line_heights = [font.getbbox(line)[3] - font.getbbox(line)[1] for line in lines]
            line_spacing = line_heights[0] * LINE_SPACING_RATIO if line_heights else 0
            total_text_h = sum(line_heights) + line_spacing * (len(lines) - 1)

            # 复制模板并绘制文本
            module_img = option_img_template.copy()
            draw = ImageDraw.Draw(module_img)

            text_y = (slot_height - total_text_h) // 2 - MAX_FONT_HEIGHT // 2

            for j, line in enumerate(lines):
                bbox = font.getbbox(line)
                line_w = bbox[2] - bbox[0]
                text_x = TEXT_OFFSET_X + (TEXT_WIDTH - line_w) // 2

                # 使用紫色绘制【】括号内容
                draw_line_with_brackets(
                    draw, line, font, text_x, text_y, TEXT_COLOR, BRACKET_COLOR
                )

                text_y += line_heights[j] + line_spacing

            # 粘贴陈述图标(使用缓存图片和alpha通道作为遮罩)
            statement_img = load_statement_image(statement)
            module_img.paste(statement_img, (STATEMENT_OFFSET_X, STATEMENT_OFFSET_Y), statement_img)

            # 将模块粘贴到结果图，使用遮罩保留圆角透明效果
            result_img.paste(module_img, (OPTION_START_X, slot_y), module_img)

        output = io.BytesIO()
        result_img.convert("RGB").save(output, format="PNG")
        images.append(output.getvalue())

    if len(images) == 1:
        return images[0]

    # 步骤5: 垂直拼接多页图片
    combined = io.BytesIO()
    result_img = Image.new("RGB", (TRIAL_IMAGE_WIDTH, TRIAL_IMAGE_HEIGHT * len(images)))
    for i, img_bytes in enumerate(images):
        img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        result_img.paste(img, (0, TRIAL_IMAGE_HEIGHT * i))
    result_img.save(combined, format="PNG")
    return combined.getvalue()
