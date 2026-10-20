"""工具函数模块

此模块提供字符串到枚举的转换功能，包括：
- get_magic_statement: 魔法角色名到 Statement 枚举的转换
- get_statement: 陈述类型到 Statement 枚举的转换
- get_character: 角色名到 Character 枚举的转换
"""

import re
from typing import Optional

from .models import Statement, Character, Option
from .constants import FACE_WHITELIST, MAX_ANAN_TEXT_LENGTH, MAX_OPTIONS_COUNT


# Compile flags into the pattern: AstrBot's regex decorator does not apply a
# separate flags keyword to RegexFilter.
TRIAL_TRIGGER = re.compile(r"^\s*【(?:疑问|反驳|伪证|赞同|魔法)(?:[:：][^】]*)?】")
TRIAL_LINE = re.compile(r"【(疑问|反驳|伪证|赞同|魔法)(?:[:：]([^】]*))?】(.*)")


def parse_anan(content: str) -> tuple[str, Optional[str]]:
    content = content.strip()
    parts = content.rsplit(None, 1)
    face = None
    if len(parts) == 2 and parts[1] in FACE_WHITELIST:
        content, face = parts
    text = content.replace("\\n", "\n").strip()
    if not text:
        raise ValueError("请输入要写在素描本上的文本")
    if len(text) > MAX_ANAN_TEXT_LENGTH:
        raise ValueError(f"安安说文本最多支持 {MAX_ANAN_TEXT_LENGTH} 个字符")
    return text, face


def parse_trial(message: str) -> list[Option]:
    lines = [line.strip() for line in message.splitlines() if line.strip()]
    if not lines:
        raise ValueError("请至少输入一个选项")
    if len(lines) > MAX_OPTIONS_COUNT:
        raise ValueError(f"选项数量过多，最多支持 {MAX_OPTIONS_COUNT} 个选项")
    options = []
    for index, line in enumerate(lines, 1):
        match = TRIAL_LINE.fullmatch(line)
        if not match:
            raise ValueError(f"第 {index} 行格式错误，请使用：【疑问/反驳/伪证/赞同/魔法:角色名】文本")
        statement, arg, text = match.groups()
        if arg is not None and statement != "魔法":
            raise ValueError(f"第 {index} 行只有魔法类型需要指定角色名")
        options.append(Option(get_statement(statement, arg), text.replace("\\n", "\n")))
    return options


def _normalize_text(text: str) -> str:
    """标准化输入文本
    
    此函数会：
    1. 去除首尾空格
    2. 将全角空格转换为半角空格
    3. 将多个连续空格合并为一个
    
    Args:
        text (str): 待标准化的文本
        
    Returns:
        str: 标准化后的文本
    """
    if not text:
        return text
    
    # 去除首尾空格
    text = text.strip()
    
    # 将全角空格转换为半角空格
    text = text.replace('\u3000', ' ')
    
    # 将多个连续空格合并为一个
    text = ' '.join(text.split())
    
    return text


def get_magic_statement(text: str) -> Statement:
    """Convert a string magic statement type to a Statement enum
    
    此函数会对输入进行标准化处理，包括：
    - 去除首尾空格
    - 处理全角空格
    
    Args:
        text (str): The string representation of the magic statement type

    Returns:
        Statement: The corresponding Statement enum
        
    Raises:
        ValueError: If text is empty or not a valid magic character name
    """
    if not text:
        raise ValueError("Magic character name cannot be empty")
    
    # 标准化输入
    normalized_text = _normalize_text(text)
    
    if not normalized_text:
        raise ValueError("Magic character name cannot be empty or whitespace only")
    
    mapping = {
        "梅露露": Statement.MAGIC_CHIYUSAISEI,
        "诺亚": Statement.MAGIC_EKITAISOUSA,
        "汉娜": Statement.MAGIC_FUYUU,
        "奈叶香": Statement.MAGIC_GENSHI,
        "亚里沙": Statement.MAGIC_HAKKA,
        "米莉亚": Statement.MAGIC_IREKAWARI,
        "雪莉": Statement.MAGIC_KAIRIKI,
        "艾玛": Statement.MAGIC_MAJOGOROSHI,
        "玛格": Statement.MAGIC_MONOMANE,
        "安安": Statement.MAGIC_SENNOU,
        "可可": Statement.MAGIC_SENRIGAN,
        "希罗": Statement.MAGIC_SHINIMODORI,
        "蕾雅": Statement.MAGIC_SHISENYUUDOU,
    }
    
    # 使用 .get() 方法，如果键不存在则抛出清晰的 ValueError
    result = mapping.get(normalized_text)
    if result is None:
        raise ValueError(
            f"无效的角色 '{text}'，请从以下选项中选择："
            "梅露露, 诺亚, 汉娜, 奈叶香, 亚里沙, 米莉亚, 雪莉, 艾玛, 玛格, 安安, 可可, 希罗, 蕾雅"
        )
    return result


def get_statement(statement: str, arg: Optional[str] = None) -> Statement:
    """Convert a string statement type to a Statement enum
    
    Args:
        statement (str): The string representation of the statement type
        arg (Optional[str]): Extra argument for the magic statement types

    Returns:
        Statement: The corresponding Statement enum
        
    Raises:
        ValueError: If statement type is invalid or arg is missing for magic type
    """
    # 标准化陈述类型
    normalized_statement = _normalize_text(statement)
    
    match normalized_statement:
        case "赞同":
            return Statement.AGREEMENT
        case "疑问":
            return Statement.DOUBT
        case "伪证":
            return Statement.PERJURY
        case "反驳":
            return Statement.REFUTATION
        case "魔法":
            if not arg or not arg.strip():
                raise ValueError("魔法类型需要指定角色名，格式：魔法:角色名")
            return get_magic_statement(arg)
        case _:
            raise ValueError(f"无效的陈述类型: {statement}")


def get_character(character: str) -> Character:
    """Convert a string character name to a Character enum
    
    此函数会对输入进行标准化处理，包括：
    - 去除首尾空格
    - 处理全角空格
    
    Args:
        character (str): The string representation of the character name

    Returns:
        Character: The corresponding Character enum
        
    Raises:
        ValueError: If character name is invalid
    """
    if not character:
        raise ValueError("Character name cannot be empty")
    
    # 标准化输入
    normalized_character = _normalize_text(character)
    
    if not normalized_character:
        raise ValueError("Character name cannot be empty or whitespace only")
    
    mapping = {
        "艾玛": Character.EMA,
        "希罗": Character.HIRO,
        # Older versions persist enum values, not the Chinese display names.
        "Ema": Character.EMA,
        "Hiro": Character.HIRO,
    }
    
    # 使用 .get() 方法，如果键不存在则抛出清晰的 ValueError
    result = mapping.get(normalized_character)
    if result is None:
        raise ValueError(
            f"无效的角色 '{character}'，请从以下选项中选择：艾玛, 希罗"
        )
    return result
