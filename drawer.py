from io import BytesIO
from pathlib import Path
from typing import List, Optional, Tuple

from PIL import Image
from sketchbook import Drawer  # type: ignore
from sketchbook import FontSet  # type: ignore
from sketchbook import Layer  # type: ignore
from sketchbook import ParseRule  # type: ignore
from sketchbook import Region  # type: ignore
from sketchbook import TextStyle  # type: ignore

from .constants import (
    ANAN_REGION_HEIGHT,
    ANAN_REGION_WIDTH,
    ANAN_REGION_X,
    ANAN_REGION_Y,
    BRACKET_COLOR,
    FACE_WHITELIST,
    MAX_ANAN_TEXT_LENGTH,
    MAX_FONT_HEIGHT,
    MAX_OPTIONS_COUNT,
    OPTION_END_Y,
    OPTION_HEIGHT,
    OPTION_START_X,
    OPTION_START_Y,
    OPTION_WIDTH,
    OPTIONS_PER_PAGE,
    STATEMENT_ICON_HEIGHT,
    STATEMENT_ICON_WIDTH,
    STATEMENT_OFFSET_X,
    STATEMENT_OFFSET_Y,
    TEXT_COLOR,
    TEXT_HEIGHT,
    TEXT_OFFSET_X,
    TEXT_OFFSET_Y,
    TEXT_WIDTH,
    TRIAL_IMAGE_HEIGHT,
    TRIAL_IMAGE_WIDTH,
)
from .emoji_renderer import has_emoji, render_mixed
from .models import Character, Option, Statement

PLUGIN_PATH = Path(__file__).parent


def _text_style(max_font_size: Optional[int] = None) -> TextStyle:
    """Build a sketchbook 1.x text style matching the legacy bracket highlight."""
    return TextStyle(
        color=TEXT_COLOR,
        max_font_size=max_font_size,
        antialias=False,
        parse_rules=[
            ParseRule.cn_bracket(BRACKET_COLOR),
            ParseRule.bracket(BRACKET_COLOR),
        ],
    )


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

    # 安全校验：确保 face 在白名单中，防止路径遍历攻击
    if face not in FACE_WHITELIST:
        raise ValueError(f"Invalid face type: {face}. Must be one of {FACE_WHITELIST}")

    # 使用 .name 获取文件名部分，确保路径不会包含目录分隔符
    safe_face = Path(face).name
    return str(PLUGIN_PATH / "assets/anan" / f"{safe_face}.png")


def draw_anan(text: str, face: Optional[str] = None) -> bytes:
    """Draw the image of what Anan says

    Args:
        text (str): The text to be drawn
        face (Optional[str], optional): The face type to be used.
                                       Available: 害羞, 生气, 病娇, 无语, 开心.
                                       Defaults to None.

    Returns:
        bytes: The image bytes of the drawn image
    """
    text = text.replace("\\n", "\n").strip()
    if not text:
        raise ValueError("请输入要写在素描本上的文本")
    if len(text) > MAX_ANAN_TEXT_LENGTH:
        raise ValueError(f"安安说文本最多支持 {MAX_ANAN_TEXT_LENGTH} 个字符")
    font = str(PLUGIN_PATH / "assets/fonts/SourceHanSansSC-Bold.otf")
    if has_emoji(text):
        with Image.open(get_anan_base_image(face)) as source:
            canvas = source.convert("RGBA")
        lettering = render_mixed(
            text,
            font,
            ANAN_REGION_WIDTH,
            ANAN_REGION_HEIGHT,
            max_font_size=60,
        )
        canvas.alpha_composite(lettering, (ANAN_REGION_X, ANAN_REGION_Y))
        with Image.open(PLUGIN_PATH / "assets/anan/base_overlay.png") as overlay:
            canvas.alpha_composite(overlay.convert("RGBA"))
        result = BytesIO()
        canvas.save(result, format="PNG")
        return result.getvalue()

    fonts = FontSet(font)
    drawer = Drawer.from_image(get_anan_base_image(face), fonts)
    drawer.layer(
        Layer("overlay").image_fit(
            str(PLUGIN_PATH / "assets/anan/base_overlay.png"),
            Region(0, 0, drawer.size[0], drawer.size[1]),
        )
    )
    drawer.layer(
        Layer("text").text(
            text,
            Region(
                ANAN_REGION_X,
                ANAN_REGION_Y,
                ANAN_REGION_WIDTH,
                ANAN_REGION_HEIGHT,
            ),
            _text_style(max_font_size=60),
        )
    )
    return drawer.render()


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

    # 使用 .get() 方法，避免直接索引可能引发的 KeyError
    image_file = mapping.get(statement)
    if image_file is None:
        raise ValueError(f"未知的陈述类型: {statement}")

    return str(PLUGIN_PATH / "assets/trial" / image_file)


