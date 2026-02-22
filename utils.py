from typing import Optional

from .models import Statement, Character


def get_magic_statement(text: str) -> Statement:
    """Convert a string magic statement type to a Statement enum

    Args:
        text (str): The string representation of the magic statement type

    Returns:
        Statement: The corresponding Statement enum
        
    Raises:
        ValueError: If text is empty or not a valid magic character name
    """
    if not text or not text.strip():
        raise ValueError("Magic character name cannot be empty")
    
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
    result = mapping.get(text)
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
    match statement:
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

    Args:
        character (str): The string representation of the character name

    Returns:
        Character: The corresponding Character enum
        
    Raises:
        ValueError: If character name is invalid
    """
    mapping = {
        "艾玛": Character.EMA,
        "希罗": Character.HIRO,
    }
    
    # 使用 .get() 方法，如果键不存在则抛出清晰的 ValueError
    result = mapping.get(character)
    if result is None:
        raise ValueError(
            f"无效的角色 '{character}'，请从以下选项中选择：艾玛, 希罗"
        )
    return result