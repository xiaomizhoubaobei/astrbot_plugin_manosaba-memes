import math
from pathlib import Path
from typing import Optional, List, Tuple

from sketchbook import (
    Drawer,  # type: ignore
    TextStyle,  # type: ignore
    PasteStyle,  # type: ignore
    DrawerRegion,  # type: ignore
    TextFitDrawer,  # type: ignore
)

from .models import Character, Option, Statement
from .constants import (
    FACE_WHITELIST,
    TRIAL_IMAGE_WIDTH,
    TRIAL_IMAGE_HEIGHT,
    OPTION_WIDTH,
    OPTION_HEIGHT,
    OPTION_START_X,
    OPTION_START_Y,
    OPTION_END_Y,
    MAX_PADDING,
    MAX_OPTIONS_COUNT,
    STATEMENT_ICON_WIDTH,
    STATEMENT_ICON_HEIGHT,
    STATEMENT_OFFSET_X,
    STATEMENT_OFFSET_Y,
    TEXT_OFFSET_X,
    TEXT_OFFSET_Y,
    TEXT_WIDTH,
    TEXT_HEIGHT,
    MAX_FONT_HEIGHT,
    TEXT_COLOR,
    BRACKET_COLOR,
    ANAN_REGION_X,
    ANAN_REGION_Y,
    ANAN_REGION_WIDTH,
    ANAN_REGION_HEIGHT,
)


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
    drawer = TextFitDrawer(
        base_image=get_anan_base_image(face),
        font=str(PLUGIN_PATH / "assets/fonts/SourceHanSansSC-Bold.otf"),
        overlay_image=str(PLUGIN_PATH / "assets/anan/base_overlay.png"),
        region=DrawerRegion(
            ANAN_REGION_X, 
            ANAN_REGION_Y, 
            ANAN_REGION_X + ANAN_REGION_WIDTH, 
            ANAN_REGION_Y + ANAN_REGION_HEIGHT
        ),
    )
    image_bytes = drawer.draw(
        text=text,
        style=TextStyle(color=(0, 0, 0, 255)),
    )
    return image_bytes


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
    """Get the coordinates for drawing options based on the number of options
    
    布局算法说明：
    - 选项在审判界面中从上到下排列
    - 确保选项之间至少有 20px 的间距，避免挤在一起
    - 在可用范围内垂直居中显示所有选项
    
    Args:
        number (int): The number of options

    Returns:
        List[Tuple[int, int]]: A list of (x, y) coordinates for each option
        
    Raises:
        ValueError: If number of options exceeds the maximum limit
    """
    # 前置校验：确保选项数量在合理范围内
    if number > MAX_OPTIONS_COUNT:
        raise ValueError(f"选项数量过多，最多支持 {MAX_OPTIONS_COUNT} 个选项")
    
    if number <= 0:
        raise ValueError("选项数量必须大于 0")
    
    # 最小间距（确保选项不会挤在一起）
    MIN_SPACING = 20
    
    # 计算所需的总高度（选项高度 + 最小间距）
    total_layout_height = number * OPTION_HEIGHT + (number - 1) * MIN_SPACING
    
    # 计算可用高度
    available_height = OPTION_END_Y - OPTION_START_Y
    
    if number == 1:
        # 单个选项，垂直居中
        start_y = OPTION_START_Y + (available_height - OPTION_HEIGHT) // 2
        return [(OPTION_START_X, start_y)]
    
    # 计算起始Y坐标，使整体布局垂直居中
    # 如果总高度超过可用高度，从 OPTION_START_Y 开始
    if total_layout_height > available_height:
        start_y = OPTION_START_Y
    else:
        start_y = OPTION_START_Y + (available_height - total_layout_height) // 2
    
    # 生成选项坐标，每个选项之间保持 MIN_SPACING 间距
    return [
        (OPTION_START_X, start_y + i * (OPTION_HEIGHT + MIN_SPACING))
        for i in range(number)
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
    
    # Background and character
    drawer = Drawer(
        base_image=str(PLUGIN_PATH / "assets/trial/black.png"),
        font=str(PLUGIN_PATH / "assets/fonts/SourceHanSerifSC.otf"),
    )
    drawer = drawer.paste_image(
        str(PLUGIN_PATH / "assets/trial/background.png"),
        region=DrawerRegion(0, 0, TRIAL_IMAGE_WIDTH, TRIAL_IMAGE_HEIGHT),
        style=PasteStyle(keep_alpha=False),
    ).paste_image(
        str(
            PLUGIN_PATH
            / "assets/trial"
            / ("ema.png" if character == Character.EMA else "hiro.png")
        ),
        region=DrawerRegion(667, 0, TRIAL_IMAGE_WIDTH, TRIAL_IMAGE_HEIGHT),
        style=PasteStyle(keep_alpha=False),
    )

    # Options, texts, and statements
    coordinates = get_option_coordinates(len(options))
    for option, (x, y) in zip(options, coordinates):
        drawer = (
            drawer.paste_image(
                str(PLUGIN_PATH / "assets/trial/option.png"),
                region=DrawerRegion(x, y, x + OPTION_WIDTH, y + OPTION_HEIGHT),
                style=PasteStyle(keep_alpha=False),
            )
            .draw_text(
                text=option.text,
                region=DrawerRegion(
                    x + TEXT_OFFSET_X, 
                    y + TEXT_OFFSET_Y, 
                    x + TEXT_OFFSET_X + TEXT_WIDTH, 
                    y + TEXT_OFFSET_Y + TEXT_HEIGHT
                ),
                style=TextStyle(
                    color=TEXT_COLOR,
                    bracket_color=BRACKET_COLOR,
                    max_font_height=MAX_FONT_HEIGHT,
                ),
            )
            .paste_image(
                get_statement_image(option.statement),
                region=DrawerRegion(
                    x + STATEMENT_OFFSET_X, 
                    y + STATEMENT_OFFSET_Y, 
                    x + STATEMENT_OFFSET_X + STATEMENT_ICON_WIDTH, 
                    y + STATEMENT_OFFSET_Y + STATEMENT_ICON_HEIGHT
                ),
                style=PasteStyle(keep_alpha=False),
            )
        )

    return drawer.finish()