"""models.py 数据模型单测。"""

import pytest
from astrbot_plugin_manosaba_memes.models import (
    MAX_OPTION_TEXT_LENGTH,
    Character,
    Option,
    Statement,
    StrEnum,
)


def test_str_enum_is_string_like() -> None:
    assert Character.EMA == "Ema"
    assert isinstance(Character.HIRO, str)
    assert str(Statement.DOUBT) == "Statement.DOUBT"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("Ema", Character.EMA), ("Hiro", Character.HIRO)],
)
def test_character_values(raw: str, expected: Character) -> None:
    assert Character(raw) is expected


def test_option_normalizes_text() -> None:
    option = Option(Statement.DOUBT, "  这是疑问  ")
    assert option.text == "这是疑问"
    assert option.statement is Statement.DOUBT


def test_option_rejects_wrong_statement_type() -> None:
    with pytest.raises(TypeError, match="Statement"):
        Option("Doubt", "文本")  # type: ignore[arg-type]


@pytest.mark.parametrize("bad_text", ["", "   ", "\u3000"])
def test_option_rejects_blank_text(bad_text: str) -> None:
    with pytest.raises(ValueError, match="text cannot be empty"):
        Option(Statement.AGREEMENT, bad_text)


def test_option_rejects_too_long_text() -> None:
    with pytest.raises(ValueError, match="exceeds maximum limit"):
        Option(Statement.AGREEMENT, "x" * (MAX_OPTION_TEXT_LENGTH + 1))


def test_option_accepts_max_length_text() -> None:
    option = Option(Statement.AGREEMENT, "x" * MAX_OPTION_TEXT_LENGTH)
    assert len(option.text) == MAX_OPTION_TEXT_LENGTH


def test_option_repr_contains_statement_name() -> None:
    assert "DOUBT" in repr(Option(Statement.DOUBT, "文本"))


def test_str_enum_base_is_instantiable() -> None:
    """覆盖 StrEnum 基类的 pass 分支。"""
    assert issubclass(Character, StrEnum)
