"""数据模型定义

此模块定义了插件中使用的所有数据模型，包括：
- Character: 审判角色枚举
- Statement: 陈述类型枚举
- Option: 审判选项数据类
"""

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


# 常量定义
MAX_OPTION_TEXT_LENGTH = 200  # 选项文本最大长度


class StrEnum(str, Enum):
    """String Enum base class"""

    pass


class Character(StrEnum):
    """Characters available for trial drawing"""

    EMA = "Ema"
    HIRO = "Hiro"


class Statement(StrEnum):
    """Types of statements for the trial drawing"""

    AGREEMENT = "Agreement"
    DOUBT = "Doubt"
    PERJURY = "Perjury"
    REFUTATION = "Refutation"
    MAGIC_CHIYUSAISEI = "Magic Chiyu & Saisei"
    MAGIC_EKITAISOUSA = "Magic Ekitai Sousa"
    MAGIC_FUYUU = "Magic Fuyuu"
    MAGIC_GENSHI = "Magic Genshi"
    MAGIC_HAKKA = "Magic Hakka"
    MAGIC_IREKAWARI = "Magic Irekawari"
    MAGIC_KAIRIKI = "Magic Kairiki"
    MAGIC_MAJOGOROSHI = "Magic Majo Goroshi"
    MAGIC_MONOMANE = "Magic Monomane"
    MAGIC_SENNOU = "Magic Sennou"
    MAGIC_SENRIGAN = "Magic Senrigan"
    MAGIC_SHINIMODORI = "Magic Shini Modori"
    MAGIC_SHISENYUUDOU = "Magic Shisen Yuudou"


@dataclass
class Option:
    """A trial option for a character to say
    
    Attributes:
        statement (Statement): The type of statement this option represents
        text (str): The text content of the option
    
    Raises:
        TypeError: If statement is not a Statement instance
        ValueError: If text is empty or exceeds maximum length
    """
    
    statement: Statement
    text: str
    
    def __post_init__(self):
        """Validate option data after initialization
        
        Raises:
            TypeError: If statement is not a Statement instance
            ValueError: If text is empty or exceeds maximum length
        """
        # 验证 statement 类型
        if not isinstance(self.statement, Statement):
            raise TypeError(
                f"statement must be a Statement instance, "
                f"got {type(self.statement).__name__}"
            )
        
        # 验证 text 不为空
        if not self.text or not self.text.strip():
            raise ValueError("text cannot be empty or whitespace only")
        
        # 验证 text 长度
        text_stripped = self.text.strip()
        if len(text_stripped) > MAX_OPTION_TEXT_LENGTH:
            raise ValueError(
                f"text length exceeds maximum limit of {MAX_OPTION_TEXT_LENGTH} characters"
            )
        
        # 自动去除首尾空格
        self.text = text_stripped
    
    def __repr__(self) -> str:
        """Return a string representation of the option"""
        return f"Option(statement={self.statement.name}, text={self.text[:50]}...)"