def get_option_coordinates(number: int) -> List[Tuple[int, int]]:
    """Place up to three options without clipping panels or statement icons.

    Longer requests are paginated by the handler to retain readable text.
    """
    if not 1 <= number <= OPTIONS_PER_PAGE:
        raise ValueError(f"每张图片支持 1～{OPTIONS_PER_PAGE} 个选项，请分页绘制")
    # An icon extends 43px above its panel; 54px keeps it clear of the
    # preceding panel. Center around the original single-option position.
    spacing = 54
    total_height = number * OPTION_HEIGHT + (number - 1) * spacing
    center_y = (OPTION_START_Y + OPTION_END_Y) // 2
    start_y = center_y - total_height // 2
    return [
        (OPTION_START_X, start_y + i * (OPTION_HEIGHT + spacing)) for i in range(number)
    ]


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
    # 前置校验：确保选项数量在合理范围内
    if len(options) > MAX_OPTIONS_COUNT:
        raise ValueError(f"选项数量过多，最多支持 {MAX_OPTIONS_COUNT} 个选项")
    if len(options) == 0:
        raise ValueError("选项数量不能为 0")
    if not isinstance(character, Character):
        raise ValueError("无效的审判角色")
    coordinates = get_option_coordinates(len(options))

    fonts = FontSet(str(PLUGIN_PATH / "assets/fonts/SourceHanSerifSC.otf"))
    drawer = Drawer(TRIAL_IMAGE_WIDTH, TRIAL_IMAGE_HEIGHT, fonts)
    drawer.base(str(PLUGIN_PATH / "assets/trial/black.png"))
    drawer.layer(
        Layer("background").image_fit(
            str(PLUGIN_PATH / "assets/trial/background.png"),
            Region(0, 0, TRIAL_IMAGE_WIDTH, TRIAL_IMAGE_HEIGHT),
        )
    )
    drawer.layer(
        Layer("character").image_fit(
            str(
                PLUGIN_PATH
                / "assets/trial"
                / ("ema.png" if character == Character.EMA else "hiro.png")
            ),
            Region(667, 0, TRIAL_IMAGE_WIDTH - 667, TRIAL_IMAGE_HEIGHT),
        )
    )

    # Keep the original renderer for plain text. Emoji text is composited in
    # its bounded region after the scene, without touching character artwork.
    emoji_regions = []
    for index, (option, (x, y)) in enumerate(zip(options, coordinates)):
        drawer.layer(
            Layer(f"option-{index}").image_fit(
                str(PLUGIN_PATH / "assets/trial/option.png"),
                Region(x, y, OPTION_WIDTH, OPTION_HEIGHT),
            )
        )
        if has_emoji(option.text):
            emoji_regions.append((option.text, x + TEXT_OFFSET_X, y + TEXT_OFFSET_Y))
        else:
            drawer.layer(
                Layer(f"text-{index}").text(
                    option.text,
                    Region(
                        x + TEXT_OFFSET_X,
                        y + TEXT_OFFSET_Y,
                        TEXT_WIDTH,
                        TEXT_HEIGHT,
                    ),
                    _text_style(max_font_size=MAX_FONT_HEIGHT),
                )
            )
        drawer.layer(
            Layer(f"statement-{index}").image_fit(
                get_statement_image(option.statement),
                Region(
                    x + STATEMENT_OFFSET_X,
                    y + STATEMENT_OFFSET_Y,
                    STATEMENT_ICON_WIDTH,
                    STATEMENT_ICON_HEIGHT,
                ),
            )
        )

    result = drawer.render()
    if not emoji_regions:
        return result
    with Image.open(BytesIO(result)) as source:
        canvas = source.convert("RGBA")
    for text, x, y in emoji_regions:
        lettering = render_mixed(
            text,
            str(PLUGIN_PATH / "assets/fonts/SourceHanSerifSC.otf"),
            TEXT_WIDTH,
            TEXT_HEIGHT,
            color=TEXT_COLOR,
            bracket_color=BRACKET_COLOR,
            max_font_size=MAX_FONT_HEIGHT,
        )
        canvas.alpha_composite(lettering, (x, y))
    output = BytesIO()
    canvas.save(output, format="PNG")
    return output.getvalue()
